"""
Swarm orchestrator — runs agents sequentially, chaining their outputs,
all sharing memory scoped to the current git branch via Memori.
"""

import logging

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from agents.coder import CoderAgent
from agents.docs import DocsAgent
from agents.reviewer import ReviewerAgent
from agents.tester import TesterAgent
from core.git_context import (
    get_changed_files,
    get_context_id,
    get_current_branch,
    get_recent_commits,
)

console = Console()
logger = logging.getLogger(__name__)

PIPELINE: list[tuple[str, type, str]] = [
    ("Coder", CoderAgent, "blue"),
    ("Reviewer", ReviewerAgent, "yellow"),
    ("Tester", TesterAgent, "green"),
    ("Docs", DocsAgent, "magenta"),
]


def run_swarm(
    task: str,
    repo_path: str = ".",
    agents: list[str] | None = None,
) -> dict[str, str]:
    branch = get_current_branch(repo_path)
    context_id = get_context_id(repo_path)
    commits = get_recent_commits(repo_path, n=3)
    changed = get_changed_files(repo_path)

    _print_header(task, branch, context_id, commits, changed)

    results: dict[str, str] = {}
    prior_output = ""

    active = [
        (name, cls, color)
        for name, cls, color in PIPELINE
        if agents is None or name.lower() in [a.lower() for a in agents]
    ]

    for name, agent_cls, color in active:
        with Progress(
            SpinnerColumn(),
            TextColumn(f"[{color}]\\[{name}][/{color}] {{task.description}}"),
            transient=True,
            console=console,
        ) as progress:
            progress.add_task("thinking...", total=None)
            output = agent_cls(repo_path=repo_path).run(
                task=task, prior_context=prior_output
            )

        console.print(
            Panel(
                output,
                title=f"[bold {color}][{name}][/bold {color}]",
                border_style=color,
            )
        )
        results[name] = output
        prior_output = output

    console.print(
        "\n[bold green]✓ Swarm complete.[/bold green] "
        "Context saved to Memori — your next session picks up exactly here.\n"
    )
    return results


def _print_header(
    task: str,
    branch: str,
    context_id: str,
    commits: list[str],
    changed: list[str],
) -> None:
    commit_lines = "\n".join(f"  {c}" for c in commits) if commits else "  (none)"
    changed_lines = ", ".join(changed) if changed else "none"

    console.print()
    console.print(
        Panel(
            f"[bold]Task:[/bold] {task}\n"
            f"[dim]Branch:[/dim]  {branch}  [dim]|  Memory scope:[/dim] {context_id}\n"
            f"[dim]Recent commits:[/dim]\n{commit_lines}\n"
            f"[dim]Changed files:[/dim] {changed_lines}",
            title="[bold cyan]Persistent Memory Dev Agents[/bold cyan]",
            border_style="cyan",
        )
    )
