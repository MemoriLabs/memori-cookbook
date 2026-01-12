from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

# Lazy imports for heavy dependencies
if TYPE_CHECKING:
    pass


class WellnessProfile(BaseModel):
    """User wellness profile."""

    name: str = Field(..., description="User's name or handle.")
    age: int | None = Field(None, description="User's age.")
    gender: str | None = Field(None, description="User's gender.")
    primary_goals: list[str] = Field(
        default_factory=list,
        description="Primary wellness goals, e.g. ['Better sleep', 'Weight loss', 'Stress reduction'].",
    )
    health_conditions: list[str] = Field(
        default_factory=list, description="Any health conditions or concerns."
    )
    activity_level: str = Field(
        default="Moderate",
        description="Activity level: Sedentary, Light, Moderate, Active, Very Active.",
    )
    time_commitment: str = Field(
        default="30 minutes/day",
        description="Available time commitment for wellness activities.",
    )
    preferences: list[str] = Field(
        default_factory=list,
        description="Wellness preferences, e.g. ['Yoga', 'Running', 'Meditation'].",
    )


class DailyHabitEntry(BaseModel):
    """Daily habit entry model."""

    date: str  # ISO date string
    sleep_hours: float | None = None
    sleep_quality: int | None = None  # 1-10
    exercise_type: str | None = None
    exercise_duration_minutes: int | None = None
    exercise_intensity: str | None = None
    steps: int | None = None
    water_intake_liters: float | None = None
    calories_consumed: int | None = None
    mood_score: int | None = None  # 1-10
    energy_level: int | None = None  # 1-10
    stress_level: int | None = None  # 1-10
    notes: str | None = None


class WellnessPlanResult(BaseModel):
    """Result from wellness plan generation."""

    focus_areas: list[str]
    daily_goals: dict[str, Any]
    weekly_objectives: list[str]
    plan_markdown: str
    interventions: list[dict[str, Any]]


class CheckInResult(BaseModel):
    """Result from weekly check-in assessment."""

    progress_summary: dict[str, Any]
    correlations_found: list[dict[str, Any]]
    recommendations: list[str]
    assessment_markdown: str


def generate_wellness_plan(
    profile: WellnessProfile,
    habit_history: list[dict[str, Any]],
    weakness_context: str | None = None,
    model_name: str = "gpt-4o-mini",
    api_key: str | None = None,
) -> WellnessPlanResult:
    """
    Use LangGraph to generate a personalized wellness plan.

    This creates a multi-step planning process:
    1. Analyze current habits and identify patterns
    2. Identify weak areas and opportunities
    3. Generate personalized interventions
    4. Create daily goals and weekly objectives
    """
    # Lazy import heavy dependencies
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat

    # Build context from habit history
    habit_summary = ""
    if habit_history:
        recent = habit_history[-7:]  # Last 7 days
        habit_summary = f"Recent habit data (last {len(recent)} days):\n"
        for entry in recent:
            habit_summary += f"- Sleep: {entry.get('sleep_hours', 'N/A')}h, "
            habit_summary += f"Mood: {entry.get('mood_score', 'N/A')}/10, "
            habit_summary += (
                f"Exercise: {entry.get('exercise_duration_minutes', 0)}min\n"
            )
    else:
        habit_summary = "No habit history available yet."

    weakness_block = weakness_context or "No specific weaknesses identified yet."

    prompt = f"""You are an expert wellness coach with access to long-term memory about this user's wellness journey.

User Profile:
{profile.model_dump_json(indent=2)}

Habit History Summary:
{habit_summary}

Identified Weaknesses/Opportunities:
{weakness_block}

Generate a comprehensive 1-week personalized wellness plan. The plan should:

1. Focus Areas: Identify 3-5 key areas to focus on (e.g., "Sleep Quality", "Stress Management", "Regular Exercise")
2. Daily Goals: Create specific, achievable daily goals for each focus area
3. Weekly Objectives: Set 3-5 weekly objectives that are measurable
4. Interventions: Suggest 5-7 specific interventions or actions the user can take
5. Plan Document: Create a detailed markdown plan with day-by-day guidance

Respond using the following JSON structure:
{{
  "focus_areas": ["area1", "area2", ...],
  "daily_goals": {{
    "sleep": "goal description",
    "exercise": "goal description",
    "nutrition": "goal description",
    "mood": "goal description"
  }},
  "weekly_objectives": ["objective1", "objective2", ...],
  "interventions": [
    {{"type": "sleep", "action": "action description", "rationale": "why this helps"}},
    ...
  ],
  "plan_markdown": "Full markdown plan with day-by-day breakdown..."
}}
"""

    # Set API key if provided
    model_kwargs = {"id": model_name}
    if api_key:
        model_kwargs["api_key"] = api_key

    agent = Agent(
        name="Wellness Plan Generator",
        model=OpenAIChat(**model_kwargs),  # type: ignore[arg-type]
        markdown=False,
    )
    result = agent.run(prompt)
    text = str(getattr(result, "content", result))

    # Parse JSON response
    import json
    import re

    # Try to extract JSON from the response
    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
        except json.JSONDecodeError:
            # Fallback to structured parsing
            data = _parse_wellness_plan_fallback(text)
    else:
        data = _parse_wellness_plan_fallback(text)

    # Extract plan markdown (everything after the JSON or as a separate section)
    plan_markdown = data.get("plan_markdown", "")
    if not plan_markdown:
        # Try to extract from the full text
        markdown_match = re.search(r"```markdown\s*([\s\S]*?)\s*```", text)
        if markdown_match:
            plan_markdown = markdown_match.group(1)
        else:
            plan_markdown = text

    return WellnessPlanResult(
        focus_areas=data.get("focus_areas", ["Sleep", "Exercise", "Nutrition", "Mood"]),
        daily_goals=data.get("daily_goals", {}),
        weekly_objectives=data.get("weekly_objectives", []),
        plan_markdown=plan_markdown,
        interventions=data.get("interventions", []),
    )


