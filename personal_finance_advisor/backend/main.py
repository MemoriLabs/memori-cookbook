import json
import logging
import os
from datetime import datetime

from core import (
    Budget,
    FinancialGoal,
    FinancialProfile,
    Transaction,
    conduct_financial_health_assessment,
    format_transaction_summary,
    generate_goal_setting_plan,
    identify_recurring_expenses,
)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from memory_utils import MemoriManager
from pydantic import BaseModel

from backend.database import (
    Budget as BudgetModel,
)
from backend.database import (
    FinancialGoal as FinancialGoalModel,
)
from backend.database import (
    FinancialHealthAssessment,
    RecurringExpense,
    get_budget_status,
    get_monthly_summary,
    get_session,
    get_transaction_stats,
    init_database,
)
from backend.database import (
    Transaction as TransactionModel,
)

# --- Request / Response models ---


class InitRequest(BaseModel):
    userId: str
    openaiKey: str | None = None
    memoriKey: str | None = None


class InitResponse(BaseModel):
    profile: FinancialProfile | None = None


class ProfileRequest(BaseModel):
    userId: str
    profile: FinancialProfile
    openaiKey: str | None = None
    memoriKey: str | None = None


class LogTransactionRequest(BaseModel):
    userId: str
    transaction: Transaction
    openaiKey: str | None = None
    memoriKey: str | None = None


class GetTransactionsRequest(BaseModel):
    userId: str
    startDate: str | None = None  # ISO date string
    endDate: str | None = None  # ISO date string
    category: str | None = None
    limit: int = 100


class CreateBudgetRequest(BaseModel):
    userId: str
    budget: Budget


class CreateGoalRequest(BaseModel):
    userId: str
    goal: FinancialGoal


class FinancialHealthRequest(BaseModel):
    userId: str
    profile: FinancialProfile
    openaiKey: str | None = None
    memoriKey: str | None = None


class GoalSettingRequest(BaseModel):
    userId: str
    profile: FinancialProfile
    openaiKey: str | None = None
    memoriKey: str | None = None


