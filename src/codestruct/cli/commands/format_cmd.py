"""Format command for CodeStruct CLI."""

import sys
from pathlib import Path

import typer
from rich.console import Console

from codestruct.formatter import CodeStructFormatter

app = typer.Typer(help="Format and auto-fix CodeStruct files")
console = Console()


@app.command()
def fix(
	files: list[Path],
	indent_size: int = typer.Option(2, "--indent", "-i", help="Number of spaces for indentation (2 or 4)"),
	auto_add_docs: bool = typer.Option(default=True, help="Automatically add placeholder documentation"),
	auto_fix: bool = typer.Option(default=True, help="Apply automatic fixes for linting issues"),
	in_place: bool = typer.Option(default=False, help="Modify files in place"),
	check_only: bool = typer.Option(default=False, help="Check if files would be reformatted (don't modify)"),
	diff: bool = typer.Option(default=False, help="Show diff of changes that would be made"),
	backup: bool = typer.Option(default=True, help="Create backup files when modifying in place"),
) -> None:
	"""Format CodeStruct files and optionally auto-fix issues."""
	if not files:
		console.print("[red]Error:[/red] No files specified")
		sys.exit(1)

	if indent_size not in (2, 4):
		console.print("[red]Error:[/red] Indent size must be 2 or 4")
		sys.exit(1)

	formatter = CodeStructFormatter.get_instance(indent_size, auto_add_docs)
	files_changed = 0
	files_processed = 0
	total_issues_fixed = 0

	for file_path in files:
		if not file_path.exists():
			console.print(f"[red]Error:[/red] File not found: {file_path}")
			continue

		if not file_path.is_file():
			console.print(f"[red]Error:[/red] Not a file: {file_path}")
			continue

		files_processed += 1

		try:
			# Read original content
			original_content = file_path.read_text(encoding="utf-8")

			# Format the content
			formatted_content, remaining_messages = formatter.format_string(original_content, auto_fix)

			# Check if content changed
			content_changed = original_content != formatted_content

			if check_only:
				if content_changed:
					console.print(f"[yellow]Would reformat:[/yellow] {file_path}")
					files_changed += 1
				else:
					console.print(f"[green]Already formatted:[/green] {file_path}")
				continue

			if diff and content_changed:
				_show_diff(file_path, original_content, formatted_content)
				continue

			if content_changed:
				if in_place:
					# Create backup if requested
					if backup:
						backup_path = file_path.with_suffix(file_path.suffix + ".bak")
						backup_path.write_text(original_content, encoding="utf-8")
						console.print(f"[blue]Backup created:[/blue] {backup_path}")

					# Write formatted content
					file_path.write_text(formatted_content, encoding="utf-8")
					console.print(f"[green]Formatted:[/green] {file_path}")
					files_changed += 1
				else:
					# Output to stdout
					console.print(f"\n[bold]Formatted content for {file_path}:[/bold]")
					console.print(formatted_content)
			else:
				console.print(f"[green]No changes needed:[/green] {file_path}")

			# Count issues that were fixed
			if auto_fix:
				# Get original issues count
				try:
					from codestruct.linter import CodeStructLinter

					linter = CodeStructLinter.get_instance()
					original_messages = linter.lint_file(str(file_path))
					issues_fixed = len(original_messages) - len(remaining_messages)
					total_issues_fixed += max(0, issues_fixed)
				except (ImportError, OSError, UnicodeDecodeError):
					# If we can't get original issues, skip counting
					pass

			# Show remaining issues if any
			if remaining_messages:
				console.print(f"[yellow]Remaining issues in {file_path}:[/yellow]")
				for msg in remaining_messages:
					console.print(f"  {msg.line}:{msg.col}: {msg.code} - {msg.message}")

		except (OSError, UnicodeDecodeError) as e:
			console.print(f"[red]Error processing {file_path}:[/red] {e}")
			continue

	# Summary
	console.print("\n[bold]Summary:[/bold]")
	console.print(f"Files processed: {files_processed}")

	if check_only:
		console.print(f"Files that would be reformatted: {files_changed}")
		if files_changed > 0:
			sys.exit(1)
	else:
		console.print(f"Files changed: {files_changed}")
		if auto_fix and total_issues_fixed > 0:
			console.print(f"Issues auto-fixed: {total_issues_fixed}")


@app.command()
def check(
	files: list[Path],
	indent_size: int = typer.Option(2, "--indent", "-i", help="Number of spaces for indentation (2 or 4)"),
) -> None:
	"""Check if files are properly formatted without making changes."""
	if not files:
		console.print("[red]Error:[/red] No files specified")
		sys.exit(1)

	if indent_size not in (2, 4):
		console.print("[red]Error:[/red] Indent size must be 2 or 4")
		sys.exit(1)

	formatter = CodeStructFormatter.get_instance(indent_size, auto_add_docs=False)
	files_need_formatting = 0
	files_processed = 0

	for file_path in files:
		if not file_path.exists():
			console.print(f"[red]Error:[/red] File not found: {file_path}")
			continue

		if not file_path.is_file():
			console.print(f"[red]Error:[/red] Not a file: {file_path}")
			continue

		files_processed += 1

		try:
			original_content = file_path.read_text(encoding="utf-8")
			formatted_content, _ = formatter.format_string(original_content, auto_fix=False)

			if original_content != formatted_content:
				console.print(f"[yellow]Needs formatting:[/yellow] {file_path}")
				files_need_formatting += 1
			else:
				console.print(f"[green]Properly formatted:[/green] {file_path}")

		except (OSError, UnicodeDecodeError) as e:
			console.print(f"[red]Error checking {file_path}:[/red] {e}")
			continue

	console.print("\n[bold]Summary:[/bold]")
	console.print(f"Files checked: {files_processed}")
	console.print(f"Files needing formatting: {files_need_formatting}")

	if files_need_formatting > 0:
		sys.exit(1)


def _show_diff(file_path: Path, original: str, formatted: str) -> None:
	"""Show diff between original and formatted content."""
	import difflib

	console.print(f"\n[bold]Diff for {file_path}:[/bold]")

	diff = difflib.unified_diff(
		original.splitlines(keepends=True),
		formatted.splitlines(keepends=True),
		fromfile=f"a/{file_path}",
		tofile=f"b/{file_path}",
		lineterm="",
	)

	for line in diff:
		line_content = line.rstrip()
		if line_content.startswith(("+++", "---")):
			console.print(f"[bold]{line_content}[/bold]")
		elif line_content.startswith("@@"):
			console.print(f"[cyan]{line_content}[/cyan]")
		elif line_content.startswith("+"):
			console.print(f"[green]{line_content}[/green]")
		elif line_content.startswith("-"):
			console.print(f"[red]{line_content}[/red]")
		else:
			console.print(line_content)
