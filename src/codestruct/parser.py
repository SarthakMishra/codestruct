"""CodeStruct grammar."""

import re
from collections.abc import Generator, Iterator
from pathlib import Path

from lark import Lark, Tree, logger
from lark.exceptions import (
	ParseError as LarkParseError,
)
from lark.exceptions import (
	UnexpectedCharacters,
	UnexpectedInput,
	UnexpectedToken,
)
from lark.indenter import Indenter as LarkIndenter
from lark.lexer import Token


# Define a custom indenter that recognizes _NEWLINE
class CustomIndenter(LarkIndenter):
	"""Custom Lark Indenter to handle _NEWLINE tokens for indentation."""

	@property
	def NL_type(self) -> str:
		return "_NEWLINE"

	@property
	def INDENT_type(self) -> str:
		return "_INDENT"

	@property
	def DEDENT_type(self) -> str:
		return "_DEDENT"

	@property
	def tab_len(self) -> int:
		return 8

	@property
	def OPEN_PAREN_types(self) -> list[str]:
		return []

	@property
	def CLOSE_PAREN_types(self) -> list[str]:
		return []

	@property
	def always_accept(self) -> tuple[str, ...]:  # type: ignore[override]
		"""Allow newline, comment, and code block tokens to pass through the lexer regardless of parser state."""
		return (self.NL_type, "COMMENT", "CODE_BLOCK_RAW")

	def __init__(self) -> None:
		"""Initialize the CustomIndenter."""
		super().__init__()  # Call super's init first

		logger.debug("__init__ called.")
		logger.debug(f"__init__: self.NL_type (from ClassVar) = {self.NL_type!r}")
		logger.debug(f"__init__: self.INDENT_type (from ClassVar) = {self.INDENT_type!r}")
		logger.debug(f"__init__: self.DEDENT_type (from ClassVar) = {self.DEDENT_type!r}")
		logger.debug(f"__init__: self.tab_len (from ClassVar) = {self.tab_len!r}")
		logger.debug(f"__init__: self.OPEN_PAREN_types (from ClassVar) = {self.OPEN_PAREN_types!r}")
		logger.debug(f"__init__: self.CLOSE_PAREN_types (from ClassVar) = {self.CLOSE_PAREN_types!r}")

		# Ensure inherited state is also what we expect
		logger.debug(f"__init__: self.indent_level = {self.indent_level!r}")
		logger.debug(f"__init__: self.paren_level = {self.paren_level!r}")

	def process(self, stream: Iterator[Token]) -> Generator[Token, None, None]:
		logger.debug("process() method called.")
		logger.debug(f"process(): Stream type: {type(stream)}")
		logger.debug(f"process(): self.NL_type = {self.NL_type!r}")
		logger.debug(f"process(): self.paren_level (before super call) = {self.paren_level!r}")
		logger.debug(f"process(): self.indent_level (before super call) = {self.indent_level!r}")

		yielded_token_count = 0
		try:
			# Ensure we call the base class's process method to get actual indentation
			for token in super().process(stream):
				yielded_token_count += 1
				# logger.debug(f"process() yielding from super: {token!r}") # Potentially too verbose
				yield token
		except Exception as e:
			logger.debug(f"process(): Exception during super().process(): {e!r}")
			raise
		finally:
			logger.debug(
				f"process() method finished executing super().process(). Yielded {yielded_token_count} tokens."
			)
			logger.debug(f"process(): self.paren_level (after super call) = {self.paren_level!r}")
			logger.debug(f"process(): self.indent_level (after super call) = {self.indent_level!r}")

	def _process_new_line(self, token: Token) -> Iterator[Token]:  # token is NL_type
		logger.debug(f"_process_new_line CALLED with token: {token!r}")
		logger.debug(f"_process_new_line: Current indent_level (before super call): {self.indent_level!r}")
		logger.debug(f"_process_new_line: self.NL_type = {self.NL_type!r}")

		# We will call the super method and log what it yields.
		# This shows us the decisions made by the base Indenter logic.
		original_tokens_yielded_by_super_process_new_line = []
		try:
			for t in super()._process_new_line(token):  # type: ignore[misc]
				original_tokens_yielded_by_super_process_new_line.append(repr(t))
				yield t  # Pass the token through to the parser
		except Exception as e:
			logger.debug(f"_process_new_line: Exception in super()._process_new_line: {e!r}")
			raise
		finally:
			logger.debug(f"_process_new_line: super()._process_new_line for {token!r} finished.")
			logger.debug(
				f"_process_new_line: Tokens yielded by super's _process_new_line: {original_tokens_yielded_by_super_process_new_line}"  # noqa: E501
			)
			logger.debug(f"_process_new_line: Current indent_level (after super call): {self.indent_level!r}")


