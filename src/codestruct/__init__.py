"""
CodeStruct - A language-agnostic notation for describing software structure.

This module provides tools for parsing and working with CodeStruct notation,
which is a hierarchical, indentation-based format for describing code structure.
"""

from pathlib import Path
from typing import Any

from lark import Tree

from .linter import CodeStructLinter, LintMessage
from .parser import CodeStructParser, ParseError
from .transformer import CodeStructTransformer

__version__ = "0.1.0"

# Create a default parser instance for easy import
default_parser = CodeStructParser()
default_transformer = CodeStructTransformer()


def parse_string(text: str, as_dict: bool = False) -> Tree | list[dict[str, Any]]:
	"""Parse CodeStruct from a string.

	Args:
	    text: The CodeStruct text to parse
	    as_dict: Whether to return a Python dictionary instead of a parse tree

	Returns:
	    Either a Lark parse tree or a Python dictionary representation
	"""
	tree = default_parser.parse_string(text)
	if as_dict:
		return default_transformer.transform(tree)
	return tree


def parse_file(file_path: str | Path, as_dict: bool = False) -> Tree | list[dict[str, Any]]:
	"""Parse CodeStruct from a file.

	Args:
	    file_path: Path to the file to parse
	    as_dict: Whether to return a Python dictionary instead of a parse tree

	Returns:
	    Either a Lark parse tree or a Python dictionary representation
	"""
	tree = default_parser.parse_file(file_path)
	if as_dict:
		return default_transformer.transform(tree)
	return tree


def lint_files(file_paths: list[str]) -> list[LintMessage]:
	"""Lint multiple CodeStruct files.

	Args:
		file_paths: List of file paths to lint

	Returns:
		List of lint messages across all files
	"""
	linter = CodeStructLinter()
	all_messages = []

	for file_path in file_paths:
		messages = linter.lint_file(file_path)
		all_messages.extend(messages)

	return all_messages


__all__ = [
	"CodeStructLinter",
	"CodeStructParser",
	"CodeStructTransformer",
	"LintMessage",
	"ParseError",
	"lint_files",
	"parse_file",
	"parse_string",
]