class FinanceQuestionRequest(BaseModel):
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
        sqlite_path=os.getenv("FINANCE_SQLITE_PATH") or "./memori_finance.sqlite",
        entity_id=user_id,
    )
    return mgr


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Personal Finance Advisor API")


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
    - Load the latest financial profile, if any.
    """
    mgr = _get_memori_manager(req.userId, req.openaiKey)

    profile_dict = mgr.get_latest_financial_profile()
    profile: FinancialProfile | None = None
    if profile_dict is not None:
        try:
            profile = FinancialProfile(**profile_dict)
        except Exception:
            profile = None

    return InitResponse(profile=profile)


@app.post("/profile", response_model=UsageResponse)
def save_profile(req: ProfileRequest) -> UsageResponse:
    """
    Save the financial profile into Memori for this user.
    """
    mgr = _get_memori_manager(req.userId, req.openaiKey)
    mgr.log_financial_profile(req.profile.model_dump())
    return UsageResponse(success=True)


@app.post("/transactions/log")
def log_transaction(req: LogTransactionRequest) -> dict:
    """
    Log a financial transaction.
    """
    mgr = _get_memori_manager(req.userId, req.openaiKey)

    # Parse date
    try:
        transaction_date = datetime.fromisoformat(
            req.transaction.date.replace("Z", "+00:00")
        )
    except Exception:
        transaction_date = datetime.utcnow()

    # Get profile for Memori logging
    profile_dict = mgr.get_latest_financial_profile()
    if profile_dict:
        profile = FinancialProfile(**profile_dict)
    else:
        # Create a minimal profile
        profile = FinancialProfile(name=req.userId, currency="USD")

    # Format summary for Memori
    transaction_summary = format_transaction_summary(profile, req.transaction)
    mgr.log_transaction(transaction_summary)

    # Save to database
    db = get_session()
    try:
        transaction = TransactionModel(
            user_id=req.userId,
            date=transaction_date,
            amount=req.transaction.amount,
            category=req.transaction.category,
            merchant=req.transaction.merchant,
            description=req.transaction.description,
            transaction_type=req.transaction.transaction_type,
            payment_method=req.transaction.payment_method,
            is_recurring=req.transaction.is_recurring,
            notes=req.transaction.notes,
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        return {"success": True, "transactionId": transaction.id}
    finally:
        db.close()


@app.post("/transactions/get")
def get_transactions(req: GetTransactionsRequest) -> dict:
    """
    Get transactions for a user, optionally filtered by date range and category.
    """
    db = get_session()
    try:
        query = db.query(TransactionModel).filter(
            TransactionModel.user_id == req.userId
        )

        if req.startDate:
            try:
                start = datetime.fromisoformat(req.startDate.replace("Z", "+00:00"))
                query = query.filter(TransactionModel.date >= start)
            except Exception:
                pass

        if req.endDate:
            try:
                end = datetime.fromisoformat(req.endDate.replace("Z", "+00:00"))
                query = query.filter(TransactionModel.date <= end)
            except Exception:
                pass

        if req.category:
            query = query.filter(TransactionModel.category == req.category)

        transactions = (
            query.order_by(TransactionModel.date.desc()).limit(req.limit).all()
        )

        return {
            "total": len(transactions),
            "transactions": [t.to_dict() for t in transactions],
        }
    finally:
        db.close()


@app.post("/budgets/create")
def create_budget(req: CreateBudgetRequest) -> dict:
    """
    Create a new budget.
    """
    db = get_session()
    try:
        # Check if budget already exists for this category
        existing = (
            db.query(BudgetModel)
            .filter(
                BudgetModel.user_id == req.userId,
                BudgetModel.category == req.budget.category,
                BudgetModel.is_active,
            )
            .first()
        )

        if existing:
            existing.monthly_limit = req.budget.monthly_limit
            existing.currency = req.budget.currency
            db.commit()
            db.refresh(existing)
            return {"success": True, "budgetId": existing.id, "updated": True}
        else:
            budget = BudgetModel(
                user_id=req.userId,
                category=req.budget.category,
                monthly_limit=req.budget.monthly_limit,
                currency=req.budget.currency,
            )
            db.add(budget)
            db.commit()
            db.refresh(budget)
            return {"success": True, "budgetId": budget.id, "updated": False}
    finally:
        db.close()


@app.get("/budgets/{user_id}")
def get_budgets(user_id: str) -> dict:
    """
    Get all active budgets for a user.
    """
    db = get_session()
    try:
        budgets = (
            db.query(BudgetModel)
            .filter(
                BudgetModel.user_id == user_id,
                BudgetModel.is_active,
            )
            .all()
        )

        return {"budgets": [b.to_dict() for b in budgets]}
    finally:
        db.close()


@app.get("/budgets/{user_id}/status")
def get_budget_status_endpoint(user_id: str, month: str | None = None) -> dict:
    """
    Get budget status for a user.
    """
    db = get_session()
    try:
        status = get_budget_status(db, user_id, month)
        return {"status": status}
    finally:
        db.close()


@app.post("/goals/create")
def create_goal(req: CreateGoalRequest) -> dict:
    """
    Create a new financial goal.
    """
    db = get_session()
    try:
        goal = FinancialGoalModel(
            user_id=req.userId,
            name=req.goal.name,
            target_amount=req.goal.target_amount,
            current_amount=req.goal.current_amount,
            target_date=(
                datetime.fromisoformat(req.goal.target_date.replace("Z", "+00:00"))
                if req.goal.target_date
                else None
            ),
            priority=req.goal.priority,
            description=req.goal.description,
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)
        return {"success": True, "goalId": goal.id}
    finally:
        db.close()


@app.get("/goals/{user_id}")
def get_goals(user_id: str) -> dict:
    """
    Get all active goals for a user.
    """
    db = get_session()
    try:
        goals = (
            db.query(FinancialGoalModel)
            .filter(
                FinancialGoalModel.user_id == user_id,
                FinancialGoalModel.is_active,
            )
            .all()
        )

        return {"goals": [g.to_dict() for g in goals]}
    finally:
        db.close()


@app.post("/goals/{user_id}/{goal_id}/update")
def update_goal(user_id: str, goal_id: int, current_amount: float) -> dict:
    """
    Update the current amount for a goal.
    """
    db = get_session()
    try:
        goal = (
            db.query(FinancialGoalModel)
            .filter(
                FinancialGoalModel.id == goal_id,
                FinancialGoalModel.user_id == user_id,
            )
            .first()
        )

        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")

        goal.current_amount = current_amount
        if goal.current_amount >= goal.target_amount and not goal.completed_at:
            goal.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(goal)
        return {"success": True, "goal": goal.to_dict()}
    finally:
        db.close()


@app.post("/assessment/health")
def conduct_assessment(req: FinancialHealthRequest) -> dict:
    """
    Conduct a financial health assessment using LangGraph.
    """
    mgr = _get_memori_manager(req.userId, req.openaiKey)

    # Get transaction history
    db = get_session()
    try:
        transactions = (
            db.query(TransactionModel)
            .filter(TransactionModel.user_id == req.userId)
            .order_by(TransactionModel.date.desc())
            .limit(200)
            .all()
        )

        transaction_history = []
        for t in reversed(transactions):  # Oldest first
            transaction_history.append(
                {
                    "date": t.date.isoformat() if t.date else None,
                    "amount": t.amount,
                    "category": t.category,
                    "merchant": t.merchant,
                    "transaction_type": t.transaction_type,
                }
            )

        # Get budgets
        budgets = (
            db.query(BudgetModel)
            .filter(
                BudgetModel.user_id == req.userId,
                BudgetModel.is_active,
            )
            .all()
        )
        budget_list = [b.to_dict() for b in budgets]

        # Get goals
        goals = (
            db.query(FinancialGoalModel)
            .filter(
                FinancialGoalModel.user_id == req.userId,
                FinancialGoalModel.is_active,
            )
            .all()
        )
        goal_list = [g.to_dict() for g in goals]
    finally:
        db.close()

    # Get spending issues context from Memori
    issues_context = ""
    try:
        issues_context = mgr.identify_spending_issues()
    except Exception:
        issues_context = ""

    model_name = os.getenv("FINANCE_MODEL", "gpt-4o-mini")
    api_key = req.openaiKey or os.getenv("OPENAI_API_KEY")
    assessment_result = conduct_financial_health_assessment(
        profile=req.profile,
        transactions=transaction_history,
        budgets=budget_list,
        goals=goal_list,
        spending_issues_context=issues_context,
        model_name=model_name,
        api_key=api_key,
    )

    # Save assessment to database
    db = get_session()
    try:
        assessment = FinancialHealthAssessment(
            user_id=req.userId,
            overall_score=assessment_result.overall_score,
            assessment_markdown=assessment_result.assessment_markdown,
            spending_analysis=json.dumps(assessment_result.spending_analysis),
            budget_adherence=json.dumps(assessment_result.budget_adherence),
            goal_progress=json.dumps(assessment_result.goal_progress),
            risk_factors=json.dumps(assessment_result.risk_factors),
            opportunities=json.dumps(assessment_result.opportunities),
            recommendations=json.dumps(assessment_result.recommendations),
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

        return {
            "assessmentId": assessment.id,
            "overallScore": assessment_result.overall_score,
            "spendingAnalysis": assessment_result.spending_analysis,
            "budgetAdherence": assessment_result.budget_adherence,
            "goalProgress": assessment_result.goal_progress,
            "riskFactors": assessment_result.risk_factors,
            "opportunities": assessment_result.opportunities,
            "recommendations": assessment_result.recommendations,
            "assessmentMarkdown": assessment_result.assessment_markdown,
        }
    finally:
        db.close()


@app.get("/assessment/{user_id}/latest")
def get_latest_assessment(user_id: str) -> dict:
    """
    Get the latest financial health assessment for a user.
    """
    db = get_session()
    try:
        assessment = (
            db.query(FinancialHealthAssessment)
            .filter(FinancialHealthAssessment.user_id == user_id)
            .order_by(FinancialHealthAssessment.created_at.desc())
            .first()
        )

        if assessment:
            return {"exists": True, "assessment": assessment.to_dict()}
        else:
            return {"exists": False, "assessment": None}
    finally:
        db.close()


@app.post("/goals/generate")
def generate_goal_plan(req: GoalSettingRequest) -> dict:
    """
    Generate a personalized goal-setting plan using LangGraph.
    """
    # Validate memori manager and get transaction history
    _get_memori_manager(req.userId, req.openaiKey)  # validate API key

    # Get transaction history
    db = get_session()
    try:
        transactions = (
            db.query(TransactionModel)
            .filter(TransactionModel.user_id == req.userId)
            .order_by(TransactionModel.date.desc())
            .limit(200)
            .all()
        )

        transaction_history = []
        for t in reversed(transactions):
            transaction_history.append(
                {
                    "date": t.date.isoformat() if t.date else None,
                    "amount": t.amount,
                    "category": t.category,
                    "merchant": t.merchant,
                    "transaction_type": t.transaction_type,
                }
            )

        # Get current goals
        goals = (
            db.query(FinancialGoalModel)
            .filter(
                FinancialGoalModel.user_id == req.userId,
                FinancialGoalModel.is_active,
            )
            .all()
        )
        goal_list = [g.to_dict() for g in goals]
    finally:
        db.close()

    model_name = os.getenv("FINANCE_MODEL", "gpt-4o-mini")
    api_key = req.openaiKey or os.getenv("OPENAI_API_KEY")
    goal_result = generate_goal_setting_plan(
        profile=req.profile,
        transactions=transaction_history,
        current_goals=goal_list,
        model_name=model_name,
        api_key=api_key,
    )

    return {
        "recommendedGoals": goal_result.recommended_goals,
        "actionPlan": goal_result.action_plan,
        "timeline": goal_result.timeline,
        "milestones": goal_result.milestones,
        "goalMarkdown": goal_result.goal_markdown,
    }


@app.post("/recurring/identify")
def identify_recurring(req: FinancialHealthRequest) -> dict:
    """
    Identify recurring expenses from transaction history.
    """
    db = get_session()
    try:
        transactions = (
            db.query(TransactionModel)
            .filter(TransactionModel.user_id == req.userId)
            .order_by(TransactionModel.date.desc())
            .limit(200)
            .all()
        )

        transaction_history = []
        for t in transactions:
            transaction_history.append(
                {
                    "date": t.date.isoformat() if t.date else None,
                    "amount": t.amount,
                    "category": t.category,
                    "merchant": t.merchant,
                    "transaction_type": t.transaction_type,
                }
            )
    finally:
        db.close()

    model_name = os.getenv("FINANCE_MODEL", "gpt-4o-mini")
    api_key = req.openaiKey or os.getenv("OPENAI_API_KEY")
    recurring = identify_recurring_expenses(
        transactions=transaction_history,
        model_name=model_name,
        api_key=api_key,
    )

    # Save to database
    db = get_session()
    try:
        # Clear old recurring expenses
        db.query(RecurringExpense).filter(
            RecurringExpense.user_id == req.userId
        ).delete()

        # Add new ones
        for exp in recurring:
            recurring_exp = RecurringExpense(
                user_id=req.userId,
                merchant=exp.get("merchant", ""),
                category=exp.get("category", "Other"),
                average_amount=exp.get("average_amount", 0.0),
                frequency=exp.get("frequency", "monthly"),
                confidence=exp.get("confidence", 0.5),
                last_seen=datetime.utcnow(),
            )
            db.add(recurring_exp)

        db.commit()

        return {"recurringExpenses": recurring}
    finally:
        db.close()


@app.get("/recurring/{user_id}")
def get_recurring_expenses(user_id: str) -> dict:
    """
    Get identified recurring expenses for a user.
    """
    db = get_session()
    try:
        expenses = (
            db.query(RecurringExpense).filter(RecurringExpense.user_id == user_id).all()
        )

        return {"recurringExpenses": [e.to_dict() for e in expenses]}
    finally:
        db.close()


@app.post("/finance/question")
def ask_finance_question(req: FinanceQuestionRequest) -> dict:
    """
    Ask Memori about the user's financial performance, patterns, and trends.
    """
    mgr = _get_memori_manager(req.userId, req.openaiKey)
    answer = mgr.summarize_financial_performance(req.question)
    return {"answer": answer}


@app.get("/analytics/{user_id}")
def get_analytics(user_id: str, days: int = 30) -> dict:
    """
    Get comprehensive analytics for a user.
    """
    db = get_session()
    try:
        stats = get_transaction_stats(db, user_id, days)
        monthly_summary = get_monthly_summary(db, user_id, months=6)

        return {
            "stats": stats,
            "monthlySummary": monthly_summary,
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
