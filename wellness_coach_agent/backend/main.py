import json
import logging
import os
from datetime import datetime, timedelta

from core import (
    DailyHabitEntry,
    WellnessProfile,
    conduct_weekly_checkin,
    format_habit_summary,
    generate_wellness_plan,
)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from memory_utils import MemoriManager
from pydantic import BaseModel

from backend.database import (
    Correlation,
    DailyHabitLog,
    WeeklyCheckIn,
    WellnessPlan,
    get_habit_stats,
    get_session,
    get_weekly_activity,
    init_database,
)

# --- Request / Response models ---


class InitRequest(BaseModel):
    userId: str
    openaiKey: str | None = None
    memoriKey: str | None = None


class InitResponse(BaseModel):
    profile: WellnessProfile | None = None


class ProfileRequest(BaseModel):
    userId: str
    profile: WellnessProfile
    openaiKey: str | None = None
    memoriKey: str | None = None


class LogHabitRequest(BaseModel):
    userId: str
    habitEntry: DailyHabitEntry
    openaiKey: str | None = None
    memoriKey: str | None = None


class GetHabitsRequest(BaseModel):
    userId: str
    startDate: str | None = None  # ISO date string
    endDate: str | None = None  # ISO date string
    limit: int = 100


class GeneratePlanRequest(BaseModel):
    userId: str
    profile: WellnessProfile
    openaiKey: str | None = None
    memoriKey: str | None = None


class WeeklyCheckInRequest(BaseModel):
    userId: str
    profile: WellnessProfile
    weekStartDate: str | None = None  # ISO date string
    openaiKey: str | None = None
    memoriKey: str | None = None


class WellnessQuestionRequest(BaseModel):
    userId: str
    question: str
    openaiKey: str | None = None
    memoriKey: str | None = None


class UsageResponse(BaseModel):
    success: bool = True


def _get_memori_manager(
    user_id: str,
    openai_key_override: str | None = None,
    memori_key_override: str | None = None,
) -> MemoriManager:
    """
    Create a MemoriManager for the given logical user id.
    """
    user_id = (user_id or "").strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="userId must be non-empty.")

    # Prefer user-provided key, else fall back to environment
    openai_key = (openai_key_override or "").strip() or os.getenv("OPENAI_API_KEY", "")
    if not openai_key:
        raise HTTPException(
            status_code=500,
            detail="No OpenAI API key available. Provide your own or configure OPENAI_API_KEY on the backend.",
        )

    mgr = MemoriManager(
        openai_api_key=openai_key,
        sqlite_path=os.getenv("WELLNESS_SQLITE_PATH") or "./memori_wellness.sqlite",
        entity_id=user_id,
    )
    return mgr


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Wellness Coach API")


# Initialize database tables on startup
@app.on_event("startup")
def startup_event():
    logger.info("Starting up - initializing database...")
    try:
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.post("/init", response_model=InitResponse)
def init_session(req: InitRequest) -> InitResponse:
    """
    Initialize a session for the given user:
    - Ensure Memori / SQLite are reachable.
    - Load the latest wellness profile, if any.
    """
    mgr = _get_memori_manager(req.userId, req.openaiKey)

    profile_dict = mgr.get_latest_wellness_profile()
    profile: WellnessProfile | None = None
    if profile_dict is not None:
        try:
            profile = WellnessProfile(**profile_dict)
        except Exception:
            profile = None

    return InitResponse(profile=profile)


@app.post("/profile", response_model=UsageResponse)
def save_profile(req: ProfileRequest) -> UsageResponse:
    """
    Save the wellness profile into Memori for this user.
    """
    mgr = _get_memori_manager(req.userId, req.openaiKey)
    mgr.log_wellness_profile(req.profile.model_dump())
    return UsageResponse(success=True)