def _parse_wellness_plan_fallback(text: str) -> dict:
    """Fallback parser if JSON parsing fails."""
    import re

    data = {
        "focus_areas": [],
        "daily_goals": {},
        "weekly_objectives": [],
        "interventions": [],
        "plan_markdown": text,
    }

    # Try to extract focus areas
    focus_match = re.search(r"Focus Areas?[:\-]\s*([^\n]+)", text, re.IGNORECASE)
    if focus_match:
        data["focus_areas"] = [f.strip() for f in focus_match.group(1).split(",")]

    return data


def conduct_weekly_checkin(
    profile: WellnessProfile,
    habit_history: list[dict[str, Any]],
    previous_plan: dict[str, Any] | None = None,
    model_name: str = "gpt-4o-mini",
    api_key: str | None = None,
) -> CheckInResult:
    """
    Conduct a weekly check-in assessment using LangGraph.

    This process:
    1. Analyzes the week's habit data
    2. Identifies correlations between different metrics
    3. Assesses progress against the wellness plan
    4. Generates recommendations for the next week
    """
    # Lazy import heavy dependencies
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat

    # Build habit summary
    if not habit_history:
        habit_summary = "No habit data available for this week."
    else:
        habit_summary = f"Analyzing {len(habit_history)} days of habit data:\n\n"
        for entry in habit_history:
            habit_summary += f"Date: {entry.get('date', 'N/A')}\n"
            habit_summary += f"  Sleep: {entry.get('sleep_hours', 'N/A')}h (quality: {entry.get('sleep_quality', 'N/A')}/10)\n"
            habit_summary += f"  Exercise: {entry.get('exercise_type', 'None')} ({entry.get('exercise_duration_minutes', 0)}min)\n"
            habit_summary += f"  Mood: {entry.get('mood_score', 'N/A')}/10, Energy: {entry.get('energy_level', 'N/A')}/10, Stress: {entry.get('stress_level', 'N/A')}/10\n"
            habit_summary += f"  Water: {entry.get('water_intake_liters', 'N/A')}L\n\n"

    plan_context = ""
    if previous_plan:
        plan_context = f"Previous week's plan focused on: {', '.join(previous_plan.get('focus_areas', []))}\n"
        plan_context += f"Weekly objectives: {', '.join(previous_plan.get('weekly_objectives', []))}"
    else:
        plan_context = "No previous plan to compare against."

    prompt = f"""You are an expert wellness coach conducting a weekly check-in assessment.

User Profile:
{profile.model_dump_json(indent=2)}

This Week's Habit Data:
{habit_summary}

Previous Week's Plan:
{plan_context}

Conduct a comprehensive weekly assessment. You must:

1. Progress Summary: Analyze progress across all metrics (sleep, exercise, nutrition, mood)
2. Correlations: Identify any correlations you notice between different metrics (e.g., "When sleep hours increase, mood scores improve")
3. Recommendations: Provide 5-7 specific, actionable recommendations for the next week
4. Assessment Document: Create a detailed markdown assessment

Look for patterns like:
- Sleep quality vs mood
- Exercise frequency vs energy levels
- Stress levels vs sleep duration
- Water intake vs energy
- Any other meaningful correlations

Respond using the following JSON structure:
{{
  "progress_summary": {{
    "sleep": "improved/stable/declined",
    "exercise": "improved/stable/declined",
    "mood": "improved/stable/declined",
    "overall": "summary text"
  }},
  "correlations_found": [
    {{
      "metric1": "sleep_hours",
      "metric2": "mood_score",
      "type": "positive",
      "strength": 0.7,
      "description": "When sleep hours increase, mood scores tend to improve"
    }},
    ...
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
        name="Weekly Check-In Assessor",
        model=OpenAIChat(**model_kwargs),  # type: ignore[arg-type]
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
            data = _parse_checkin_fallback(text)
    else:
        data = _parse_checkin_fallback(text)

    assessment_markdown = data.get("assessment_markdown", "")
    if not assessment_markdown:
        assessment_markdown = text

    return CheckInResult(
        progress_summary=data.get("progress_summary", {}),
        correlations_found=data.get("correlations_found", []),
        recommendations=data.get("recommendations", []),
        assessment_markdown=assessment_markdown,
    )


def _parse_checkin_fallback(text: str) -> dict:
    """Fallback parser for check-in results."""
    return {
        "progress_summary": {"overall": "Assessment completed"},
        "correlations_found": [],
        "recommendations": [],
        "assessment_markdown": text,
    }


def identify_correlations(
    habit_history: list[dict[str, Any]],
    model_name: str = "gpt-4o-mini",
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """
    Use AI to identify correlations between different wellness metrics.
    """
    # Lazy import heavy dependencies
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat

    if len(habit_history) < 7:
        return []  # Need at least a week of data

    # Build data summary
    data_summary = "Habit data for correlation analysis:\n"
    for entry in habit_history:
        data_summary += f"Sleep: {entry.get('sleep_hours')}h, "
        data_summary += f"Mood: {entry.get('mood_score')}/10, "
        data_summary += f"Energy: {entry.get('energy_level')}/10, "
        data_summary += f"Exercise: {entry.get('exercise_duration_minutes', 0)}min, "
        data_summary += f"Stress: {entry.get('stress_level')}/10\n"

    prompt = f"""Analyze the following wellness habit data and identify meaningful correlations between different metrics.

