import json
import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from core import (
    CandidateProfile,
    ProblemMetadata,
    evaluate_solution,
    format_attempt_summary,
    generate_hint,
    generate_personalized_problem,
)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from memory_utils import MemoriManager
from pydantic import BaseModel

from backend.database import (
    Bookmark,
    MockInterviewSession,
    ProblemAttempt,
    StudyPlan,
    calculate_next_review,
    get_difficulty_stats,
    get_due_problems,
    get_pattern_stats,
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
    profile: CandidateProfile | None = None


class ProfileRequest(BaseModel):
    userId: str
    profile: CandidateProfile
    openaiKey: str | None = None
    memoriKey: str | None = None


class ProblemRequest(BaseModel):
    userId: str
    profile: CandidateProfile
    difficulty: str
    patterns: list[str] = []
    openaiKey: str | None = None
    memoriKey: str | None = None


class HintRequest(BaseModel):
    userId: str
    problem: ProblemMetadata
    language: str
    codeSoFar: str
    hintIndex: int
    openaiKey: str | None = None
    memoriKey: str | None = None


class EvaluateRequest(BaseModel):
    userId: str
    profile: CandidateProfile
    problem: ProblemMetadata
    language: str
    candidateCode: str
    hints: list[str] = []
    openaiKey: str | None = None
    memoriKey: str | None = None


class ProgressQuestionRequest(BaseModel):
    userId: str
    question: str
    openaiKey: str | None = None
    memoriKey: str | None = None


class UsageResponse(BaseModel):
    success: bool = True


# --- New request/response models for features ---


class SaveAttemptRequest(BaseModel):
    userId: str
    problem: ProblemMetadata
    language: str
    code: str
    hintsUsed: int
    verdict: str  # correct, partially_correct, incorrect
    timeComplexity: str | None = None
    spaceComplexity: str | None = None
    evaluationMarkdown: str
    companyStyle: str | None = None
    mockSessionId: str | None = None


class HistoryFilter(BaseModel):
    userId: str
    difficulty: str | None = None
    pattern: str | None = None
    verdict: str | None = None
    companyStyle: str | None = None
    limit: int = 50
    offset: int = 0


class BookmarkRequest(BaseModel):
    userId: str
    attemptId: int
    collectionName: str = "Saved"
    notes: str | None = None


class MockSessionRequest(BaseModel):
    userId: str
    sessionType: str  # phone_screen, onsite, custom
    timeLimitMinutes: int = 45
    numProblems: int = 2
    difficulties: list[str] = []
    openaiKey: str | None = None
    memoriKey: str | None = None


class StudyPlanRequest(BaseModel):
    userId: str
    profile: CandidateProfile
    openaiKey: str | None = None
    memoriKey: str | None = None


class CompanyProblemRequest(BaseModel):
    userId: str
    profile: CandidateProfile
    company: str
    difficulty: str = "Medium"
    openaiKey: str | None = None
    memoriKey: str | None = None


def _get_memori_manager(
    user_id: str,
    openai_key_override: str | None = None,
    memori_key_override: str | None = None,
) -> MemoriManager:
    """
    Create a MemoriManager for the given logical user id.

    If the caller provides their own OpenAI key, we use that instead of the env var.
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

    # memori_key_override is accepted for future use / Memori cloud features
    # For now, Memori uses the OpenAI key for embeddings, so we just pass openai_key.
    mgr = MemoriManager(
        openai_api_key=openai_key,
        sqlite_path=os.getenv("INTERVIEW_SQLITE_PATH") or "./memori_interview.sqlite",
        entity_id=user_id,
    )
    return mgr


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Initialize database tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up - initializing database...")
    try:
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    yield
    # Shutdown (if needed)
    logger.info("Shutting down...")


app = FastAPI(title="Technical Interview Prep API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
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
    - Load the latest candidate profile, if any.
    """
    mgr = _get_memori_manager(req.userId, req.openaiKey)

    profile_dict = mgr.get_latest_candidate_profile()
    profile: CandidateProfile | None = None
    if profile_dict is not None:
        try:
            profile = CandidateProfile(**profile_dict)
        except Exception:
            profile = None

    return InitResponse(profile=profile)


@app.post("/profile", response_model=UsageResponse)
def save_profile(req: ProfileRequest) -> UsageResponse:
    """
    Save the candidate profile into Memori for this user.
    """
    mgr = _get_memori_manager(req.userId, req.openaiKey)
    mgr.log_candidate_profile(req.profile.model_dump())
    return UsageResponse(success=True)


@app.post("/problem", response_model=ProblemMetadata)
def generate_problem(req: ProblemRequest) -> ProblemMetadata:
    """
    Generate a personalized problem for the candidate, considering:
    - Their profile
    - Desired difficulty and patterns
    - Weakness summary from prior attempts (queried via Memori)
    """
    mgr = _get_memori_manager(req.userId, req.openaiKey)

    weakness_context = ""
    try:
        weakness_context = mgr.summarize_performance(
            "In 3–5 bullet points, summarize my weakest algorithm/data-structure "
            "patterns and typical difficulties."
        )
    except Exception:
        weakness_context = ""

    model_name = os.getenv("INTERVIEW_MODEL", "gpt-4o-mini")
    problem = generate_personalized_problem(
        profile=req.profile,
        difficulty=req.difficulty,
        patterns=req.patterns,
        weakness_context=weakness_context,
        model_name=model_name,
    )
    return problem


@app.post("/hint")
def generate_hint_endpoint(req: HintRequest) -> dict:
    """
    Generate an incremental hint for the current attempt.
    """
    _get_memori_manager(req.userId, req.openaiKey)  # Validate API key

    model_name = os.getenv("INTERVIEW_MODEL", "gpt-4o-mini")
    hint = generate_hint(
        problem=req.problem,
        language=req.language,
        code_so_far=req.codeSoFar,
        hint_index=req.hintIndex,
        model_name=model_name,
    )
    return {"hint": hint}


@app.post("/evaluate")
def evaluate_solution_endpoint(req: EvaluateRequest) -> dict:
    """
    Evaluate the candidate's solution and log the attempt into Memori.
    Also saves to database for history/analytics.
    """
    mgr = _get_memori_manager(req.userId, req.openaiKey)

    model_name = os.getenv("INTERVIEW_MODEL", "gpt-4o-mini")
    evaluation_md = evaluate_solution(
        problem=req.problem,
        language=req.language,
        candidate_code=req.candidateCode,
        model_name=model_name,
    )

    attempt_summary = format_attempt_summary(
        profile=req.profile,
        problem=req.problem,
        language=req.language,
        candidate_code=req.candidateCode,
        hints=req.hints,
        evaluation_markdown=evaluation_md,
    )
    mgr.log_problem_attempt(attempt_summary)

    # Parse verdict from evaluation (look for patterns like "correct", "incorrect", "partially")
    verdict = "partially_correct"
    eval_lower = evaluation_md.lower()
    if "incorrect" in eval_lower or "wrong" in eval_lower:
        verdict = "incorrect"
    elif "correct" in eval_lower and "partially" not in eval_lower:
        verdict = "correct"

    # Extract complexity if mentioned
    time_complexity = None
    space_complexity = None
    time_match = re.search(r"O\([^)]+\)", evaluation_md)
    if time_match:
        time_complexity = time_match.group(0)

    # Save to database for history/analytics
    db = get_session()
    try:
        attempt = ProblemAttempt(
            user_id=req.userId,
            title=req.problem.title,
            difficulty=req.problem.difficulty,
            patterns=json.dumps(req.problem.patterns),
            statement=req.problem.statement,
            language=req.language,
            code=req.candidateCode,
            hints_used=len(req.hints),
            verdict=verdict,
            time_complexity=time_complexity,
            space_complexity=space_complexity,
            evaluation_markdown=evaluation_md,
            next_review_at=datetime.now(timezone.utc),
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)

        # Calculate next review
        calculate_next_review(attempt, verdict == "correct")
        db.commit()

        attempt_id = attempt.id
    finally:
        db.close()

    return {
        "evaluationMarkdown": evaluation_md,
        "attemptId": attempt_id,
        "verdict": verdict,
    }


@app.post("/progress")
def summarize_progress(req: ProgressQuestionRequest) -> dict:
    """
    Ask Memori about the user's interview performance, weaknesses, and trends.
    """
    mgr = _get_memori_manager(req.userId, req.openaiKey)
    answer = mgr.summarize_performance(req.question)
    return {"answer": answer}


# ============================================
# PROBLEM HISTORY & RETRY
# ============================================


@app.post("/attempts/save")
def save_attempt(req: SaveAttemptRequest) -> dict:
    """Save a problem attempt to the database for history/analytics."""
    db = get_session()
    try:
        attempt = ProblemAttempt(
            user_id=req.userId,
            title=req.problem.title,
            difficulty=req.problem.difficulty,
            patterns=json.dumps(req.problem.patterns),
            statement=req.problem.statement,
            language=req.language,
            code=req.code,
            hints_used=req.hintsUsed,
            verdict=req.verdict,
            time_complexity=req.timeComplexity,
            space_complexity=req.spaceComplexity,
            evaluation_markdown=req.evaluationMarkdown,
            company_style=req.companyStyle,
            mock_session_id=req.mockSessionId,
            next_review_at=datetime.now(
                timezone.utc
            ),  # Due immediately for first review
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)

        # Calculate next review based on verdict
        was_correct = req.verdict == "correct"
        calculate_next_review(attempt, was_correct)
        db.commit()

        return {"success": True, "attemptId": attempt.id}
    finally:
        db.close()


@app.post("/attempts/history")
def get_history(req: HistoryFilter) -> dict:
    """Get problem attempt history with optional filters."""
    db = get_session()
    try:
        query = db.query(ProblemAttempt).filter(ProblemAttempt.user_id == req.userId)

        if req.difficulty:
            query = query.filter(ProblemAttempt.difficulty == req.difficulty)
        if req.verdict:
            query = query.filter(ProblemAttempt.verdict == req.verdict)
        if req.companyStyle:
            query = query.filter(ProblemAttempt.company_style == req.companyStyle)
        if req.pattern:
            query = query.filter(ProblemAttempt.patterns.contains(req.pattern))

        total = query.count()
        attempts = (
            query.order_by(ProblemAttempt.created_at.desc())
            .offset(req.offset)
            .limit(req.limit)
            .all()
        )

        return {
            "total": total,
            "attempts": [a.to_dict() for a in attempts],
        }
    finally:
        db.close()


@app.get("/attempts/{attempt_id}")
def get_attempt(attempt_id: int) -> dict:
    """Get a single attempt by ID for retry."""
    db = get_session()
    try:
        attempt = (
            db.query(ProblemAttempt).filter(ProblemAttempt.id == attempt_id).first()
        )
        if not attempt:
            raise HTTPException(status_code=404, detail="Attempt not found")
        return attempt.to_dict()
    finally:
        db.close()


# ============================================
# SPACED REPETITION
# ============================================


@app.get("/review/due/{user_id}")
def get_due_for_review(user_id: str, limit: int = 10) -> dict:
    """Get problems due for spaced repetition review."""
    db = get_session()
    try:
        due = get_due_problems(db, user_id, limit)
        return {
            "dueCount": len(due),
            "problems": [a.to_dict() for a in due],
        }
    finally:
        db.close()


@app.post("/review/complete/{attempt_id}")
def complete_review(attempt_id: int, was_correct: bool) -> dict:
    """Mark a review as complete and calculate next review date."""
    db = get_session()
    try:
        attempt = (
            db.query(ProblemAttempt).filter(ProblemAttempt.id == attempt_id).first()
        )
        if not attempt:
            raise HTTPException(status_code=404, detail="Attempt not found")

        next_review = calculate_next_review(attempt, was_correct)
        db.commit()

        return {
            "success": True,
            "nextReviewAt": next_review.isoformat(),
            "intervalDays": attempt.review_interval_days,
        }
    finally:
        db.close()


# ============================================
# BOOKMARKS & COLLECTIONS
# ============================================


@app.post("/bookmarks/add")
def add_bookmark(req: BookmarkRequest) -> dict:
    """Add a problem to a bookmark collection."""
    db = get_session()
    try:
        # Check if already bookmarked
        existing = (
            db.query(Bookmark)
            .filter(
                Bookmark.user_id == req.userId,
                Bookmark.attempt_id == req.attemptId,
                Bookmark.collection_name == req.collectionName,
            )
            .first()
        )

        if existing:
            return {
                "success": True,
                "bookmarkId": existing.id,
                "message": "Already bookmarked",
            }

        bookmark = Bookmark(
            user_id=req.userId,
            attempt_id=req.attemptId,
            collection_name=req.collectionName,
            notes=req.notes,
        )
        db.add(bookmark)
        db.commit()
        db.refresh(bookmark)

        return {"success": True, "bookmarkId": bookmark.id}
    finally:
        db.close()


@app.get("/bookmarks/{user_id}")
def get_bookmarks(user_id: str, collection: str | None = None) -> dict:
    """Get all bookmarks for a user, optionally filtered by collection."""
    db = get_session()
    try:
        query = db.query(Bookmark).filter(Bookmark.user_id == user_id)
        if collection:
            query = query.filter(Bookmark.collection_name == collection)

        bookmarks = query.order_by(Bookmark.created_at.desc()).all()

        # Get unique collection names
        collections = (
            db.query(Bookmark.collection_name)
            .filter(Bookmark.user_id == user_id)
            .distinct()
            .all()
        )

        return {
            "bookmarks": [b.to_dict() for b in bookmarks],
            "collections": [c[0] for c in collections],
        }
    finally:
        db.close()


@app.delete("/bookmarks/{bookmark_id}")
def delete_bookmark(bookmark_id: int) -> dict:
    """Remove a bookmark."""
    db = get_session()
    try:
        bookmark = db.query(Bookmark).filter(Bookmark.id == bookmark_id).first()
        if bookmark:
            db.delete(bookmark)
            db.commit()
        return {"success": True}
    finally:
        db.close()


# ============================================
# MOCK INTERVIEW MODE
# ============================================


@app.post("/mock/start")
def start_mock_session(req: MockSessionRequest) -> dict:
    """Start a new mock interview session."""
    db = get_session()
    try:
        session_id = str(uuid.uuid4())

        # Determine difficulties based on session type
        if not req.difficulties:
            if req.sessionType == "phone_screen":
                difficulties = ["Easy", "Medium"]
            elif req.sessionType == "onsite":
                difficulties = ["Medium", "Medium", "Hard"]
            else:
                difficulties = ["Medium"] * req.numProblems
        else:
            difficulties = req.difficulties

        session = MockInterviewSession(
            id=session_id,
            user_id=req.userId,
            session_type=req.sessionType,
            time_limit_minutes=req.timeLimitMinutes,
            num_problems=len(difficulties),
            difficulties=json.dumps(difficulties),
        )
        db.add(session)
        db.commit()

        return {
            "sessionId": session_id,
            "timeLimitMinutes": req.timeLimitMinutes,
            "numProblems": len(difficulties),
            "difficulties": difficulties,
        }
    finally:
        db.close()


@app.get("/mock/session/{session_id}")
def get_mock_session(session_id: str) -> dict:
    """Get mock session details."""
    db = get_session()
    try:
        session = (
            db.query(MockInterviewSession)
            .filter(MockInterviewSession.id == session_id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get problems for this session
        problems = (
            db.query(ProblemAttempt)
            .filter(ProblemAttempt.mock_session_id == session_id)
            .all()
        )

        return {
            **session.to_dict(),
            "problems": [p.to_dict() for p in problems],
        }
    finally:
        db.close()


@app.post("/mock/complete/{session_id}")
def complete_mock_session(session_id: str) -> dict:
    """Complete a mock interview session and calculate score."""
    db = get_session()
    try:
        session = (
            db.query(MockInterviewSession)
            .filter(MockInterviewSession.id == session_id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get problems and calculate score
        problems = (
            db.query(ProblemAttempt)
            .filter(ProblemAttempt.mock_session_id == session_id)
            .all()
        )

        total_score = 0
        for p in problems:
            if p.verdict == "correct":
                total_score += 100
            elif p.verdict == "partially_correct":
                total_score += 50

        if problems:
            total_score = total_score / len(problems)

        session.completed_at = datetime.now(timezone.utc)
        session.problems_completed = len(problems)
        session.total_score = total_score
        db.commit()

        return {
            "success": True,
            "score": total_score,
            "problemsCompleted": len(problems),
        }
    finally:
        db.close()


@app.get("/mock/history/{user_id}")
def get_mock_history(user_id: str) -> dict:
    """Get mock interview session history."""
    db = get_session()
    try:
        sessions = (
            db.query(MockInterviewSession)
            .filter(MockInterviewSession.user_id == user_id)
            .order_by(MockInterviewSession.created_at.desc())
            .limit(20)
            .all()
        )

        return {"sessions": [s.to_dict() for s in sessions]}
    finally:
        db.close()


# ============================================
# ANALYTICS
# ============================================


@app.get("/analytics/{user_id}")
def get_analytics(user_id: str) -> dict:
    """Get comprehensive analytics for a user."""
    db = get_session()
    try:
        pattern_stats = get_pattern_stats(db, user_id)
        difficulty_stats = get_difficulty_stats(db, user_id)
        weekly_activity = get_weekly_activity(db, user_id)

        # Total counts
        total_attempts = (
            db.query(ProblemAttempt).filter(ProblemAttempt.user_id == user_id).count()
        )

        correct_attempts = (
            db.query(ProblemAttempt)
            .filter(
                ProblemAttempt.user_id == user_id,
                ProblemAttempt.verdict == "correct",
            )
            .count()
        )

        return {
            "totalAttempts": total_attempts,
            "correctAttempts": correct_attempts,
            "accuracy": (
                round(correct_attempts / total_attempts * 100, 1)
                if total_attempts > 0
                else 0
            ),
            "patternStats": pattern_stats,
            "difficultyStats": difficulty_stats,
            "weeklyActivity": weekly_activity,
        }
    finally:
        db.close()


# ============================================
# COMPANY-SPECIFIC PROBLEMS
# ============================================


@app.post("/problem/company")
def generate_company_problem(req: CompanyProblemRequest) -> ProblemMetadata:
    """Generate a problem tailored to a specific company's interview style."""
    _get_memori_manager(req.userId, req.openaiKey)  # Validate API key

    # Company-specific patterns
    company_patterns = {
        "Google": ["graphs", "dynamic programming", "system design", "arrays"],
        "Meta": ["graphs", "trees", "dynamic programming", "strings"],
        "Amazon": ["arrays", "trees", "system design", "OOP"],
        "Apple": ["arrays", "strings", "linked list", "system design"],
        "Microsoft": ["arrays", "trees", "dynamic programming", "graphs"],
        "Netflix": ["system design", "distributed systems", "caching"],
        "Stripe": ["API design", "strings", "hashing", "system design"],
    }

    patterns = company_patterns.get(req.company, ["arrays", "strings", "trees"])

    model_name = os.getenv("INTERVIEW_MODEL", "gpt-4o-mini")
    problem = generate_personalized_problem(
        profile=req.profile,
        difficulty=req.difficulty,
        patterns=patterns[:3],  # Focus on top 3 patterns
        weakness_context=f"This problem should be in the style of {req.company} interviews.",
        model_name=model_name,
    )

    return problem


# ============================================
# STUDY PLAN GENERATOR
# ============================================


@app.post("/study-plan/generate")
def generate_study_plan(req: StudyPlanRequest) -> dict:
    """Generate a personalized weekly study plan."""
    mgr = _get_memori_manager(req.userId, req.openaiKey)

    # Get analytics to inform the plan
    db = get_session()
    try:
        pattern_stats = get_pattern_stats(db, req.userId)
        difficulty_stats = get_difficulty_stats(db, req.userId)

        # Find weak patterns
        weak_patterns = []
        for pattern, stats in pattern_stats.items():
            if stats["total"] > 0:
                accuracy = stats["correct"] / stats["total"]
                if accuracy < 0.6:
                    weak_patterns.append(pattern)

        if not weak_patterns:
            weak_patterns = ["arrays", "strings", "trees"]

        # Generate plan using LLM
        prompt = f"""Generate a 1-week study plan for a technical interview candidate.

Profile:
- Target role: {req.profile.target_role}
- Experience: {req.profile.experience_level}
- Target companies: {", ".join(req.profile.target_companies) or "FAANG"}
- Timeframe: {req.profile.timeframe}
- Goal: {req.profile.main_goal}

Weak patterns that need focus: {", ".join(weak_patterns[:5])}

Current stats:
- Easy: {difficulty_stats.get("Easy", {}).get("correct", 0)}/{difficulty_stats.get("Easy", {}).get("total", 0)} correct
- Medium: {difficulty_stats.get("Medium", {}).get("correct", 0)}/{difficulty_stats.get("Medium", {}).get("total", 0)} correct
- Hard: {difficulty_stats.get("Hard", {}).get("correct", 0)}/{difficulty_stats.get("Hard", {}).get("total", 0)} correct

Create a day-by-day plan for 7 days with:
1. Which patterns to focus on each day
2. Recommended difficulty level
3. Number of problems to solve
4. Any specific tips

Format as markdown."""

        response = mgr.openai_client.chat.completions.create(
            model=os.getenv("INTERVIEW_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert technical interview coach.",
                },
                {"role": "user", "content": prompt},
            ],
        )

        plan_markdown = response.choices[0].message.content or ""

        # Save the plan
        plan = StudyPlan(
            user_id=req.userId,
            focus_patterns=json.dumps(weak_patterns[:5]),
            daily_goal=3,
            difficulty_focus="Medium",
            plan_markdown=plan_markdown,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

        return {
            "planId": plan.id,
            "weekNumber": plan.week_number,
            "focusPatterns": weak_patterns[:5],
            "planMarkdown": plan_markdown,
        }
    finally:
        db.close()


@app.get("/study-plan/{user_id}")
def get_study_plans(user_id: str) -> dict:
    """Get study plans for a user."""
    db = get_session()
    try:
        plans = (
            db.query(StudyPlan)
            .filter(StudyPlan.user_id == user_id)
            .order_by(StudyPlan.created_at.desc())
            .limit(5)
            .all()
        )

        return {"plans": [p.to_dict() for p in plans]}
    finally:
        db.close()


# ============================================
# EXPORT
# ============================================


@app.get("/export/{user_id}/markdown", response_class=PlainTextResponse)
def export_markdown(user_id: str) -> str:
    """Export practice history as Markdown."""
    db = get_session()
    try:
        attempts = (
            db.query(ProblemAttempt)
            .filter(ProblemAttempt.user_id == user_id)
            .order_by(ProblemAttempt.created_at.desc())
            .all()
        )

        pattern_stats = get_pattern_stats(db, user_id)
        difficulty_stats = get_difficulty_stats(db, user_id)

        # Build markdown
        md = "# Interview Practice History\n\n"
        md += f"**User:** {user_id}\n"
        md += f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"

        # Summary
        md += "## Summary\n\n"
        md += f"- **Total Problems:** {len(attempts)}\n"
        correct = sum(1 for a in attempts if a.verdict == "correct")
        md += f"- **Correct:** {correct} ({round(correct / len(attempts) * 100, 1) if attempts else 0}%)\n\n"

        # By difficulty
        md += "### By Difficulty\n\n"
        md += "| Difficulty | Solved | Correct |\n"
        md += "|------------|--------|--------|\n"
        for diff in ["Easy", "Medium", "Hard"]:
            stats = difficulty_stats.get(diff, {"total": 0, "correct": 0})
            md += f"| {diff} | {stats['total']} | {stats['correct']} |\n"

        # By pattern
        md += "\n### By Pattern\n\n"
        md += "| Pattern | Total | Correct | Accuracy |\n"
        md += "|---------|-------|---------|----------|\n"
        for pattern, stats in sorted(
            pattern_stats.items(), key=lambda x: x[1]["total"], reverse=True
        )[:10]:
            acc = (
                round(stats["correct"] / stats["total"] * 100, 1)
                if stats["total"] > 0
                else 0
            )
            md += f"| {pattern} | {stats['total']} | {stats['correct']} | {acc}% |\n"

        # Recent problems
        md += "\n## Recent Problems\n\n"
        for attempt in attempts[:20]:
            md += f"### {attempt.title}\n\n"
            md += f"- **Difficulty:** {attempt.difficulty}\n"
            md += f"- **Patterns:** {', '.join(json.loads(attempt.patterns) if attempt.patterns else [])}\n"
            md += f"- **Verdict:** {attempt.verdict}\n"
            md += f"- **Date:** {attempt.created_at.strftime('%Y-%m-%d')}\n\n"

        return md
    finally:
        db.close()


@app.get("/export/{user_id}/resume-bullets")
def export_resume_bullets(user_id: str) -> dict:
    """Generate resume bullet points from practice history."""
    db = get_session()
    try:
        attempts = (
            db.query(ProblemAttempt).filter(ProblemAttempt.user_id == user_id).all()
        )

        pattern_stats = get_pattern_stats(db, user_id)

        total = len(attempts)
        correct = sum(1 for a in attempts if a.verdict == "correct")
        patterns_count = len(pattern_stats)

        bullets = [
            f"Solved {total}+ algorithmic coding challenges across {patterns_count} data structure and algorithm patterns",
            f"Achieved {round(correct / total * 100) if total else 0}% success rate on technical interview problems",
        ]

        # Add pattern-specific bullets
        top_patterns = sorted(
            pattern_stats.items(), key=lambda x: x[1]["total"], reverse=True
        )[:3]
        if top_patterns:
            pattern_names = [p[0] for p in top_patterns]
            bullets.append(
                f"Demonstrated proficiency in {', '.join(pattern_names)} problem-solving techniques"
            )

        return {"bullets": bullets}
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
