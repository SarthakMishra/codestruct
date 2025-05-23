"""Main CLI application for CodeStruct."""

import typer
from rich.console import Console
from rich.table import Table

from codestruct import __version__

from .commands import format_cmd, lint_cmd, minify_cmd

# Create the main Typer app
app = typer.Typer(
	name="codestruct",
	help="CodeStruct: A plain-text notation for describing software structure.",
	add_completion=False,
	rich_markup_mode="rich",
)

# Add commands
app.add_typer(lint_cmd.app, name="lint", help="Lint CodeStruct files")
app.add_typer(format_cmd.app, name="format", help="Format CodeStruct files")
app.add_typer(minify_cmd.app, name="minify", help="Minify CodeStruct files")

console = Console()


@app.command()
def version() -> None:
	"""Show the version of CodeStruct."""
	console.print(f"CodeStruct version: [bold green]{__version__}[/bold green]")


@app.command()
def info() -> None:
	"""Show information about CodeStruct."""
	table = Table(title="CodeStruct Information")
	table.add_column("Component", style="cyan", no_wrap=True)
	table.add_column("Description", style="magenta")

	table.add_row("Parser", "Parse CodeStruct notation files")
	table.add_row("Linter", "Check CodeStruct files for issues")
	table.add_row("Formatter", "Format and auto-fix CodeStruct files")
	table.add_row("Minifier", "Compress CodeStruct files for LLM context")
	table.add_row("Transformer", "Transform parse trees to structured data")

	console.print(table)


if __name__ == "__main__":
	app()
