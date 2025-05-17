"""CodeStruct Linter for checking CodeStruct notation files."""

import re
from pathlib import Path

from lark import Token, Tree
from lark.exceptions import UnexpectedToken

from .parser import CodeStructParser, ParseError


class LintMessage:
	"""A message produced by the linter."""

	def __init__(self, file_path: str, line: int, col: int, code: str, message: str) -> None:
		"""Initialize a lint message."""
		self.file_path = file_path
		self.line = line
		self.col = col
		self.code = code
		self.message = message

	def __str__(self) -> str:
		"""Return a string representation of the lint message."""
		return f"{self.file_path}:{self.line}:{self.col}: {self.code} - {self.message}"


class CodeStructLinter:
	"""Linter for CodeStruct notation."""

	def __init__(self) -> None:
		"""Initialize the linter."""
		self.parser = CodeStructParser()
		self.rules = [
			self.check_short_names,
			self.check_missing_doc,
			self.check_hash_format,
			self.check_attribute_naming,
		]

	def lint_file(self, file_path: str) -> list[LintMessage]:
		"""Lint a CodeStruct file.

		Args:
			file_path: Path to the file to lint

		Returns:
			List of lint messages
		"""
		try:
			path = Path(file_path)
			content = path.read_text()
			tree = self.parser.parse_string(content)
			return self.lint_tree(tree, file_path)
		except ParseError as e:
			# Handle parse error as a lint error
			line, col = 1, 0
			# Try to get line/col from underlying exception if available
			if hasattr(e, "__cause__") and isinstance(e.__cause__, UnexpectedToken):
				line = getattr(e.__cause__, "line", 1)
				col = getattr(e.__cause__, "column", 0)
			return [LintMessage(file_path, line, col, "CS001", f"Parse error: {e!s}")]
		except FileNotFoundError:
			return [LintMessage(file_path, 1, 0, "CS002", f"File not found: {file_path}")]
		except PermissionError:
			return [LintMessage(file_path, 1, 0, "CS003", f"Permission denied: {file_path}")]
		except UnicodeDecodeError as e:
			return [LintMessage(file_path, 1, 0, "CS004", f"Unicode decode error: {e!s}")]
		except OSError as e:
			return [LintMessage(file_path, 1, 0, "CS005", f"OS error: {e!s}")]

	def lint_tree(self, tree: Tree, file_path: str) -> list[LintMessage]:
		"""Lint a parsed CodeStruct tree.

		Args:
			tree: Parsed Lark tree
			file_path: Source file path for messages

		Returns:
			List of lint messages
		"""
		messages = []
		for rule in self.rules:
			messages.extend(rule(tree, file_path))
		return messages

	def check_short_names(self, tree: Tree, file_path: str) -> list[LintMessage]:
		"""Check for overly short entity names.

		Args:
			tree: Parsed Lark tree
			file_path: Source file path for messages

		Returns:
			List of lint messages
		"""
		messages = []

		for entity_node in tree.find_data("entity_name"):
			if entity_node.children and isinstance(entity_node.children[0], Token):
				token = entity_node.children[0]
				name = token.value.strip()
				if len(name) == 1:
					messages.append(
						LintMessage(
							file_path,
							getattr(token, "line", 1),
							getattr(token, "column", 0),
							"CS101",
							f"Entity name '{name}' is too short",
						)
					)
		return messages

	def check_missing_doc(self, tree: Tree, file_path: str) -> list[LintMessage]:
		"""Check for entities missing documentation.

		Args:
			tree: Parsed Lark tree
			file_path: Source file path for messages

		Returns:
			List of lint messages
		"""
		messages = []

		# Find entities (module, class, func) that don't have a doc_field
		for entity in tree.find_data("entity"):
			entity_type: str | None = None
			entity_name: str | None = None
			entity_line = 1
			entity_col = 0

			# Get entity type and name
			for child in entity.children:
				if isinstance(child, Tree) and child.data == "entity_line":
					# Get position from the entity_line for error reporting
					if hasattr(child, "meta"):
						entity_line = getattr(child.meta, "line", 1)
						entity_col = getattr(child.meta, "column", 0)

					# Process children to find type and name
					for i, subchild in enumerate(child.children):
						if i == 0 and isinstance(subchild, Token):  # First child is the keyword
							entity_type = subchild.value.rstrip(":")
						elif i == 1 and isinstance(subchild, Token):  # Second child is the name
							entity_name = subchild.value.strip()

			# Skip entities that aren't module/class/func
			if not entity_type or entity_type not in ["module", "class", "func"]:
				continue

			# Check if this entity has a doc_field
			has_doc = False
			for child in entity.children:
				if isinstance(child, Tree) and child.data == "child_block":
					for subchild in child.children:
						if isinstance(subchild, Tree) and subchild.data == "doc_field":
							has_doc = True
							break

			if not has_doc and entity_name:
				entity_type_str = entity_type.capitalize() if entity_type else "Entity"
				messages.append(
					LintMessage(
						file_path,
						entity_line,
						entity_col,
						"CS201",
						f"{entity_type_str} '{entity_name}' is missing documentation",
					)
				)

		return messages

	def check_hash_format(self, tree: Tree, file_path: str) -> list[LintMessage]:
		"""Check that hash IDs follow the required format.

		Args:
			tree: Parsed Lark tree
			file_path: Source file path for messages

		Returns:
			List of lint messages
		"""
		messages = []

		for hash_node in tree.find_data("hash_id"):
			for child in hash_node.children:
				if isinstance(child, Token) and child.type == "_HASH_VALUE_TERMINAL":
					hash_value = child.value
					if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", hash_value):
						messages.append(
							LintMessage(
								file_path,
								getattr(child, "line", 1),
								getattr(child, "column", 0),
								"CS301",
								f"Hash ID '{hash_value}' does not follow naming convention",
							)
						)
		return messages

	def check_attribute_naming(self, tree: Tree, file_path: str) -> list[LintMessage]:
		"""Check attribute naming conventions.

		Args:
			tree: Parsed Lark tree
			file_path: Source file path for messages

		Returns:
			List of lint messages
		"""
		messages = []

		for attr in tree.find_data("attribute"):
			attr_key = None
			attr_line = getattr(attr, "line", 1) if hasattr(attr, "line") else 1
			attr_col = getattr(attr, "column", 0) if hasattr(attr, "column") else 0

			# Try to get better position information from metadata if available
			if hasattr(attr, "meta"):
				attr_line = getattr(attr.meta, "line", attr_line)
				attr_col = getattr(attr.meta, "column", attr_col)

			for child in attr.children:
				if isinstance(child, Token) and child.type == "ATTR_KEY":
					attr_key = child.value
					attr_line = getattr(child, "line", attr_line)
					attr_col = getattr(child, "column", attr_col)

			if attr_key and not re.match(r"^[a-z][a-zA-Z0-9_]*$", attr_key):
				messages.append(
					LintMessage(
						file_path,
						attr_line,
						attr_col,
						"CS401",
						f"Attribute key '{attr_key}' should be camelCase or snake_case starting with lowercase",
					)
				)
		return messages
