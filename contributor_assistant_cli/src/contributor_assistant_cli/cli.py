"""Command-line interface for the contributor assistant."""

import click
from dotenv import load_dotenv
from rich.console import Console

from contributor_assistant_cli.config import Config
from contributor_assistant_cli.core import ContributorAssistant
from contributor_assistant_cli.llm_manager import LLMManager

# Load environment variables from .env file
load_dotenv()

console = Console()


@click.group()
@click.version_option()
def main() -> None:
    """Memori Contributor Assistant - Help with contributing to Memori."""
    pass


@main.command()
@click.option(
    "--provider",
    type=click.Choice(LLMManager.get_available_providers()),
    default="anthropic",
    help="LLM provider to use",
)
def init(provider: str) -> None:
    """Initialize the contributor assistant."""
    config = Config()

    if config.is_initialized():
        if not click.confirm("Configuration already exists. Reset and reinitialize?"):
            console.print("[yellow]Skipped initialization[/yellow]")
            return
        config.reset()

    console.print("[bold cyan]Welcome to Memori Contributor Assistant![/bold cyan]\n")

    # Contribution type
    console.print("What would you like to contribute to Memori?")
    contribution_types = ["Bug fixes", "New features", "Documentation"]
    for i, ct in enumerate(contribution_types, 1):
        console.print(f"  {i}. {ct}")
    choice = click.prompt("Choice", type=click.IntRange(1, len(contribution_types)))
    contribution_type = contribution_types[choice - 1].lower()

    # Areas of interest
    console.print("\nWhich areas interest you? (comma-separated)")
    areas = [
        "Anthropic adapter",
        "Storage layer",
        "Memory augmentation",
        "Testing patterns",
        "Documentation",
        "Other",
    ]
    for i, area in enumerate(areas, 1):
        console.print(f"  {i}. {area}")

    area_input = click.prompt("Enter numbers separated by commas", default="1,2,3")
    selected_areas = [
        areas[int(i.strip()) - 1]
        for i in area_input.split(",")
        if i.strip().isdigit() and 1 <= int(i.strip()) <= len(areas)
    ]

    if not selected_areas:
        selected_areas = [areas[0], areas[1]]

    # Save configuration
    config.initialize(contribution_type, selected_areas, provider)

    console.print(
        f"\n[bold green]✅ Initialized![/bold green]\n"
        f"Provider: [cyan]{provider}[/cyan]\n"
        f"Contribution type: [cyan]{contribution_type}[/cyan]\n"
        f"Areas: [cyan]{', '.join(selected_areas)}[/cyan]\n"
    )

    console.print(
        "Run [bold]contributor-assistant ask 'your question'[/bold] to get started!\n"
    )


@main.command()
@click.argument("question")
@click.option(
    "--provider",
    type=click.Choice(LLMManager.get_available_providers()),
    help="Override default LLM provider",
)
def ask(question: str, provider: str | None) -> None:
    """Ask the assistant a question."""
    config = Config()

    if not config.is_initialized():
        console.print(
            "[red]❌ Not initialized![/red] Run [bold]contributor-assistant init[/bold] first.\n"
        )
        return

    # Get provider from config or use override
    if provider is None:
        provider = config.get("default_provider", "anthropic")

    console.print(f"\n[dim]Using provider: {provider}[/dim]\n")

    try:
        assistant = ContributorAssistant(
            llm_provider=provider,
            entity_id=config.get("entity_id"),
        )

        console.print("[cyan]🤔 Thinking...[/cyan]")
        response = assistant.ask(question)

        console.print(f"\n[bold blue]Assistant:[/bold blue]\n{response}\n")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]\n")


@main.command()
def context() -> None:
    """Show current context and stored facts."""
    config = Config()

    if not config.is_initialized():
        console.print(
            "[red]❌ Not initialized![/red] Run [bold]contributor-assistant init[/bold] first.\n"
        )
        return

    console.print("\n[bold cyan]📚 Current Context[/bold cyan]\n")

    # Display configuration
    console.print(f"Entity ID: [cyan]{config.get('entity_id')}[/cyan]")
    console.print(f"Provider: [cyan]{config.get('default_provider')}[/cyan]")
    console.print(f"Contribution Type: [cyan]{config.get('contribution_type')}[/cyan]")

    areas = config.get("areas_of_interest", [])
    if areas:
        console.print("Areas of Interest:")
        for area in areas:
            console.print(f"  • [cyan]{area}[/cyan]")

    console.print(f"\nDatabase: [cyan]{config.get('database_path')}[/cyan]\n")

    # Try to load stored facts
    try:
        provider = config.get("default_provider", "anthropic")
        assistant = ContributorAssistant(
            llm_provider=provider,
            entity_id=config.get("entity_id"),
        )
        ctx = assistant.get_context()

        if ctx.get("facts"):
            console.print("[bold]Stored Facts:[/bold]")
            for fact in ctx["facts"]:
                console.print(f"  • {fact}")
        else:
            console.print(
                "[dim]No facts stored yet. Ask questions to build memories![/dim]"
            )
    except Exception as e:
        console.print(f"[dim]Could not retrieve facts: {e}[/dim]")

    console.print()


@main.command()
def provider() -> None:
    """Show or change the default LLM provider."""
    config = Config()

    if not config.is_initialized():
        console.print(
            "[red]❌ Not initialized![/red] Run [bold]contributor-assistant init[/bold] first.\n"
        )
        return

    current = config.get("default_provider", "anthropic")
    console.print(f"\nCurrent provider: [bold cyan]{current}[/bold cyan]\n")

    available = LLMManager.get_available_providers()
    console.print("Available providers:")
    for i, p in enumerate(available, 1):
        console.print(f"  {i}. {p}")

    choice = click.prompt(
        "\nChange provider? (1-4, or press Enter to skip)",
        type=click.IntRange(1, len(available)),
        default=0,
        show_default=False,
    )

    if choice > 0:
        new_provider = available[choice - 1]
        cfg_dict = config.load()
        cfg_dict["default_provider"] = new_provider
        config.save(cfg_dict)
        console.print(
            f"\n[bold green]✅ Provider changed to {new_provider}[/bold green]\n"
        )
    else:
        console.print("[yellow]No changes[/yellow]\n")


@main.command()
def reset() -> None:
    """Reset configuration and clear all memories."""
    config = Config()

    if not config.is_initialized():
        console.print("[yellow]Already reset[/yellow]\n")
        return

    if click.confirm(
        "Are you sure? This will delete all stored memories and configuration."
    ):
        config.reset()
        console.print("[bold green]✅ Reset complete![/bold green]\n")
    else:
        console.print("[yellow]Cancelled[/yellow]\n")


if __name__ == "__main__":
    main()