@app.post("/habits/log")
def log_habit(req: LogHabitRequest) -> dict:
    """
    Log a daily habit entry (sleep, exercise, nutrition, mood).
    """
    mgr = _get_memori_manager(req.userId, req.openaiKey)

    # Parse date
    try:
        entry_date = datetime.fromisoformat(req.habitEntry.date.replace("Z", "+00:00"))
    except Exception:
        entry_date = datetime.utcnow()

    # Get profile for Memori logging
    profile_dict = mgr.get_latest_wellness_profile()
    if profile_dict:
        from core import WellnessProfile

        profile = WellnessProfile(**profile_dict)
    else:
        # Create a minimal profile
        from core import WellnessProfile

        profile = WellnessProfile(name=req.userId, primary_goals=[])

    # Format summary for Memori
    habit_summary = format_habit_summary(profile, req.habitEntry)
    mgr.log_daily_habit(habit_summary)

    # Save to database
    db = get_session()
    try:
        # Check if entry already exists for this date
        existing = (
            db.query(DailyHabitLog)
            .filter(
                DailyHabitLog.user_id == req.userId,
                DailyHabitLog.date == entry_date.date(),
            )
            .first()
        )

        if existing:
            # Update existing entry
            existing.sleep_hours = req.habitEntry.sleep_hours
            existing.sleep_quality = req.habitEntry.sleep_quality
            existing.exercise_type = req.habitEntry.exercise_type
            existing.exercise_duration_minutes = (
                req.habitEntry.exercise_duration_minutes
            )
            existing.exercise_intensity = req.habitEntry.exercise_intensity
            existing.steps = req.habitEntry.steps
            existing.water_intake_liters = req.habitEntry.water_intake_liters
            existing.calories_consumed = req.habitEntry.calories_consumed
            existing.mood_score = req.habitEntry.mood_score
            existing.energy_level = req.habitEntry.energy_level
            existing.stress_level = req.habitEntry.stress_level
            existing.general_notes = req.habitEntry.notes
            db.commit()
            db.refresh(existing)
            return {"success": True, "logId": existing.id, "updated": True}
        else:
            # Create new entry
            log_entry = DailyHabitLog(
                user_id=req.userId,
                date=entry_date,
                sleep_hours=req.habitEntry.sleep_hours,
                sleep_quality=req.habitEntry.sleep_quality,
                exercise_type=req.habitEntry.exercise_type,
                exercise_duration_minutes=req.habitEntry.exercise_duration_minutes,
                exercise_intensity=req.habitEntry.exercise_intensity,
                steps=req.habitEntry.steps,
                water_intake_liters=req.habitEntry.water_intake_liters,
                calories_consumed=req.habitEntry.calories_consumed,
                mood_score=req.habitEntry.mood_score,
                energy_level=req.habitEntry.energy_level,
                stress_level=req.habitEntry.stress_level,
                general_notes=req.habitEntry.notes,
            )
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            return {"success": True, "logId": log_entry.id, "updated": False}
    finally:
        db.close()


@app.post("/habits/get")
def get_habits(req: GetHabitsRequest) -> dict:
    """
    Get habit logs for a user, optionally filtered by date range.
    """
    db = get_session()
    try:
        query = db.query(DailyHabitLog).filter(DailyHabitLog.user_id == req.userId)

        if req.startDate:
            try:
                start = datetime.fromisoformat(req.startDate.replace("Z", "+00:00"))
                query = query.filter(DailyHabitLog.date >= start.date())
            except Exception:
                pass

        if req.endDate:
            try:
                end = datetime.fromisoformat(req.endDate.replace("Z", "+00:00"))
                query = query.filter(DailyHabitLog.date <= end.date())
            except Exception:
                pass

        logs = query.order_by(DailyHabitLog.date.desc()).limit(req.limit).all()

        return {
            "total": len(logs),
            "habits": [log.to_dict() for log in logs],
        }
    finally:
        db.close()


@app.get("/habits/{user_id}/today")
def get_today_habit(user_id: str) -> dict:
    """
    Get today's habit log for a user.
    """
    db = get_session()
    try:
        today = datetime.utcnow().date()
        log = (
            db.query(DailyHabitLog)
            .filter(
                DailyHabitLog.user_id == user_id,
                DailyHabitLog.date == today,
            )
            .first()
        )

        if log:
            return {"exists": True, "habit": log.to_dict()}
        else:
            return {"exists": False, "habit": None}
    finally:
        db.close()


