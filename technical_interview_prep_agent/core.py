from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

# Lazy imports for heavy dependencies
if TYPE_CHECKING:
    pass


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
) -> ProblemMetadata:
    """
    Use an Agno Agent (OpenAIChat) to generate a single coding interview problem
    tailored to the candidate profile + requested difficulty/patterns.
    """
    # Lazy import heavy dependencies
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat

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

    agent = Agent(
        name="Interview Problem Generator",
        model=OpenAIChat(id=model_name),
        markdown=False,
    )
    result = agent.run(prompt)
    text = str(getattr(result, "content", result))

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
) -> str:
    """
    Use Agno Agent to generate an incremental hint for the current attempt.
    """
    # Lazy import heavy dependencies
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat

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

    agent = Agent(
        name="Interview Hint Coach",
        model=OpenAIChat(id=model_name),
        markdown=True,
    )
    result = agent.run(prompt)
    return str(getattr(result, "content", result))


def evaluate_solution(
    problem: ProblemMetadata,
    language: str,
    candidate_code: str,
    model_name: str = "gpt-4o-mini",
) -> str:
    """
    Use Agno Agent to evaluate the candidate's solution.

    Returns markdown text including:
    - Verdict (correct/partially correct/incorrect)
    - Complexity analysis
    - Strengths and weaknesses
    - Recommended next focus
    """
    # Lazy import heavy dependencies
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat

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

    agent = Agent(
        name="Interview Solution Evaluator",
        model=OpenAIChat(id=model_name),
        markdown=True,
    )
    result = agent.run(prompt)
    return str(getattr(result, "content", result))


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
