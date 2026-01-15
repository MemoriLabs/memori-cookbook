from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

# Lazy imports for heavy dependencies
if TYPE_CHECKING:
    pass


class FinancialProfile(BaseModel):
    """User financial profile."""

    name: str = Field(..., description="User's name or handle.")
    age: int | None = Field(None, description="User's age.")
    income: float | None = Field(None, description="Monthly income.")
    currency: str = Field(default="USD", description="Currency code (USD, EUR, etc.).")
    financial_goals: list[str] = Field(
        default_factory=list,
        description="Financial goals, e.g. ['Save for emergency fund', 'Pay off credit card debt', 'Save for vacation'].",
    )
    risk_tolerance: str = Field(
        default="Moderate",
        description="Risk tolerance: Conservative, Moderate, Aggressive.",
    )
    monthly_expenses_estimate: float | None = Field(
        None, description="Estimated monthly expenses."
    )
    savings_balance: float | None = Field(None, description="Current savings balance.")
    debt_balance: float | None = Field(None, description="Current total debt balance.")


class Transaction(BaseModel):
    """Transaction model."""

    date: str  # ISO date string
    amount: float
    category: (
        str  # e.g., "Food", "Transportation", "Entertainment", "Bills", "Shopping"
    )
    merchant: str | None = None
    description: str | None = None
    transaction_type: str = Field(default="expense", description="expense or income")
    payment_method: str | None = (
        None  # e.g., "Credit Card", "Debit Card", "Cash", "Bank Transfer"
    )
    is_recurring: bool = Field(
        default=False, description="Whether this is a recurring expense"
    )
    notes: str | None = None


class Budget(BaseModel):
    """Budget model."""

    category: str
    monthly_limit: float
    currency: str = "USD"


class FinancialGoal(BaseModel):
    """Financial goal model."""

    name: str
    target_amount: float
    current_amount: float = 0.0
    target_date: str | None = None  # ISO date string
    priority: str = Field(default="Medium", description="High, Medium, Low")
    description: str | None = None


class FinancialHealthResult(BaseModel):
    """Result from financial health assessment."""

    overall_score: float  # 0-100
    spending_analysis: dict[str, Any]
    budget_adherence: dict[str, Any]
    goal_progress: dict[str, Any]
    recommendations: list[str]
    assessment_markdown: str
    risk_factors: list[str]
    opportunities: list[str]


class GoalSettingResult(BaseModel):
    """Result from goal-setting workflow."""

    recommended_goals: list[dict[str, Any]]
    action_plan: dict[str, Any]
    timeline: dict[str, Any]
    goal_markdown: str
    milestones: list[dict[str, Any]]