@app.post("/plan/generate")
def generate_plan(req: GeneratePlanRequest) -> dict:
    """
    Generate a personalized wellness plan using LangGraph.
    """
    mgr = _get_memori_manager(req.userId, req.openaiKey)

    # Get habit history
    db = get_session()
    try:
        logs = (
            db.query(DailyHabitLog)
            .filter(DailyHabitLog.user_id == req.userId)
            .order_by(DailyHabitLog.date.desc())
            .limit(30)
            .all()
        )

        habit_history = []
        for log in reversed(logs):  # Oldest first
            habit_history.append(
                {
                    "date": log.date.isoformat() if log.date else None,
                    "sleep_hours": log.sleep_hours,
                    "sleep_quality": log.sleep_quality,
                    "exercise_type": log.exercise_type,
                    "exercise_duration_minutes": log.exercise_duration_minutes,
                    "mood_score": log.mood_score,
                    "energy_level": log.energy_level,
                    "stress_level": log.stress_level,
                    "water_intake_liters": log.water_intake_liters,
                }
            )
    finally:
        db.close()

    # Get weakness context from Memori
    weakness_context = ""
    try:
        weakness_context = mgr.identify_weaknesses()
    except Exception:
        weakness_context = ""

    model_name = os.getenv("WELLNESS_MODEL", "gpt-4o-mini")
    # Get API key from request or environment
    api_key = req.openaiKey or os.getenv("OPENAI_API_KEY")
    plan_result = generate_wellness_plan(
        profile=req.profile,
        habit_history=habit_history,
        weakness_context=weakness_context,
        model_name=model_name,
        api_key=api_key,
    )

    # Save plan to database
    db = get_session()
    try:
        # Deactivate previous plans
        db.query(WellnessPlan).filter(
            WellnessPlan.user_id == req.userId,
            WellnessPlan.is_active,
        ).update({"is_active": False})

        plan = WellnessPlan(
            user_id=req.userId,
            focus_areas=json.dumps(plan_result.focus_areas),
            daily_goals=json.dumps(plan_result.daily_goals),
            weekly_objectives=json.dumps(plan_result.weekly_objectives),
            plan_markdown=plan_result.plan_markdown,
            interventions=json.dumps(plan_result.interventions),
            is_active=True,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

        return {
            "planId": plan.id,
            "weekNumber": plan.week_number,
            "focusAreas": plan_result.focus_areas,
            "dailyGoals": plan_result.daily_goals,
            "weeklyObjectives": plan_result.weekly_objectives,
            "planMarkdown": plan_result.plan_markdown,
            "interventions": plan_result.interventions,
        }
    finally:
        db.close()


@app.get("/plan/{user_id}/active")
def get_active_plan(user_id: str) -> dict:
    """
    Get the active wellness plan for a user.
    """
    db = get_session()
    try:
        plan = (
            db.query(WellnessPlan)
            .filter(
                WellnessPlan.user_id == user_id,
                WellnessPlan.is_active,
            )
            .order_by(WellnessPlan.created_at.desc())
            .first()
        )

        if plan:
            return {"exists": True, "plan": plan.to_dict()}
        else:
            return {"exists": False, "plan": None}
    finally:
        db.close()


@app.get("/plan/{user_id}/history")
def get_plan_history(user_id: str, limit: int = 10) -> dict:
    """
    Get wellness plan history for a user.
    """
    db = get_session()
    try:
        plans = (
            db.query(WellnessPlan)
            .filter(WellnessPlan.user_id == user_id)
            .order_by(WellnessPlan.created_at.desc())
            .limit(limit)
            .all()
        )

        return {"plans": [p.to_dict() for p in plans]}
    finally:
        db.close()


@app.post("/checkin/weekly")
def conduct_checkin(req: WeeklyCheckInRequest) -> dict:
    """
    Conduct a weekly check-in assessment using LangGraph.
    """
    # Determine week start date
    if req.weekStartDate:
        try:
            week_start = datetime.fromisoformat(
                req.weekStartDate.replace("Z", "+00:00")
            )
        except Exception:
            week_start = datetime.utcnow() - timedelta(days=7)
    else:
        week_start = datetime.utcnow() - timedelta(days=7)

    week_end = week_start + timedelta(days=7)

    # Get habit history for the week
    db = get_session()
    try:
        logs = (
            db.query(DailyHabitLog)
            .filter(
                DailyHabitLog.user_id == req.userId,
                DailyHabitLog.date >= week_start.date(),
                DailyHabitLog.date < week_end.date(),
            )
            .order_by(DailyHabitLog.date)
            .all()
        )

        habit_history = []
        for log in logs:
            habit_history.append(
                {
                    "date": log.date.isoformat() if log.date else None,
                    "sleep_hours": log.sleep_hours,
                    "sleep_quality": log.sleep_quality,
                    "exercise_type": log.exercise_type,
                    "exercise_duration_minutes": log.exercise_duration_minutes,
                    "mood_score": log.mood_score,
                    "energy_level": log.energy_level,
                    "stress_level": log.stress_level,
                    "water_intake_liters": log.water_intake_liters,
                }
            )

        # Get previous plan
        previous_plan = None
        plan = (
            db.query(WellnessPlan)
            .filter(WellnessPlan.user_id == req.userId)
            .order_by(WellnessPlan.created_at.desc())
            .first()
        )
        if plan:
            previous_plan = plan.to_dict()
    finally:
        db.close()

    model_name = os.getenv("WELLNESS_MODEL", "gpt-4o-mini")
    # Get API key from request or environment
    api_key = req.openaiKey or os.getenv("OPENAI_API_KEY")
    checkin_result = conduct_weekly_checkin(
        profile=req.profile,
        habit_history=habit_history,
        previous_plan=previous_plan,
        model_name=model_name,
        api_key=api_key,
    )

    # Calculate summary metrics
    avg_sleep = None
    avg_mood = None
    total_exercise = None
    avg_energy = None

    if habit_history:
        sleep_hours = [h["sleep_hours"] for h in habit_history if h.get("sleep_hours")]
        mood_scores = [h["mood_score"] for h in habit_history if h.get("mood_score")]
        exercise_mins = [
            h["exercise_duration_minutes"]
            for h in habit_history
            if h.get("exercise_duration_minutes")
        ]
        energy_levels = [
            h["energy_level"] for h in habit_history if h.get("energy_level")
        ]

        avg_sleep = sum(sleep_hours) / len(sleep_hours) if sleep_hours else None
        avg_mood = sum(mood_scores) / len(mood_scores) if mood_scores else None
        total_exercise = sum(exercise_mins) if exercise_mins else None
        avg_energy = sum(energy_levels) / len(energy_levels) if energy_levels else None

    # Save check-in to database
    db = get_session()
    try:
        checkin = WeeklyCheckIn(
            user_id=req.userId,
            week_start_date=week_start,
            assessment_markdown=checkin_result.assessment_markdown,
            progress_summary=json.dumps(checkin_result.progress_summary),
            correlations_found=json.dumps(checkin_result.correlations_found),
            recommendations=json.dumps(checkin_result.recommendations),
            avg_sleep_hours=avg_sleep,
            avg_mood_score=avg_mood,
            total_exercise_minutes=total_exercise,
            avg_energy_level=avg_energy,
        )
        db.add(checkin)
        db.commit()
        db.refresh(checkin)

        # Save correlations to database
        for corr in checkin_result.correlations_found:
            correlation = Correlation(
                user_id=req.userId,
                metric1=corr.get("metric1", ""),
                metric2=corr.get("metric2", ""),
                correlation_type=corr.get("type", "positive"),
                strength=corr.get("strength", 0.5),
                description=corr.get("description", ""),
            )
            db.add(correlation)
        db.commit()

        return {
            "checkInId": checkin.id,
            "weekStartDate": week_start.isoformat(),
            "progressSummary": checkin_result.progress_summary,
            "correlationsFound": checkin_result.correlations_found,
            "recommendations": checkin_result.recommendations,
            "assessmentMarkdown": checkin_result.assessment_markdown,
            "avgSleepHours": avg_sleep,
            "avgMoodScore": avg_mood,
            "totalExerciseMinutes": total_exercise,
            "avgEnergyLevel": avg_energy,
        }
    finally:
        db.close()


@app.get("/checkin/{user_id}/history")
def get_checkin_history(user_id: str, limit: int = 10) -> dict:
    """
    Get weekly check-in history for a user.
    """
    db = get_session()
    try:
        checkins = (
            db.query(WeeklyCheckIn)
            .filter(WeeklyCheckIn.user_id == user_id)
            .order_by(WeeklyCheckIn.created_at.desc())
            .limit(limit)
            .all()
        )

        return {"checkIns": [c.to_dict() for c in checkins]}
    finally:
        db.close()


@app.get("/correlations/{user_id}")
def get_correlations(user_id: str) -> dict:
    """
    Get identified correlations for a user.
    """
    db = get_session()
    try:
        correlations = (
            db.query(Correlation)
            .filter(Correlation.user_id == user_id)
            .order_by(Correlation.strength.desc())
            .limit(20)
            .all()
        )

        return {"correlations": [c.to_dict() for c in correlations]}
    finally:
        db.close()


@app.post("/wellness/question")
def ask_wellness_question(req: WellnessQuestionRequest) -> dict:
    """
    Ask Memori about the user's wellness performance, patterns, and trends.
    """
    mgr = _get_memori_manager(req.userId, req.openaiKey)
    answer = mgr.summarize_wellness_performance(req.question)
    return {"answer": answer}


@app.get("/analytics/{user_id}")
def get_analytics(user_id: str, days: int = 30) -> dict:
    """
    Get comprehensive analytics for a user.
    """
    db = get_session()
    try:
        stats = get_habit_stats(db, user_id, days)
        weekly_activity = get_weekly_activity(db, user_id, weeks=12)

        return {
            "stats": stats,
            "weeklyActivity": weekly_activity,
        }
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