{data_summary}

Identify correlations such as:
- Sleep hours vs mood score
- Exercise duration vs energy level
- Stress level vs sleep quality
- Water intake vs energy
- Any other meaningful relationships

For each correlation found, provide:
- The two metrics being compared
- The type (positive or negative)
- The strength (0.0 to 1.0)
- A brief description

Respond in JSON format:
{{
  "correlations": [
    {{
      "metric1": "sleep_hours",
      "metric2": "mood_score",
      "type": "positive",
      "strength": 0.75,
      "description": "When sleep hours increase, mood scores improve"
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
        name="Correlation Analyzer",
        model=OpenAIChat(**model_kwargs),  # type: ignore[arg-type]
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
            return data.get("correlations", [])
        except json.JSONDecodeError:
            pass

    return []


def format_habit_summary(
    profile: WellnessProfile,
    habit_entry: DailyHabitEntry,
) -> str:
    """
    Format a daily habit entry for logging into Memori.
    """
    summary = f"""Daily Wellness Habit Log

User profile:
{profile.model_dump_json(indent=2)}

Date: {habit_entry.date}

Sleep:
- Hours: {habit_entry.sleep_hours or "Not logged"}
- Quality (1-10): {habit_entry.sleep_quality or "Not logged"}

Exercise:
- Type: {habit_entry.exercise_type or "None"}
- Duration: {habit_entry.exercise_duration_minutes or 0} minutes
- Intensity: {habit_entry.exercise_intensity or "N/A"}
- Steps: {habit_entry.steps or "Not logged"}

Nutrition:
- Water intake: {habit_entry.water_intake_liters or "Not logged"} liters
- Calories: {habit_entry.calories_consumed or "Not logged"}

Mood & Energy:
- Mood score (1-10): {habit_entry.mood_score or "Not logged"}
- Energy level (1-10): {habit_entry.energy_level or "Not logged"}
- Stress level (1-10): {habit_entry.stress_level or "Not logged"}

Notes: {habit_entry.notes or "None"}
"""
    return summary