def conduct_financial_health_assessment(
    profile: FinancialProfile,
    transactions: list[dict[str, Any]],
    budgets: list[dict[str, Any]],
    goals: list[dict[str, Any]],
    spending_issues_context: str | None = None,
    model_name: str = "gpt-4o-mini",
    api_key: str | None = None,
) -> FinancialHealthResult:
    """
    Use LangGraph to conduct a comprehensive financial health assessment.

    This creates a multi-step assessment process:
    1. Analyze spending patterns and trends
    2. Evaluate budget adherence
    3. Assess goal progress
    4. Identify risk factors and opportunities
    5. Generate personalized recommendations
    """
    # Lazy import heavy dependencies
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat

    # Build transaction summary
    if not transactions:
        transaction_summary = "No transaction data available yet."
    else:
        recent = transactions[-30:]  # Last 30 transactions
        transaction_summary = (
            f"Recent transaction data (last {len(recent)} transactions):\n"
        )
        total_spent = sum(
            t.get("amount", 0) for t in recent if t.get("transaction_type") == "expense"
        )
        total_income = sum(
            t.get("amount", 0) for t in recent if t.get("transaction_type") == "income"
        )

        transaction_summary += f"Total Income: {profile.currency} {total_income:.2f}\n"
        transaction_summary += f"Total Expenses: {profile.currency} {total_spent:.2f}\n"
        transaction_summary += (
            f"Net: {profile.currency} {total_income - total_spent:.2f}\n\n"
        )

        # Group by category
        category_totals = {}
        for t in recent:
            if t.get("transaction_type") == "expense":
                cat = t.get("category", "Other")
                category_totals[cat] = category_totals.get(cat, 0) + abs(
                    t.get("amount", 0)
                )

        transaction_summary += "Spending by category:\n"
        for cat, amt in sorted(
            category_totals.items(), key=lambda x: x[1], reverse=True
        )[:10]:
            transaction_summary += f"  {cat}: {profile.currency} {amt:.2f}\n"

    # Build budget summary
    budget_summary = ""
    if budgets:
        budget_summary = "Current budgets:\n"
        for b in budgets:
            budget_summary += f"  {b.get('category', 'Unknown')}: {profile.currency} {b.get('monthly_limit', 0):.2f}/month\n"
    else:
        budget_summary = "No budgets set yet."

    # Build goals summary
    goals_summary = ""
    if goals:
        goals_summary = "Financial goals:\n"
        for g in goals:
            progress = (
                (g.get("current_amount", 0) / g.get("target_amount", 1)) * 100
                if g.get("target_amount", 0) > 0
                else 0
            )
            goals_summary += f"  {g.get('name', 'Unknown')}: {profile.currency} {g.get('current_amount', 0):.2f} / {profile.currency} {g.get('target_amount', 0):.2f} ({progress:.1f}%)\n"
    else:
        goals_summary = "No financial goals set yet."

    issues_block = (
        spending_issues_context or "No specific spending issues identified yet."
    )

    prompt = f"""You are an expert financial advisor with access to long-term memory about this user's financial history.

User Profile:
{profile.model_dump_json(indent=2)}

Transaction Summary:
{transaction_summary}

Budget Summary:
{budget_summary}

Goals Summary:
{goals_summary}

Identified Spending Issues/Opportunities:
{issues_block}

Conduct a comprehensive financial health assessment. You must:

1. Overall Score: Calculate a financial health score (0-100) based on:
   - Spending vs income ratio
   - Budget adherence
   - Savings rate
   - Debt-to-income ratio
   - Goal progress

2. Spending Analysis: Analyze spending patterns, identify top categories, trends

3. Budget Adherence: Evaluate how well the user is sticking to their budgets

4. Goal Progress: Assess progress toward financial goals

5. Risk Factors: Identify financial risks (overspending, debt, lack of savings, etc.)

6. Opportunities: Identify opportunities for improvement (savings, debt reduction, etc.)

7. Recommendations: Provide 5-7 specific, actionable recommendations

Respond using the following JSON structure:
{{
  "overall_score": 75.0,
  "spending_analysis": {{
    "total_monthly_spending": 2500.0,
    "top_categories": ["Food", "Transportation", "Bills"],
    "spending_trend": "increasing/stable/decreasing",
    "recurring_expenses": ["Netflix", "Gym membership"]
  }},
  "budget_adherence": {{
    "overall_adherence": 0.85,
    "categories_over_budget": ["Food", "Entertainment"],
    "categories_under_budget": ["Transportation"]
  }},
  "goal_progress": {{
    "on_track_goals": ["Emergency fund"],
    "behind_goals": ["Vacation savings"],
    "average_progress": 0.65
  }},
  "risk_factors": [
    "High spending on non-essential categories",
    "No emergency fund"
  ],
  "opportunities": [
    "Reduce dining out expenses",
    "Increase savings rate by 5%"
  ],
  "recommendations": [
    "Recommendation 1",
    "Recommendation 2",
    ...
  ],
  "assessment_markdown": "Full markdown assessment..."
}}
"""

    # Set API key if provided
    model_kwargs = {"id": model_name}
    if api_key:
        model_kwargs["api_key"] = api_key

    agent = Agent(
        name="Financial Health Assessor",
        model=OpenAIChat(**model_kwargs),
        markdown=False,
    )
    result = agent.run(prompt)
    text = str(getattr(result, "content", result))

    # Parse JSON response
    import json
    import re

    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
        except json.JSONDecodeError:
            data = _parse_assessment_fallback(text)
    else:
        data = _parse_assessment_fallback(text)

    assessment_markdown = data.get("assessment_markdown", "")
    if not assessment_markdown:
        assessment_markdown = text

    return FinancialHealthResult(
        overall_score=data.get("overall_score", 50.0),
        spending_analysis=data.get("spending_analysis", {}),
        budget_adherence=data.get("budget_adherence", {}),
        goal_progress=data.get("goal_progress", {}),
        recommendations=data.get("recommendations", []),
        assessment_markdown=assessment_markdown,
        risk_factors=data.get("risk_factors", []),
        opportunities=data.get("opportunities", []),
    )


