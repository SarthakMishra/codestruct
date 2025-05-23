"""Lint command for CodeStruct CLI."""

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from codestruct.linter import CodeStructLinter, LintMessage

app = typer.Typer(help="Lint CodeStruct files for issues and style violations")
console = Console()


@app.command()
def check(
	files: list[Path],
	format_output: str = typer.Option("table", "--format", "-f", help="Output format: table, json, or text"),
	exit_code: bool = typer.Option(default=True, help="Exit with non-zero code if issues found"),
	show_stats: bool = typer.Option(default=False, help="Show statistics summary"),
	filter_codes: str | None = typer.Option(
		default=None, help="Filter by error codes (comma-separated, e.g., CS101,CS201)"
	),
) -> None:
	"""Check CodeStruct files for linting issues."""
	if not files:
		console.print("[red]Error:[/red] No files specified")
		sys.exit(1)

	linter = CodeStructLinter.get_instance()
	all_messages = []
	file_count = 0
	error_count = 0

	# Parse filter codes if provided
	filter_set = None
	if filter_codes:
		filter_set = {code.strip() for code in filter_codes.split(",")}

	for file_path in files:
		if not file_path.exists():
			console.print(f"[red]Error:[/red] File not found: {file_path}")
			continue

		if not file_path.is_file():
			console.print(f"[red]Error:[/red] Not a file: {file_path}")
			continue

		file_count += 1
		messages = linter.lint_file(str(file_path))

		# Apply filter if specified
		if filter_set:
			messages = [msg for msg in messages if msg.code in filter_set]

		all_messages.extend(messages)
		error_count += len(messages)

	if not all_messages:
		console.print("[green]✓[/green] No linting issues found!")
		if show_stats:
			_show_stats(file_count, 0, 0)
		return

	# Display results based on format
	if format_output == "table":
		_display_table(all_messages)
	elif format_output == "json":
		_display_json(all_messages)
	else:  # text format
		_display_text(all_messages)

	if show_stats:
		_show_stats(file_count, error_count, len(all_messages))

	if exit_code and all_messages:
		sys.exit(1)


@app.command()
def codes() -> None:
	"""Show available lint error codes and their descriptions."""
	table = Table(title="CodeStruct Lint Error Codes")
	table.add_column("Code", style="cyan", no_wrap=True)
	table.add_column("Category", style="yellow")
	table.add_column("Description", style="white")

	# Error codes from the linter
	codes_info = [
		("CS001", "Parse", "Parse error in CodeStruct file"),
		("CS002", "File", "File not found"),
		("CS003", "File", "Permission denied"),
		("CS004", "File", "Unicode decode error"),
		("CS005", "File", "OS error"),
		("CS101", "Naming", "Entity name is too short"),
		("CS201", "Documentation", "Missing documentation"),
		("CS301", "Hash", "Hash ID format violation"),
		("CS401", "Attributes", "Attribute naming convention violation"),
	]

	for code, category, description in codes_info:
		table.add_row(code, category, description)

	console.print(table)


def _display_table(messages: list[LintMessage]) -> None:
	"""Display lint messages in a table format."""
	table = Table(title="Linting Issues")
	table.add_column("File", style="cyan")
	table.add_column("Line", style="yellow", justify="right")
	table.add_column("Col", style="yellow", justify="right")
	table.add_column("Code", style="red")
	table.add_column("Message", style="white")

	for msg in messages:
		table.add_row(str(msg.file_path), str(msg.line), str(msg.col), msg.code, msg.message)

	console.print(table)


def _display_json(messages: list[LintMessage]) -> None:
	"""Display lint messages in JSON format."""
	data = [
		{"file": msg.file_path, "line": msg.line, "column": msg.col, "code": msg.code, "message": msg.message}
		for msg in messages
	]

	console.print(json.dumps(data, indent=2))


def _display_text(messages: list[LintMessage]) -> None:
	"""Display lint messages in plain text format."""
	for msg in messages:
		console.print(f"{msg.file_path}:{msg.line}:{msg.col}: {msg.code} - {msg.message}")


def _show_stats(file_count: int, error_count: int, message_count: int) -> None:
	"""Show statistics summary."""
	console.print("\n[bold]Statistics:[/bold]")
	console.print(f"Files checked: {file_count}")
	console.print(f"Issues found: {message_count}")

	if message_count == 0:
		console.print("[green]All files passed linting![/green]")
	else:
		console.print(f"[red]Found {message_count} issue(s) across {error_count} file(s)[/red]")
