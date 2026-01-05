"""
Database models and helpers for the Interview Prep application.
Stores problem attempts, bookmarks, study plans, and analytics data.
"""

import json
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

Base = declarative_base()


class ProblemAttempt(Base):
    """Stores each problem attempt with structured data for history/analytics."""

    __tablename__ = "problem_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )

    # Problem metadata
    title = Column(String(500), nullable=False)
    difficulty = Column(String(50), nullable=False)  # Easy, Medium, Hard
    patterns = Column(Text)  # JSON array of patterns
    statement = Column(Text)

    # Attempt details
    language = Column(String(50))
    code = Column(Text)
    hints_used = Column(Integer, default=0)

    # Evaluation results
    verdict = Column(String(50))  # correct, partially_correct, incorrect
    time_complexity = Column(String(50))
    space_complexity = Column(String(50))
    evaluation_markdown = Column(Text)

    # For spaced repetition
    next_review_at = Column(DateTime, nullable=True)
    review_interval_days = Column(Integer, default=1)
    ease_factor = Column(Float, default=2.5)

    # Company association (optional)
    company_style = Column(String(100), nullable=True)

    # Mock interview session (optional)
    mock_session_id = Column(String(100), nullable=True, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "userId": self.user_id,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "title": self.title,
            "difficulty": self.difficulty,
            "patterns": json.loads(self.patterns) if self.patterns else [],  # type: ignore[arg-type]
            "statement": self.statement,
            "language": self.language,
            "code": self.code,
            "hintsUsed": self.hints_used,
            "verdict": self.verdict,
            "timeComplexity": self.time_complexity,
            "spaceComplexity": self.space_complexity,
            "evaluationMarkdown": self.evaluation_markdown,
            "nextReviewAt": self.next_review_at.isoformat()
            if self.next_review_at
            else None,
            "reviewIntervalDays": self.review_interval_days,
            "companyStyle": self.company_style,
            "mockSessionId": self.mock_session_id,
        }


class Bookmark(Base):
    """Stores bookmarked problems in collections."""

    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    attempt_id = Column(Integer, ForeignKey("problem_attempts.id"), nullable=False)
    collection_name = Column(String(255), default="Saved")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "userId": self.user_id,
            "attemptId": self.attempt_id,
            "collectionName": self.collection_name,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "notes": self.notes,
        }


class MockInterviewSession(Base):
    """Stores mock interview sessions."""

    __tablename__ = "mock_interview_sessions"

    id = Column(String(100), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    # Session config
    session_type = Column(String(50))  # phone_screen, onsite, custom
    time_limit_minutes = Column(Integer, default=45)
    num_problems = Column(Integer, default=2)
    difficulties = Column(Text)  # JSON array

    # Results
    problems_completed = Column(Integer, default=0)
    total_score = Column(Float, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "userId": self.user_id,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "sessionType": self.session_type,
            "timeLimitMinutes": self.time_limit_minutes,
            "numProblems": self.num_problems,
            "difficulties": json.loads(self.difficulties) if self.difficulties else [],  # type: ignore[arg-type]
            "problemsCompleted": self.problems_completed,
            "totalScore": self.total_score,
        }


class StudyPlan(Base):
    """Stores generated study plans."""

    __tablename__ = "study_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Plan content
    week_number = Column(Integer, default=1)
    focus_patterns = Column(Text)  # JSON array
    daily_goal = Column(Integer, default=3)
    difficulty_focus = Column(String(50))
    plan_markdown = Column(Text)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "userId": self.user_id,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "weekNumber": self.week_number,
            "focusPatterns": json.loads(self.focus_patterns)  # type: ignore[arg-type]
            if self.focus_patterns
            else [],
            "dailyGoal": self.daily_goal,
            "difficultyFocus": self.difficulty_focus,
            "planMarkdown": self.plan_markdown,
        }


def get_engine():
    """Get SQLAlchemy engine for the interview prep database."""
    db_path = (
        os.getenv("INTERVIEW_SQLITE_PATH")
        or os.getenv("SQLITE_DB_PATH")
        or "./memori_interview.sqlite"
    )
    database_url = f"sqlite:///{db_path}"
    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False},
    )


