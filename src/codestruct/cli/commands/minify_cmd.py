"""Minify command for CodeStruct CLI."""

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from codestruct.minifier import CodeStructMinifier

app = typer.Typer(help="Minify CodeStruct files for LLM context compression")
console = Console()


@app.command()
def compress(
	files: list[Path],
	output: Path | None = None,
	include_legend: bool = typer.Option(default=True, help="Include legend/mapping for LLMs"),
	suffix: str = typer.Option(".min.cst", "--suffix", help="Suffix for output files when processing multiple files"),
	overwrite: bool = typer.Option(default=False, help="Overwrite existing output files"),
	stats: bool = typer.Option(default=False, help="Show compression statistics"),
) -> None:
	"""Minify CodeStruct files for LLM context compression.

	Args:
		files: CodeStruct files to minify
		output: Output file (default: stdout for single file, .min.cst for multiple)
		include_legend: Include legend/mapping for LLMs
		suffix: Suffix for output files when processing multiple files
		overwrite: Overwrite existing output files
		stats: Show compression statistics
	"""
	if not files:
		console.print("[red]Error:[/red] No files specified")
		sys.exit(1)

	minifier = CodeStructMinifier.get_instance()
	minifier.include_legend = include_legend

	files_processed = 0
	total_original_size = 0
	total_minified_size = 0

	# Handle single file to stdout
	if len(files) == 1 and output is None:
		file_path = files[0]
		if not file_path.exists():
			console.print(f"[red]Error:[/red] File not found: {file_path}")
			sys.exit(1)

		try:
			minified = minifier.minify_file(str(file_path))
			console.print(minified)

			if stats:
				original_size = len(file_path.read_text(encoding="utf-8"))
				minified_size = len(minified)
				_show_compression_stats(original_size, minified_size)

		except (OSError, UnicodeDecodeError) as e:
			console.print(f"[red]Error minifying {file_path}:[/red] {e}")
			sys.exit(1)

		return

	# Handle multiple files or specific output
	for file_path in files:
		if not file_path.exists():
			console.print(f"[red]Error:[/red] File not found: {file_path}")
			continue

		if not file_path.is_file():
			console.print(f"[red]Error:[/red] Not a file: {file_path}")
			continue

		try:
			# Determine output path
			if output and len(files) == 1:
				output_path = output
			elif output and len(files) > 1:
				# Use output as directory
				output_path = output / f"{file_path.stem}{suffix}"
			else:
				# Use same directory with suffix
				output_path = file_path.with_suffix(suffix)

			# Check if output exists and overwrite is not set
			if output_path.exists() and not overwrite:
				console.print(f"[yellow]Skipping:[/yellow] {output_path} already exists (use --overwrite)")
				continue

			# Read original content for stats
			original_content = file_path.read_text(encoding="utf-8")
			original_size = len(original_content)

			# Minify
			minified = minifier.minify_file(str(file_path))
			minified_size = len(minified)

			# Create output directory if needed
			output_path.parent.mkdir(parents=True, exist_ok=True)

			# Write minified content
			output_path.write_text(minified, encoding="utf-8")

			console.print(f"[green]Minified:[/green] {file_path} → {output_path}")

			files_processed += 1
			total_original_size += original_size
			total_minified_size += minified_size

			if stats:
				_show_compression_stats(original_size, minified_size)

		except (OSError, UnicodeDecodeError) as e:
			console.print(f"[red]Error minifying {file_path}:[/red] {e}")
			continue

	# Overall summary
	if files_processed > 1:
		console.print("\n[bold]Summary:[/bold]")
		console.print(f"Files processed: {files_processed}")

		if stats and total_original_size > 0:
			compression_ratio = (1 - total_minified_size / total_original_size) * 100
			console.print(f"Total original size: {total_original_size:,} bytes")
			console.print(f"Total minified size: {total_minified_size:,} bytes")
			console.print(f"Overall compression: {compression_ratio:.1f}%")


@app.command()
def legend() -> None:
	"""Show the minification legend/mapping."""
	minifier = CodeStructMinifier.get_instance()
	legend_text = _generate_legend_text(minifier)
	console.print(legend_text)


