"""
Persistent Memory Dev Agent — CLI entry point

Usage:
    python run.py swarm "Add JWT refresh token support"
    python run.py swarm "Refactor DB layer" --agents coder,reviewer
    python run.py token-demo
    python run.py branch-status
"""

import logging
import sys

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()
console = Console()


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cli(debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        format="%(name)s | %(levelname)s | %(message)s",
    )


@cli.command()
@click.argument("task")
@click.option(
    "--agents",
    default=None,
    help="Comma-separated subset of agents to run: coder,reviewer,tester,docs",
)
@click.option(
    "--repo",
    default=".",
    show_default=True,
    help="Path to the git repository to use as memory scope",
)
def swarm(task: str, agents: str | None, repo: str) -> None:
    """Run the full agent swarm on TASK, scoped to the current git branch."""
    from swarm import run_swarm

    agent_list = [a.strip() for a in agents.split(",")] if agents else None
    run_swarm(task=task, repo_path=repo, agents=agent_list)


@cli.command("token-demo")
def token_demo() -> None:
    """Show the before/after token usage comparison powered by Memori recall."""
    from demos.token_savings import run_demo

    run_demo()


@cli.command("branch-status")
@click.option("--repo", default=".", show_default=True, help="Path to the git repository")
def branch_status(repo: str) -> None:
    """Show the current branch memory scope and recent git context."""
    from core.git_context import (
        get_changed_files,
        get_context_id,
        get_current_branch,
        get_recent_commits,
    )

    branch = get_current_branch(repo)
    context_id = get_context_id(repo)
    commits = get_recent_commits(repo, n=5)
    changed = get_changed_files(repo)

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_row("[dim]Branch[/dim]", f"[bold]{branch}[/bold]")
    table.add_row("[dim]Memory scope[/dim]", context_id)
    table.add_row(
        "[dim]Recent commits[/dim]",
        "\n".join(commits) if commits else "[dim]none[/dim]",
    )
    table.add_row(
        "[dim]Changed files[/dim]",
        ", ".join(changed) if changed else "[dim]none[/dim]",
    )

    console.print()
    console.print(
        Panel(table, title="[bold cyan]Persistent Memory Dev Agent — Branch Status[/bold cyan]", border_style="cyan")
    )
    console.print(
        "\n[dim]Tip: switch branches with [bold]git checkout[/bold] and the swarm "
        "automatically loads that branch's memory context.[/dim]\n"
    )


if __name__ == "__main__":
    cli()
