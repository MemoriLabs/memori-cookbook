import os
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# Lazy imports for heavy dependencies
if TYPE_CHECKING:
    pass


def _run_agent_prompt(
    prompt: str,
    model_name: str,
    api_key: str | None,
    provider: str,
    markdown: bool = False,
) -> str:
    """Run a single-turn LLM prompt using the specified provider."""
    if provider == "claude":
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY", ""))
        response = client.messages.create(
            model=model_name,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text  # type: ignore
    if provider == "gemini":
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key or os.getenv("GEMINI_API_KEY", ""),
            base_url=GEMINI_BASE_URL,
        )
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""
    # Default: OpenAI via Agno
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat

    model_kwargs: dict[str, Any] = {"id": model_name}
    if api_key:
        model_kwargs["api_key"] = api_key
    agent = Agent(model=OpenAIChat(**model_kwargs), markdown=markdown)
    result = agent.run(prompt)
    return str(getattr(result, "content", result))


class CandidateProfile(BaseModel):
    name: str = Field(..., description="Candidate's name or handle.")
    target_role: str = Field(
        ..., description="Target role, e.g. Backend SWE, ML Engineer."
    )
    experience_level: str = Field(
        ..., description="Experience level, e.g. Student, Junior, Mid, Senior."
    )
    primary_language: str = Field(
        ..., description="Primary coding language for interviews."
    )
    target_companies: list[str] = Field(
        default_factory=list, description="Optional list of target companies."
    )
    main_goal: str = Field(
        ..., description="High-level goal, e.g. 'Crack FAANG interviews'."
    )
    timeframe: str = Field(
        ..., description="Time horizon for the goal, e.g. '3 months'."
    )


class ProblemMetadata(BaseModel):
    title: str
    difficulty: str = Field(
        default="Medium",
        description="Human-readable difficulty label, e.g. Easy, Medium, Hard.",
    )
    patterns: list[str] = Field(
        default_factory=list,
        description="Algorithm/data-structure patterns like arrays, graphs, DP.",
    )
    statement: str = Field(..., description="Full problem statement in Markdown.")


def generate_personalized_problem(
    profile: CandidateProfile,
    difficulty: str,
    patterns: list[str],
    weakness_context: str | None = None,
    model_name: str = "gpt-4o-mini",
    api_key: str | None = None,
    provider: str = "openai",
) -> ProblemMetadata:
    """Generate a coding interview problem. Supports OpenAI, Gemini, and Claude."""
    # Build context strings
    patterns_str = ", ".join(patterns) if patterns else "mixed core data structures"
    weakness_block = weakness_context or ""

    prompt = f"""You are an AI coding interview coach.

Candidate profile:
{profile.model_dump_json(indent=2)}

Weakness summary from prior attempts (may be empty or approximate):
{weakness_block}

Generate ONE coding interview problem for this candidate.

Requirements:
- Difficulty: {difficulty}
- Focus on these patterns: {patterns_str}

Respond using the following template exactly, with no extra commentary:

Title: <short descriptive title>
Difficulty: <Easy/Medium/Hard>
Patterns: <comma-separated patterns>
Problem:
<full problem statement in Markdown>
"""

    text = _run_agent_prompt(prompt, model_name, api_key, provider)

    # Simple parsing based on the enforced template.
    title = "Practice Problem"
    parsed_difficulty = difficulty
    parsed_patterns: list[str] = patterns.copy()
    statement_lines: list[str] = []
    in_statement = False

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Title:"):
            title = stripped.split("Title:", 1)[1].strip() or title
        elif stripped.startswith("Difficulty:"):
            parsed_difficulty = stripped.split("Difficulty:", 1)[1].strip() or (
                parsed_difficulty or difficulty
            )
        elif stripped.startswith("Patterns:"):
            pats = stripped.split("Patterns:", 1)[1]
            parsed_patterns = [p.strip() for p in pats.split(",") if p.strip()] or (
                parsed_patterns or patterns
            )
        elif stripped.startswith("Problem:"):
            in_statement = True
        elif in_statement:
            statement_lines.append(line)

    statement = "\n".join(statement_lines).strip() or text

    return ProblemMetadata(
        title=title,
        difficulty=parsed_difficulty,
        patterns=parsed_patterns,
        statement=statement,
    )


def generate_hint(
    problem: ProblemMetadata,
    language: str,
    code_so_far: str,
    hint_index: int,
    model_name: str = "gpt-4o-mini",
    api_key: str | None = None,
    provider: str = "openai",
) -> str:
    """Generate an incremental hint. Supports OpenAI, Gemini, and Claude."""

    difficulty = problem.difficulty
    patterns_str = ", ".join(problem.patterns) or "general algorithms"

    prompt = f"""You are an experienced interviewer giving HINT #{hint_index} to a candidate.

Problem (difficulty {difficulty}, patterns: {patterns_str}):
{problem.statement}

Candidate language: {language}
Candidate code so far (may be empty):
```{language.lower()}
{code_so_far or ""}
```

Provide a useful hint that:
- Moves them one step closer to a solution.
- Does NOT reveal the full answer or full code.
- Focuses on high-level strategy and key subproblems.

Respond with 1–3 short paragraphs of advice."""

    return _run_agent_prompt(prompt, model_name, api_key, provider, markdown=True)


def evaluate_solution(
    problem: ProblemMetadata,
    language: str,
    candidate_code: str,
    model_name: str = "gpt-4o-mini",
    api_key: str | None = None,
    provider: str = "openai",
) -> str:
    """Evaluate a candidate solution. Supports OpenAI, Gemini, and Claude."""

    difficulty = problem.difficulty
    patterns_str = ", ".join(problem.patterns) or "general algorithms"

    prompt = f"""You are a senior engineer and coding interview coach.

Evaluate the following candidate solution.

Problem (difficulty {difficulty}, patterns: {patterns_str}):
{problem.statement}

Candidate language: {language}
Candidate code:
```{language.lower()}
{candidate_code}
```

Provide a detailed but concise evaluation with these sections, in order:

## Verdict
State whether the solution is correct, partially correct, or incorrect, and why.

## Complexity
Give Big-O time and space complexity and note if it's optimal for this problem.

## Strengths
Short bullet list of what the candidate did well.

## Weaknesses
Short bullet list of the main issues, bugs, or missing edge cases.

## Recommended next focus
1–3 bullet points describing which algorithm/data-structure patterns or difficulty levels they should practice next, based on this attempt.
"""

    return _run_agent_prompt(prompt, model_name, api_key, provider, markdown=True)


def format_attempt_summary(
    profile: CandidateProfile,
    problem: ProblemMetadata,
    language: str,
    candidate_code: str,
    hints: list[str],
    evaluation_markdown: str,
) -> str:
    """
    Compose a rich natural-language + semi-structured summary for logging into Memori.
    """
    hints_block = "\n\n".join(
        f"Hint {i + 1}:\n{h}" for i, h in enumerate(hints) if h.strip()
    )

    summary = f"""Coding Interview Practice Attempt

Candidate profile:
{profile.model_dump_json(indent=2)}

Problem:
- Title: {problem.title}
- Difficulty: {problem.difficulty}
- Patterns: {", ".join(problem.patterns) or "N/A"}

Problem statement:
{problem.statement}

Language used: {language}

Candidate solution code:
```{language.lower()}
{candidate_code}
```

Hints used:
{hints_block or "No hints requested."}

Coach evaluation:
{evaluation_markdown}
"""
    return summary
