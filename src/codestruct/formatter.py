"""CodeStruct formatter for auto-fixing linting issues and enforcing style."""

import re
from pathlib import Path
from re import Match

from lark import Token, Tree

from .linter import CodeStructLinter, LintMessage
from .parser import CodeStructParser, ParseError

# Constants
EXPECTED_COLON_PARTS = 2


class CodeStructFormatter:
	"""Formatter for CodeStruct files that can auto-fix some linting issues and enforce style."""

	def __init__(self, indent_size: int = 2, auto_add_docs: bool = True) -> None:
		"""Initialize the formatter.

		Args:
			indent_size: Number of spaces for indentation (2 or 4)
			auto_add_docs: Whether to automatically add placeholder documentation
		"""
		if indent_size not in (2, 4):
			msg = "indent_size must be 2 or 4"
			raise ValueError(msg)

		self.indent_size = indent_size
		self.auto_add_docs = auto_add_docs
		self.parser = CodeStructParser()
		self.linter = CodeStructLinter()

	def format_file(self, file_path: str, auto_fix: bool = True) -> tuple[str, list[LintMessage]]:
		"""Format a CodeStruct file and optionally auto-fix issues.

		Args:
			file_path: Path to the file to format
			auto_fix: Whether to apply auto-fixes

		Returns:
			Tuple of (formatted_content, remaining_lint_messages)
		"""
		try:
			path = Path(file_path)
			content = path.read_text(encoding="utf-8")
			return self.format_string(content, auto_fix)
		except FileNotFoundError:
			return "", [LintMessage(file_path, 1, 0, "CS002", f"File not found: {file_path}")]
		except PermissionError:
			return "", [LintMessage(file_path, 1, 0, "CS003", f"Permission denied: {file_path}")]
		except UnicodeDecodeError as e:
			return "", [LintMessage(file_path, 1, 0, "CS004", f"Unicode decode error: {e!s}")]

	def format_string(self, content: str, auto_fix: bool = True) -> tuple[str, list[LintMessage]]:
		"""Format CodeStruct content string and optionally auto-fix issues.

		Args:
			content: The CodeStruct content to format
			auto_fix: Whether to apply auto-fixes

		Returns:
			Tuple of (formatted_content, remaining_lint_messages)
		"""
		if not content.strip():
			return content, []

		formatted = content

		# Apply basic formatting fixes
		formatted = self._normalize_line_endings(formatted)
		formatted = self._remove_trailing_whitespace(formatted)
		formatted = self._normalize_indentation(formatted)
		formatted = self._normalize_spacing(formatted)

		if auto_fix:
			# Apply auto-fixes that might change structure
			formatted = self._fix_attribute_naming(formatted)

			if self.auto_add_docs:
				formatted = self._add_missing_docs(formatted)

		# Get remaining lint messages after formatting
		try:
			tree = self.parser.parse_string(formatted)
			messages = self.linter.lint_tree(tree, "<formatted>")
		except ParseError as e:
			# If formatting broke the syntax, return original with parse error
			messages = [LintMessage("<formatted>", 1, 0, "CS001", f"Parse error after formatting: {e!s}")]
			formatted = content

		return formatted, messages

	def _normalize_line_endings(self, content: str) -> str:
		"""Normalize line endings to Unix style."""
		# Replace Windows and Mac line endings with Unix
		result = content.replace("\r\n", "\n").replace("\r", "\n")
		# If original ended with a lone CR (Mac-style), strip the added LF
		if content.endswith("\r"):
			return result.rstrip("\n")
		# Otherwise preserve LF endings (including those from original LF or CRLF)
		return result

	def _remove_trailing_whitespace(self, content: str) -> str:
		"""Remove trailing whitespace from lines."""
		return re.sub(r"[ \t]+$", "", content, flags=re.MULTILINE)

	def _normalize_indentation(self, content: str) -> str:
		"""Convert tabs to spaces and normalize indentation levels."""
		lines = content.split("\n")
		normalized_lines = []
		indent_stack = [0]  # Stack to track indentation levels
		current_level = 0

		for line in lines:
			if not line.strip():
				# Keep empty lines as-is
				normalized_lines.append("")
				continue

			# Convert tabs to spaces
			expanded_line = line.expandtabs(self.indent_size)

			# Calculate current indentation level
			stripped = expanded_line.lstrip()
			if not stripped:
				normalized_lines.append("")
				continue

			current_indent = len(expanded_line) - len(stripped)

			# Determine semantic indentation level based on previous lines
			if current_indent > indent_stack[-1]:
				# Increased indentation - go one level deeper
				current_level += 1
				indent_stack.append(current_indent)
			elif current_indent < indent_stack[-1]:
				# Decreased indentation - find the appropriate level
				while len(indent_stack) > 1 and current_indent < indent_stack[-1]:
					indent_stack.pop()
					current_level -= 1
				# If we don't match exactly, treat as same level as closest parent
				if current_indent != indent_stack[-1] and len(indent_stack) > 1:
					indent_stack[-1] = current_indent
			# If current_indent == indent_stack[-1], stay at same level

			new_indent = " " * (current_level * self.indent_size)

			normalized_lines.append(new_indent + stripped)

		return "\n".join(normalized_lines)

	def _normalize_spacing(self, content: str) -> str:
		"""Normalize spacing around operators and brackets."""
		lines = content.split("\n")
		normalized_lines = []

		for line in lines:
			if not line.strip() or line.strip().startswith("#"):
				# Skip empty lines and comments
				normalized_lines.append(line)
				continue

			# Get indentation
			stripped = line.lstrip()
			indent = line[: len(line) - len(stripped)]

			# Normalize spacing around colons (but not in strings)
			# Entity declarations: "keyword: name" -> ensure single space after colon
			if ":" in stripped and not stripped.startswith("doc:"):
				# Handle the main entity colon
				parts = stripped.split(":", 1)
				if len(parts) == EXPECTED_COLON_PARTS:
					keyword = parts[0].strip()
					rest = parts[1].strip()
					stripped = f"{keyword}: {rest}"

			# Add space before attribute brackets if missing
			stripped = re.sub(r"(\S)\[", r"\1 [", stripped)

			# Normalize spacing in attributes [key:value, key:value]
			stripped = self._normalize_attribute_spacing(stripped)

			normalized_lines.append(indent + stripped)

		return "\n".join(normalized_lines)

	def _normalize_attribute_spacing(self, line: str) -> str:
		"""Normalize spacing within attribute brackets."""

		# Find attribute sections [...]
		def replace_attributes(match: Match[str]) -> str:
			attr_content = match.group(1)
			# Split by comma, normalize each attribute
			attributes = []
			for attr_item in attr_content.split(","):
				attr_cleaned = attr_item.strip()
				if ":" in attr_cleaned:
					key, value = attr_cleaned.split(":", 1)
					key = key.strip()
					value = value.strip()
					attributes.append(f"{key}:{value}")
				else:
					attributes.append(attr_cleaned)
			return f"[{', '.join(attributes)}]"

		return re.sub(r"\[([^\]]+)\]", replace_attributes, line)

	def _fix_attribute_naming(self, content: str) -> str:
		"""Fix attribute naming conventions to follow camelCase/snake_case."""
		lines = content.split("\n")
		fixed_lines = []

		for line in lines:
			if not line.strip() or line.strip().startswith("#"):
				fixed_lines.append(line)
				continue

			# Fix attribute names in brackets
			def fix_attr_name(match: Match[str]) -> str:
				attr_content = match.group(1)
				attributes = []
				for attr_item in attr_content.split(","):
					attr_cleaned = attr_item.strip()
					if ":" in attr_cleaned:
						key, value = attr_cleaned.split(":", 1)
						key = key.strip()
						value = value.strip()
						# Convert PascalCase or UPPER_CASE to camelCase
						fixed_key = self._convert_to_camel_case(key)
						attributes.append(f"{fixed_key}:{value}")
					else:
						attributes.append(attr_cleaned)
				return f"[{', '.join(attributes)}]"

			fixed_line = re.sub(r"\[([^\]]+)\]", fix_attr_name, line)
			fixed_lines.append(fixed_line)

		return "\n".join(fixed_lines)

	def _convert_to_camel_case(self, name: str) -> str:
		"""Convert PascalCase or UPPER_CASE to camelCase."""
		# If already camelCase or snake_case starting with lowercase, keep it
		if re.match(r"^[a-z][a-zA-Z0-9_]*$", name):
			return name

		# Convert PascalCase to camelCase
		if re.match(r"^[A-Z][a-zA-Z0-9]*$", name):
			return name[0].lower() + name[1:]

		# Convert UPPER_CASE to camelCase
		if re.match(r"^[A-Z][A-Z0-9_]*$", name):
			parts = name.lower().split("_")
			if len(parts) == 1:
				return parts[0]
			return parts[0] + "".join(word.capitalize() for word in parts[1:])

		# If it starts with a number or has other issues, keep as-is
		return name

	def _add_missing_docs(self, content: str) -> str:
		"""Add placeholder documentation for entities missing docs."""
		try:
			tree = self.parser.parse_string(content)
		except ParseError:
			# If we can't parse, don't try to add docs
			return content

		lines = content.split("\n")
		lines_to_add = {}  # line_number -> doc_line_to_insert

		# Find entities that need documentation (using same logic as linter)
		for entity in tree.find_data("entity"):
			entity_type: str | None = None
			entity_name: str | None = None
			entity_line_num = None

			# Get entity type and name
			for child in entity.children:
				if isinstance(child, Tree) and child.data == "entity_line":
					# Get position from the entity_line for insertion
					if hasattr(child, "meta"):
						entity_line_num = getattr(child.meta, "line", None)
						if entity_line_num is not None:
							entity_line_num -= 1  # Convert to 0-based

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

			# Add documentation if needed
			if not has_doc and entity_name and entity_line_num is not None and 0 <= entity_line_num < len(lines):
				entity_line = lines[entity_line_num]
				indent = len(entity_line) - len(entity_line.lstrip())
				child_indent = " " * (indent + self.indent_size)

				# Create appropriate placeholder documentation
				doc_text = self._generate_placeholder_doc(entity_type, entity_name)
				doc_line = f"{child_indent}doc: {doc_text}"

				# Insert after the entity line
				lines_to_add[entity_line_num + 1] = doc_line

		# Insert documentation lines in reverse order to maintain line numbers
		for line_num in sorted(lines_to_add.keys(), reverse=True):
			lines.insert(line_num, lines_to_add[line_num])

		return "\n".join(lines)

	def _generate_placeholder_doc(self, entity_type: str, entity_name: str) -> str:
		"""Generate appropriate placeholder documentation."""
		name = entity_name.strip()

		if entity_type == "module":
			return f"{name} module"
		if entity_type == "class":
			return f"{name} class"
		if entity_type == "func":
			return f"{name} function"
		return f"{name} {entity_type}"

	def save_formatted_file(self, file_path: str, auto_fix: bool = True) -> list[LintMessage]:
		"""Format and save a file in place.

		Args:
			file_path: Path to the file to format
			auto_fix: Whether to apply auto-fixes

		Returns:
			List of remaining lint messages after formatting
		"""
		formatted_content, messages = self.format_file(file_path, auto_fix)

		if not any(msg.code == "CS002" for msg in messages):  # File not found
			try:
				Path(file_path).write_text(formatted_content, encoding="utf-8")
			except (PermissionError, OSError) as e:
				messages.append(LintMessage(file_path, 1, 0, "CS003", f"Failed to write file: {e!s}"))

		return messages