# Custom Exception for Parser
class ParseError(LarkParseError):
	"""Custom exception for parsing errors, providing context."""

	# Keep it simple for now, or add context later if needed


class CodeStructParser:
	"""Parser for CodeStruct notation."""

	def __init__(self, debug: bool = False) -> None:
		"""Initialize the CodeStruct parser.

		Args:
		    debug: Whether to enable debug mode for the parser
		"""
		grammar_path = Path(__file__).parent / "codestruct.lark"
		try:
			self.parser = Lark(
				grammar_path.read_text(),
				parser="lalr",
				lexer="contextual",
				postlex=CustomIndenter(),
				start="start",
				debug=debug,
				keep_all_tokens=True,  # Essential for Indenter to see all physical tokens
				propagate_positions=True,
			)
		except Exception as e:
			msg = f"Error initializing parser: {e!s}"
			raise LarkParseError(msg) from e

	def parse_string(self, text: str) -> Tree:
		"""Parse CodeStruct from a string.

		Args:
		    text: The CodeStruct text to parse

		Returns:
		    A Lark parse tree

		Raises:
		    ParseError: If the input cannot be parsed
		"""
		# Strip trailing spaces from each line to avoid stray indent tokens
		text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
		# Ensure there's a terminating newline for proper parsing (especially for last statement)
		if text and not text.endswith("\n"):
			text += "\n"
		try:
			return self.parser.parse(text)
		except (UnexpectedInput, UnexpectedToken, UnexpectedCharacters) as e:
			# Improve error message with line and column info
			line, col = e.line, e.column

			# Get the problematic line
			lines = text.split("\n")
			if 0 <= line - 1 < len(lines):
				error_line = lines[line - 1]
				pointer = " " * (col - 1) + "^"  # Adjusted col for 0-indexed pointer
				context = f"\nLine {line}:\n{error_line}\n{pointer}"
			else:
				context = f" at line {line}, column {col}"

			msg = f"Error parsing CodeStruct{context}: {e!s}"
			raise ParseError(msg) from e

	def parse_file(self, file_path: str | Path) -> Tree:
		"""Parse CodeStruct from a file.

		Args:
		    file_path: The path to the CodeStruct file to parse

		Returns:
		    A Lark parse tree

		Raises:
		    ParseError: If the file is not found or input cannot be parsed
		"""
		try:
			file_path_obj = Path(file_path)
			with file_path_obj.open() as file:
				return self.parse_string(file.read())
		except FileNotFoundError as e:
			msg = f"File not found: {file_path}"
			raise ParseError(msg) from e
		except ParseError:  # Already a ParseError, just re-raise
			raise
		except Exception as e:
			msg = f"Error parsing file '{file_path}': {e!s}"
			# Attempt to get Lark-specific error details if it's a Lark exception
			if isinstance(e, (UnexpectedInput, UnexpectedToken, UnexpectedCharacters)):
				# Improve error message with line and column info
				line, col = e.line, e.column
				# Get the problematic line (this requires reading the file again, or passing content)
				# For simplicity, we'll just use the line/col from the exception if available
				context = f" at line {line}, column {col}"
				msg = f"Error parsing file '{file_path}'{context}: {e!s}"
			raise ParseError(msg) from e