def generate_goal_setting_plan(
    profile: FinancialProfile,
    transactions: list[dict[str, Any]],
    current_goals: list[dict[str, Any]],
    model_name: str = "gpt-4o-mini",
    api_key: str | None = None,
) -> GoalSettingResult:
    """
    Use LangGraph to generate a personalized goal-setting plan.

    This creates a multi-step goal-setting process:
    1. Analyze current financial situation
    2. Identify goal opportunities
    3. Create actionable goals with timelines
    4. Generate milestones and action plans
    """
    # Lazy import heavy dependencies
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat

    # Build financial summary
    if transactions:
        recent = transactions[-30:]
        total_income = sum(
            t.get("amount", 0) for t in recent if t.get("transaction_type") == "income"
        )
        total_expenses = sum(
            t.get("amount", 0) for t in recent if t.get("transaction_type") == "expense"
        )
        net = total_income - total_expenses
        financial_summary = f"Monthly Income: {profile.currency} {total_income:.2f}\n"
        financial_summary += (
            f"Monthly Expenses: {profile.currency} {total_expenses:.2f}\n"
        )
        financial_summary += f"Net: {profile.currency} {net:.2f}\n"
    else:
        financial_summary = "Limited transaction data available."

    current_goals_summary = ""
    if current_goals:
        current_goals_summary = "Current goals:\n"
        for g in current_goals:
            current_goals_summary += f"  - {g.get('name', 'Unknown')}: {profile.currency} {g.get('current_amount', 0):.2f} / {profile.currency} {g.get('target_amount', 0):.2f}\n"
    else:
        current_goals_summary = "No current goals."

    prompt = f"""You are an expert financial advisor helping set and achieve financial goals.

User Profile:
{profile.model_dump_json(indent=2)}

Financial Summary:
{financial_summary}

Current Goals:
{current_goals_summary}

Generate a comprehensive goal-setting plan. You must:

1. Recommended Goals: Suggest 3-5 specific, achievable financial goals based on:
   - User's stated goals
   - Current financial situation
   - Income and spending patterns
   - Risk tolerance

2. Action Plan: Create a detailed action plan for achieving each goal:
   - Monthly savings targets
   - Specific actions to take
   - Timeline

3. Timeline: Provide realistic timelines for each goal

4. Milestones: Break down each goal into smaller milestones

Respond using the following JSON structure:
{{
  "recommended_goals": [
    {{
      "name": "Emergency Fund",
      "target_amount": 10000.0,
      "timeline_months": 12,
      "monthly_savings": 833.33,
      "priority": "High",
      "description": "Build 6 months of expenses"
    }},
    ...
  ],
  "action_plan": {{
    "emergency_fund": {{
      "monthly_target": 833.33,
      "actions": ["Set up automatic transfer", "Reduce dining out"],
      "timeline": "12 months"
    }},
    ...
  }},
  "timeline": {{
    "short_term": ["Goal 1 - 3 months", "Goal 2 - 6 months"],
    "medium_term": ["Goal 3 - 12 months"],
    "long_term": ["Goal 4 - 24 months"]
  }},
  "milestones": [
    {{
      "goal_name": "Emergency Fund",
      "milestone": "Save first $2,500",
      "target_date": "3 months",
      "reward": "Celebrate milestone"
    }},
    ...
  ],
  "goal_markdown": "Full markdown plan..."
}}
"""

    # Set API key if provided
    model_kwargs = {"id": model_name}
    if api_key:
        model_kwargs["api_key"] = api_key

    agent = Agent(
        name="Goal Setting Planner",
        model=OpenAIChat(**model_kwargs),
        markdown=False,
    )
    result = agent.run(prompt)
    text = str(getattr(result, "content", result))

    # Parse JSON response
    import json
    import re

    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
        except json.JSONDecodeError:
            data = _parse_goal_setting_fallback(text)
    else:
        data = _parse_goal_setting_fallback(text)

    goal_markdown = data.get("goal_markdown", "")
    if not goal_markdown:
        goal_markdown = text

    return GoalSettingResult(
        recommended_goals=data.get("recommended_goals", []),
        action_plan=data.get("action_plan", {}),
        timeline=data.get("timeline", {}),
        goal_markdown=goal_markdown,
        milestones=data.get("milestones", []),
    )


