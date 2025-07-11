"""CodeStruct minifier for LLM context compression."""

import re
from pathlib import Path

from .parser import CodeStructParser, ParseError


class CodeStructMinifier:
	"""Minifies CodeStruct files for LLM context compression."""

	_instance = None

	def __init__(self, include_legend: bool = True) -> None:
		"""Initialize the minifier.

		Args:
			include_legend: Whether to include the legend/mapping for LLMs
		"""
		self.include_legend = include_legend
		self.parser = CodeStructParser()

		# Keyword shortening mappings
		self.keyword_map = {
			"dir": "d",
			"file": "f",
			"module": "m",
			"namespace": "ns",
			"class": "cl",
			"func": "fn",
			"lambda": "lm",
			"attr": "at",
			"param": "p",
			"returns": "r",
			"var": "v",
			"const": "c",
			"type_alias": "ta",
			"union": "u",
			"optional": "opt",
			"import": "i",
			"doc": "dc",
			"impl": "impl",  # Will be removed anyway
		}

		# Attribute key shortening mappings
		self.attr_key_map = {
			"type": "t",
			"default": "d",
			"source": "s",
			"ref": "rf",
			"visibility": "vis",
			"static": "st",
			"abstract": "abs",
			"final": "fin",
			"async": "as",
		}

		# Type abbreviations
		self.type_map = {
			"INTEGER": "INT",
			"STRING": "STR",
			"BOOLEAN": "BOOL",
			"FLOAT": "FLT",
			"external": "ext",
			"internal": "int",
			"public": "pub",
			"private": "priv",
			"protected": "prot",
			"true": "T",
			"false": "F",
		}

	@classmethod
	def get_instance(cls) -> "CodeStructMinifier":
		"""Get a singleton instance of the minifier to avoid unnecessary initialization.

		Returns:
			CodeStructMinifier: The singleton instance
		"""
		if cls._instance is None:
			cls._instance = cls()
		return cls._instance

	def minify_file(self, file_path: str) -> str:
		"""Minify a CodeStruct file.

		Args:
			file_path: Path to the file to minify

		Returns:
			Minified CodeStruct string

		Raises:
			FileNotFoundError: If the file doesn't exist
			ParseError: If the file cannot be parsed
		"""
		try:
			path = Path(file_path)
			content = path.read_text(encoding="utf-8")
			return self.minify_string(content)
		except FileNotFoundError:
			msg = f"File not found: {file_path}"
			raise FileNotFoundError(msg) from None
		except UnicodeDecodeError as e:
			msg = f"Unicode decode error: {e!s}"
			raise ParseError(msg) from e

	def minify_string(self, content: str) -> str:
		"""Minify CodeStruct content string.

		Args:
			content: The CodeStruct content to minify

		Returns:
			Minified CodeStruct string
		"""
		if not content.strip():
			return ""

		# For this simplified version, we'll work directly with the text
		# and apply basic minification without complex AST parsing
		result = self._minify_text_directly(content)

		if self.include_legend:
			legend = self._generate_legend()
			return f"{legend}\n{result}"
		return result

	def _minify_text_directly(self, content: str) -> str:
		"""Minify content by parsing text line by line and applying transformations."""
		lines = content.split("\n")
		entities = []
		current_entity = None
		children_stack = []
		indent_stack = [0]  # Track indentation levels
		skip_impl_block = False
		impl_indent_level = 0

		for _line_num, line in enumerate(lines):
			stripped = line.strip()

			# Skip empty lines and comments
			if not stripped or stripped.startswith("#"):
				continue

			# Calculate current indentation
			current_indent = len(line) - len(line.lstrip())

			# Handle impl block skipping
			if stripped.startswith("impl:"):
				skip_impl_block = True
				impl_indent_level = current_indent
				continue

			# Skip lines that are part of an impl block
			if skip_impl_block:
				if current_indent > impl_indent_level:
					continue
				skip_impl_block = False

			# Skip doc fields (they're optional in minified format)
			if stripped.startswith("doc:"):
				continue

			# Process indent changes
			if current_indent > indent_stack[-1]:
				# Increased indentation - new child level
				indent_stack.append(current_indent)
				if current_entity:
					children_stack.append(current_entity)
					current_entity = None
			elif current_indent < indent_stack[-1]:
				# Decreased indentation - back to parent level(s)
				while len(indent_stack) > 1 and current_indent < indent_stack[-1]:
					indent_stack.pop()
					if children_stack:
						parent_entity = children_stack.pop()
						if current_entity:
							if "children" not in parent_entity:
								parent_entity["children"] = []
							parent_entity["children"].append(current_entity)
						current_entity = parent_entity

			# Check if this is a standalone attribute line or attribute block
			if current_indent > 0 and children_stack and ":" in stripped:
				# Check if this is an entity keyword or a standalone attribute
				is_entity = any(
					stripped.startswith(kw + ":")
					for kw in [
						"module",
						"class",
						"func",
						"param",
						"returns",
						"var",
						"const",
						"type_alias",
						"union",
						"optional",
						"import",
						"dir",
						"file",
						"namespace",
						"lambda",
						"attr",
					]
				)

				# Check if this is a standalone attribute block like "[type: FLOAT, default: 3.14159]"
				is_attr_block = stripped.startswith("[") and stripped.endswith("]")

				if not is_entity or is_attr_block:
					# This looks like an attribute line or block for the parent entity
					parent_entity = children_stack[-1]

					if is_attr_block:
						# Handle attribute block: [key:value, key:value]
						attr_content = stripped[1:-1]  # Remove brackets
						attr_dict = self._parse_attributes(attr_content)
						parent_entity["attributes"].update(attr_dict)
					else:
						# Handle single attribute line: key: value
						key, value = stripped.split(":", 1)
						key = key.strip()
						value = value.strip()

						# Remove quotes from value
						if (value.startswith('"') and value.endswith('"')) or (
							value.startswith("'") and value.endswith("'")
						):
							value = value[1:-1]

						# Apply transformations
						short_key = self._shorten_attr_key(key)
						short_value = self.type_map.get(value, value)
						parent_entity["attributes"][short_key] = short_value
					continue

			# Parse the entity line
			entity_data = self._parse_entity_line(stripped)
			if entity_data:
				# If we have a current entity, we need to place it appropriately
				if current_entity:
					if current_indent == indent_stack[-1]:
						# Same level - add previous entity as sibling
						if children_stack:
							parent = children_stack[-1]
							if "children" not in parent:
								parent["children"] = []
							parent["children"].append(current_entity)
						else:
							# Top level entity
							entities.append(current_entity)
					elif current_indent > indent_stack[-1]:
						# This shouldn't happen as we handle indentation above
						pass

				current_entity = entity_data

		# Handle the last entity - this is crucial for grouped entities with attributes
		if current_entity:
			# Close any remaining parent levels
			while children_stack:
				parent_entity = children_stack.pop()
				if current_entity:
					if "children" not in parent_entity:
						parent_entity["children"] = []
					parent_entity["children"].append(current_entity)
				current_entity = parent_entity
			entities.append(current_entity)

		# Also handle case where we only have entities in the children_stack (no current_entity)
		while children_stack:
			parent_entity = children_stack.pop()
			entities.append(parent_entity)

		# Convert to minified format
		return ";".join(self._entity_to_minified(entity) for entity in entities)

	def _parse_entity_line(self, line: str) -> dict | None:
		"""Parse a single entity line into structured data."""
		# Remove hash IDs (anything after :::)
		line = re.sub(r"\s*:::\s*[A-Za-z0-9_]+", "", line)

		# Handle grouped entities (with &)
		if " & " in line:
			# Split on first colon to get keyword
			colon_idx = line.find(":")
			if colon_idx == -1:
				return None

			keyword = line[:colon_idx].strip()
			rest = line[colon_idx + 1 :].strip()

			# Find attributes by looking for balanced brackets
			attr_match = self._find_attribute_section(rest)
			attributes = {}
			if attr_match:
				attributes = self._parse_attributes(attr_match)
				# Remove the attribute section from rest
				attr_start = rest.find("[")
				rest = rest[:attr_start].strip()

			# Split grouped entities
			names = [name.strip() for name in rest.split("&")]
			grouped_names = "&".join(names)

			return {
				"keyword": self._shorten_keyword(keyword),
				"name": grouped_names,
				"attributes": attributes,
				"children": [],
			}
		# Regular entity
		# Parse: keyword: name [attributes]
		colon_idx = line.find(":")
		if colon_idx == -1:
			return None

		keyword = line[:colon_idx].strip()
		rest = line[colon_idx + 1 :].strip()

		# Find attributes by looking for balanced brackets
		attr_match = self._find_attribute_section(rest)
		attributes = {}
		if attr_match:
			attributes = self._parse_attributes(attr_match)
			# Remove the attribute section from rest
			attr_start = rest.find("[")
			rest = rest[:attr_start].strip()

		name = rest.strip()

		return {"keyword": self._shorten_keyword(keyword), "name": name, "attributes": attributes, "children": []}

	def _find_attribute_section(self, text: str) -> str | None:
		"""Find and extract the attribute section [key:value, key:value] handling nested brackets in quotes."""
		start_idx = text.find("[")
		if start_idx == -1:
			return None

		bracket_count = 0
		in_quotes = False
		quote_char = None

		for i, char in enumerate(text[start_idx:], start_idx):
			if char in ('"', "'") and (i == start_idx or text[i - 1] != "\\"):
				if not in_quotes:
					in_quotes = True
					quote_char = char
				elif char == quote_char:
					in_quotes = False
					quote_char = None
			elif not in_quotes:
				if char == "[":
					bracket_count += 1
				elif char == "]":
					bracket_count -= 1
					if bracket_count == 0:
						return text[start_idx + 1 : i]

		return None

	def _parse_attributes(self, attr_str: str) -> dict:
		"""Parse attribute string into key-value pairs."""
		attributes = {}

		# Split by comma but respect quoted values
		attr_parts = []
		current = ""
		in_quotes = False
		quote_char = None

		for char in attr_str:
			if char in ('"', "'") and (not current or current[-1] != "\\"):
				if not in_quotes:
					in_quotes = True
					quote_char = char
				elif char == quote_char:
					in_quotes = False
					quote_char = None
			elif char == "," and not in_quotes:
				attr_parts.append(current.strip())
				current = ""
				continue
			current += char

		if current.strip():
			attr_parts.append(current.strip())

		# Parse each key:value pair
		for part in attr_parts:
			if ":" in part:
				key, value = part.split(":", 1)
				key = key.strip()
				value = value.strip()

				# Remove quotes from value
				if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
					value = value[1:-1]

				# Apply transformations
				short_key = self._shorten_attr_key(key)
				short_value = self.type_map.get(value, value)
				attributes[short_key] = short_value

		return attributes

	def _entity_to_minified(self, entity: dict) -> str:
		"""Convert entity dict to minified string format."""
		result = f"{entity['keyword']}:{entity['name']}"

		# Add attributes
		if entity["attributes"]:
			attr_strs = [f"{k}:{v}" for k, v in entity["attributes"].items()]
			result += f"[{','.join(attr_strs)}]"

		# Add children - use comma for siblings at same level
		if entity["children"]:
			child_strs = [self._entity_to_minified(child) for child in entity["children"]]
			result += f"|{','.join(child_strs)}"

		return result

	def _shorten_keyword(self, keyword: str) -> str:
		"""Shorten a keyword using the mapping."""
		return self.keyword_map.get(keyword, keyword)

	def _shorten_attr_key(self, key: str) -> str:
		"""Shorten an attribute key using the mapping."""
		return self.attr_key_map.get(key, key)

	def _generate_legend(self) -> str:
		"""Generate the legend for interpreting minified CodeStruct."""
		keyword_mappings = [f"{short}={long}" for long, short in self.keyword_map.items()]
		attr_mappings = [f"{short}={long}" for long, short in self.attr_key_map.items()]
		type_mappings = [f"{short}={long}" for long, short in self.type_map.items()]

		legend = [
			"# CodeStruct Minified Format Legend",
			"# Format: Entity;Entity|Child,Child[Attribute,Attribute]",
			f"# Keywords: {','.join(keyword_mappings)}",
			f"# Attributes: {','.join(attr_mappings)}",
			f"# Types: {','.join(type_mappings)}",
			"# Delimiters: ;=entity separator, |=child separator, ,=attribute separator, &=entity grouping, []=attribute container",  # noqa: E501
			"# Notes: impl: blocks and hash IDs (:::) are omitted in minified format",
		]

		return "\n".join(legend)

	def save_minified_file(self, input_path: str, output_path: str | None = None) -> str:
		"""Minify a file and save the result.

		Args:
			input_path: Path to the input CodeStruct file
			output_path: Path for the output file (defaults to input_path with .min.cst extension)

		Returns:
			Path to the output file
		"""
		if output_path is None:
			input_file = Path(input_path)
			output_path = str(input_file.with_suffix(".min.cst"))

		minified = self.minify_file(input_path)
		Path(output_path).write_text(minified, encoding="utf-8")
		return output_path