@app.command()
def analyze(
	files: list[Path],
	show_mappings: bool = typer.Option(default=False, help="Show detailed keyword and attribute mappings"),
) -> None:
	"""Analyze files and show potential compression statistics."""
	if not files:
		console.print("[red]Error:[/red] No files specified")
		sys.exit(1)

	minifier = CodeStructMinifier.get_instance()

	table = Table(title="Minification Analysis")
	table.add_column("File", style="cyan")
	table.add_column("Original Size", style="yellow", justify="right")
	table.add_column("Minified Size", style="green", justify="right")
	table.add_column("Compression", style="magenta", justify="right")
	table.add_column("Status", style="white")

	total_original = 0
	total_minified = 0
	files_analyzed = 0

	for file_path in files:
		if not file_path.exists():
			table.add_row(str(file_path), "—", "—", "—", "[red]Not found[/red]")
			continue

		if not file_path.is_file():
			table.add_row(str(file_path), "—", "—", "—", "[red]Not a file[/red]")
			continue

		try:
			original_content = file_path.read_text(encoding="utf-8")
			original_size = len(original_content)

			minified = minifier.minify_string(original_content)
			minified_size = len(minified)

			compression_ratio = (1 - minified_size / original_size) * 100 if original_size > 0 else 0

			table.add_row(
				str(file_path),
				f"{original_size:,}",
				f"{minified_size:,}",
				f"{compression_ratio:.1f}%",
				"[green]✓[/green]",
			)

			total_original += original_size
			total_minified += minified_size
			files_analyzed += 1

		except (OSError, UnicodeDecodeError) as e:
			table.add_row(str(file_path), "—", "—", "—", f"[red]Error: {e}[/red]")

	console.print(table)

	if files_analyzed > 0:
		overall_compression = (1 - total_minified / total_original) * 100 if total_original > 0 else 0
		console.print("\n[bold]Overall Statistics:[/bold]")
		console.print(f"Files analyzed: {files_analyzed}")
		console.print(f"Total original size: {total_original:,} bytes")
		console.print(f"Total minified size: {total_minified:,} bytes")
		console.print(f"Overall compression: {overall_compression:.1f}%")

	if show_mappings:
		_show_mappings(minifier)


def _show_compression_stats(original_size: int, minified_size: int) -> None:
	"""Show compression statistics for a single file."""
	compression_ratio = (1 - minified_size / original_size) * 100 if original_size > 0 else 0

	console.print(f"  Original size: {original_size:,} bytes")
	console.print(f"  Minified size: {minified_size:,} bytes")
	console.print(f"  Compression: {compression_ratio:.1f}%")


def _show_mappings(minifier: CodeStructMinifier) -> None:
	"""Show detailed keyword and attribute mappings."""
	console.print("\n[bold]Keyword Mappings:[/bold]")
	for original, short in minifier.keyword_map.items():
		console.print(f"  {original} → {short}")

	console.print("\n[bold]Attribute Mappings:[/bold]")
	for original, short in minifier.attr_key_map.items():
		console.print(f"  {original} → {short}")

	console.print("\n[bold]Type Mappings:[/bold]")
	for original, short in minifier.type_map.items():
		console.print(f"  {original} → {short}")


def _generate_legend_text(minifier: CodeStructMinifier) -> str:
	"""Generate the legend text for interpreting minified CodeStruct."""
	keyword_mappings = [f"{short}={long}" for long, short in minifier.keyword_map.items()]
	attr_mappings = [f"{short}={long}" for long, short in minifier.attr_key_map.items()]
	type_mappings = [f"{short}={long}" for long, short in minifier.type_map.items()]

	legend = [
		"# CodeStruct Minified Format Legend",
		"# Format: Entity;Entity|Child,Child[Attribute,Attribute]",
		f"# Keywords: {','.join(keyword_mappings)}",
		f"# Attributes: {','.join(attr_mappings)}",
		f"# Types: {','.join(type_mappings)}",
		"# Delimiters: ;=entity separator, |=child separator, ,=attribute separator, "
		"&=entity grouping, []=attribute container",
		"# Notes: impl: blocks and hash IDs (:::) are omitted in minified format",
	]

	return "\n".join(legend)