def identify_recurring_expenses(
    transactions: list[dict[str, Any]],
    model_name: str = "gpt-4o-mini",
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """
    Use AI to identify recurring expenses from transaction history.
    """
    # Lazy import heavy dependencies
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat

    if len(transactions) < 10:
        return []  # Need at least some data

    # Build transaction list
    transaction_list = "Transaction history for recurring expense analysis:\n"
    for t in transactions[-60:]:  # Last 60 transactions
        transaction_list += f"Date: {t.get('date', 'N/A')}, "
        transaction_list += f"Amount: {t.get('amount', 0):.2f}, "
        transaction_list += f"Category: {t.get('category', 'Unknown')}, "
        transaction_list += f"Merchant: {t.get('merchant', 'Unknown')}\n"

    prompt = f"""Analyze the following transaction history and identify recurring expenses.

{transaction_list}

Identify recurring expenses such as:
- Subscriptions (Netflix, Spotify, etc.)
- Monthly bills (utilities, rent, insurance)
- Regular purchases (gym membership, etc.)

For each recurring expense found, provide:
- Merchant/Service name
- Category
- Average monthly amount
- Frequency (monthly, weekly, etc.)
- Confidence level (0.0 to 1.0)

Respond in JSON format:
{{
  "recurring_expenses": [
    {{
      "merchant": "Netflix",
      "category": "Entertainment",
      "average_amount": 15.99,
      "frequency": "monthly",
      "confidence": 0.95
    }},
    ...
  ]
}}
"""

    # Set API key if provided
    model_kwargs = {"id": model_name}
    if api_key:
        model_kwargs["api_key"] = api_key

    agent = Agent(
        name="Recurring Expense Analyzer",
        model=OpenAIChat(**model_kwargs),
        markdown=False,
    )
    result = agent.run(prompt)
    text = str(getattr(result, "content", result))

    import json
    import re

    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            return data.get("recurring_expenses", [])
        except json.JSONDecodeError:
            pass

    return []


def _parse_assessment_fallback(text: str) -> dict:
    """Fallback parser if JSON parsing fails."""
    return {
        "overall_score": 50.0,
        "spending_analysis": {},
        "budget_adherence": {},
        "goal_progress": {},
        "risk_factors": [],
        "opportunities": [],
        "recommendations": [],
        "assessment_markdown": text,
    }


def _parse_goal_setting_fallback(text: str) -> dict:
    """Fallback parser for goal-setting results."""
    return {
        "recommended_goals": [],
        "action_plan": {},
        "timeline": {},
        "milestones": [],
        "goal_markdown": text,
    }


def format_transaction_summary(
    profile: FinancialProfile,
    transaction: Transaction,
) -> str:
    """
    Format a transaction entry for logging into Memori.
    """
    summary = f"""Financial Transaction Log

User profile:
{profile.model_dump_json(indent=2)}

Date: {transaction.date}

Transaction Details:
- Amount: {profile.currency} {transaction.amount:.2f}
- Type: {transaction.transaction_type}
- Category: {transaction.category}
- Merchant: {transaction.merchant or "N/A"}
- Payment Method: {transaction.payment_method or "N/A"}
- Is Recurring: {transaction.is_recurring}
- Description: {transaction.description or "N/A"}

Notes: {transaction.notes or "None"}
"""
    return summary