def get_session() -> Session:
    """Get a new database session."""
    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def init_database():
    """Initialize database tables."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


# Spaced Repetition helpers
def calculate_next_review(attempt: ProblemAttempt, was_correct: bool) -> datetime:
    """
    Calculate next review date using SM-2 algorithm variant.
    """
    if was_correct:
        new_interval = int(attempt.review_interval_days * attempt.ease_factor)  # type: ignore[arg-type]
        new_ease = min(2.5, attempt.ease_factor + 0.1)
    else:
        new_interval = 1  # Reset to 1 day
        new_ease = max(1.3, attempt.ease_factor - 0.2)

    attempt.review_interval_days = new_interval
    attempt.ease_factor = new_ease
    attempt.next_review_at = datetime.now(timezone.utc) + timedelta(days=new_interval)

    return attempt.next_review_at


def get_due_problems(
    db: Session, user_id: str, limit: int = 10
) -> list[ProblemAttempt]:
    """Get problems due for review (spaced repetition)."""
    now = datetime.now(timezone.utc)
    return (
        db.query(ProblemAttempt)
        .filter(
            ProblemAttempt.user_id == user_id,
            ProblemAttempt.next_review_at <= now,
        )
        .order_by(ProblemAttempt.next_review_at)
        .limit(limit)
        .all()
    )


# Analytics helpers
def get_pattern_stats(db: Session, user_id: str) -> dict[str, dict]:
    """Get statistics by pattern for a user."""
    attempts = db.query(ProblemAttempt).filter(ProblemAttempt.user_id == user_id).all()

    pattern_stats: dict[str, dict] = {}

    for attempt in attempts:
        patterns = json.loads(attempt.patterns) if attempt.patterns else []  # type: ignore[arg-type]
        for pattern in patterns:
            if pattern not in pattern_stats:
                pattern_stats[pattern] = {
                    "total": 0,
                    "correct": 0,
                    "incorrect": 0,
                    "partial": 0,
                }
            pattern_stats[pattern]["total"] += 1
            if attempt.verdict == "correct":
                pattern_stats[pattern]["correct"] += 1
            elif attempt.verdict == "incorrect":
                pattern_stats[pattern]["incorrect"] += 1
            else:
                pattern_stats[pattern]["partial"] += 1

    return pattern_stats


def get_difficulty_stats(db: Session, user_id: str) -> dict[str, dict]:
    """Get statistics by difficulty for a user."""
    attempts = db.query(ProblemAttempt).filter(ProblemAttempt.user_id == user_id).all()

    stats = {
        "Easy": {"total": 0, "correct": 0},
        "Medium": {"total": 0, "correct": 0},
        "Hard": {"total": 0, "correct": 0},
    }

    for attempt in attempts:
        diff = attempt.difficulty
        if diff in stats:
            stats[diff]["total"] += 1
            if attempt.verdict == "correct":
                stats[diff]["correct"] += 1

    return stats


def get_weekly_activity(db: Session, user_id: str, weeks: int = 12) -> list[dict]:
    """Get weekly problem count for the last N weeks."""
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(weeks=weeks)

    attempts = (
        db.query(ProblemAttempt)
        .filter(
            ProblemAttempt.user_id == user_id,
            ProblemAttempt.created_at >= start_date,
        )
        .all()
    )

    # Group by week
    weekly_data: dict[str, int] = {}
    for attempt in attempts:
        week_start = attempt.created_at - timedelta(days=attempt.created_at.weekday())
        week_key = week_start.strftime("%Y-%m-%d")
        weekly_data[week_key] = weekly_data.get(week_key, 0) + 1

    # Fill in missing weeks
    result = []
    current = start_date
    while current <= end_date:
        week_key = current.strftime("%Y-%m-%d")
        result.append(
            {
                "week": week_key,
                "count": weekly_data.get(week_key, 0),
            }
        )
        current += timedelta(weeks=1)

    return result
