"""
Database models and helpers for the Personal Finance Advisor application.
Stores transactions, budgets, goals, and financial assessments.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

Base = declarative_base()


class Transaction(Base):
    """Stores financial transactions."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Transaction details
    amount = Column(Float, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    merchant = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    transaction_type = Column(String(50), nullable=False)  # expense or income
    payment_method = Column(String(100), nullable=True)
    is_recurring = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "userId": self.user_id,
            "date": self.date.isoformat() if self.date else None,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "amount": self.amount,
            "category": self.category,
            "merchant": self.merchant,
            "description": self.description,
            "transactionType": self.transaction_type,
            "paymentMethod": self.payment_method,
            "isRecurring": self.is_recurring,
            "notes": self.notes,
        }


class Budget(Base):
    """Stores user budgets."""

    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Budget details
    category = Column(String(100), nullable=False)
    monthly_limit = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    is_active = Column(Boolean, default=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "userId": self.user_id,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "category": self.category,
            "monthlyLimit": self.monthly_limit,
            "currency": self.currency,
            "isActive": self.is_active,
        }


class FinancialGoal(Base):
    """Stores financial goals."""

    __tablename__ = "financial_goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Goal details
    name = Column(String(255), nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)
    target_date = Column(DateTime, nullable=True)
    priority = Column(String(50), default="Medium")  # High, Medium, Low
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    completed_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "userId": self.user_id,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "name": self.name,
            "targetAmount": self.target_amount,
            "currentAmount": self.current_amount,
            "targetDate": self.target_date.isoformat() if self.target_date else None,
            "priority": self.priority,
            "description": self.description,
            "isActive": self.is_active,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
        }


class FinancialHealthAssessment(Base):
    """Stores financial health assessments."""

    __tablename__ = "financial_health_assessments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Assessment results
    overall_score = Column(Float, nullable=False)
    assessment_markdown = Column(Text)
    spending_analysis = Column(Text)  # JSON
    budget_adherence = Column(Text)  # JSON
    goal_progress = Column(Text)  # JSON
    risk_factors = Column(Text)  # JSON array
    opportunities = Column(Text)  # JSON array
    recommendations = Column(Text)  # JSON array

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "userId": self.user_id,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "overallScore": self.overall_score,
            "assessmentMarkdown": self.assessment_markdown,
            "spendingAnalysis": (
                json.loads(self.spending_analysis) if self.spending_analysis else {}
            ),
            "budgetAdherence": (
                json.loads(self.budget_adherence) if self.budget_adherence else {}
            ),
            "goalProgress": (
                json.loads(self.goal_progress) if self.goal_progress else {}
            ),
            "riskFactors": json.loads(self.risk_factors) if self.risk_factors else [],
            "opportunities": (
                json.loads(self.opportunities) if self.opportunities else []
            ),
            "recommendations": (
                json.loads(self.recommendations) if self.recommendations else []
            ),
        }


class RecurringExpense(Base):
    """Stores identified recurring expenses."""

    __tablename__ = "recurring_expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Recurring expense details
    merchant = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    average_amount = Column(Float, nullable=False)
    frequency = Column(String(50), nullable=False)  # monthly, weekly, etc.
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    last_seen = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "userId": self.user_id,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "merchant": self.merchant,
            "category": self.category,
            "averageAmount": self.average_amount,
            "frequency": self.frequency,
            "confidence": self.confidence,
            "lastSeen": self.last_seen.isoformat() if self.last_seen else None,
        }


def get_engine():
    """Get SQLAlchemy engine for the finance advisor database."""
    db_path = (
        os.getenv("FINANCE_SQLITE_PATH")
        or os.getenv("SQLITE_DB_PATH")
        or "./memori_finance.sqlite"
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


# Analytics helpers
def get_transaction_stats(db: Session, user_id: str, days: int = 30) -> dict[str, Any]:
    """Get statistics for transactions over the last N days."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.date >= start_date,
        )
        .all()
    )

    if not transactions:
        return {
            "totalTransactions": 0,
            "totalIncome": 0.0,
            "totalExpenses": 0.0,
            "net": 0.0,
            "topCategories": [],
        }

    income = sum(t.amount for t in transactions if t.transaction_type == "income")
    expenses = sum(
        abs(t.amount) for t in transactions if t.transaction_type == "expense"
    )

    # Group by category
    category_totals = {}
    for t in transactions:
        if t.transaction_type == "expense":
            cat = t.category
            category_totals[cat] = category_totals.get(cat, 0) + abs(t.amount)

    top_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[
        :10
    ]

    return {
        "totalTransactions": len(transactions),
        "totalIncome": income,
        "totalExpenses": expenses,
        "net": income - expenses,
        "topCategories": [
            {"category": cat, "amount": amt} for cat, amt in top_categories
        ],
    }


def get_monthly_summary(db: Session, user_id: str, months: int = 6) -> list[dict]:
    """Get monthly transaction summaries for the last N months."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=months * 30)

    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.date >= start_date,
        )
        .all()
    )

    # Group by month
    monthly_data: dict[str, dict] = {}
    for t in transactions:
        month_key = t.date.strftime("%Y-%m")

        if month_key not in monthly_data:
            monthly_data[month_key] = {
                "income": 0.0,
                "expenses": 0.0,
            }

        if t.transaction_type == "income":
            monthly_data[month_key]["income"] += t.amount
        else:
            monthly_data[month_key]["expenses"] += abs(t.amount)

    # Convert to list
    result = []
    for month_key in sorted(monthly_data.keys()):
        data = monthly_data[month_key]
        result.append(
            {
                "month": month_key,
                "income": data["income"],
                "expenses": data["expenses"],
                "net": data["income"] - data["expenses"],
            }
        )

    return result


def get_budget_status(
    db: Session, user_id: str, month: str | None = None
) -> list[dict]:
    """Get current budget status for a user."""
    budgets = (
        db.query(Budget)
        .filter(
            Budget.user_id == user_id,
            Budget.is_active,
        )
        .all()
    )

    if not month:
        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1)
        month_end = (
            datetime(now.year, now.month + 1, 1)
            if now.month < 12
            else datetime(now.year + 1, 1, 1)
        )
    else:
        year, month_num = map(int, month.split("-"))
        month_start = datetime(year, month_num, 1)
        month_end = (
            datetime(year, month_num + 1, 1)
            if month_num < 12
            else datetime(year + 1, 1, 1)
        )

    result = []
    for budget in budgets:
        # Get transactions for this category in this month
        transactions = (
            db.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.category == budget.category,
                Transaction.transaction_type == "expense",
                Transaction.date >= month_start,
                Transaction.date < month_end,
            )
            .all()
        )

        spent = sum(abs(t.amount) for t in transactions)
        remaining = budget.monthly_limit - spent
        percentage = (
            (spent / budget.monthly_limit * 100) if budget.monthly_limit > 0 else 0
        )

        result.append(
            {
                "budgetId": budget.id,
                "category": budget.category,
                "monthlyLimit": budget.monthly_limit,
                "spent": spent,
                "remaining": remaining,
                "percentage": percentage,
                "isOverBudget": spent > budget.monthly_limit,
            }
        )

    return result
