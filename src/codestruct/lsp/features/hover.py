"""Hover feature for CodeStruct LSP."""

import re

from lsprotocol import types as lsp
from pygls.server import LanguageServer

from codestruct.parser import CodeStructParser, ParseError
from codestruct.transformer import CodeStructTransformer


def get_hover(server: LanguageServer, params: lsp.HoverParams) -> lsp.Hover | None:
	"""Provide hover information."""
	uri = params.text_document.uri
	document = server.workspace.get_text_document(uri)
	position = params.position

	# Get the current line and word under cursor
	current_line = document.lines[position.line]
	word_range = _get_word_range(current_line, position.character)

	if not word_range:
		return None

	word = current_line[word_range[0] : word_range[1]]

	# Try to get context-specific hover information
	hover_content = _get_hover_content(word, current_line, document.source)

	if not hover_content:
		return None

	return lsp.Hover(
		contents=lsp.MarkupContent(
			kind=lsp.MarkupKind.Markdown,
			value=hover_content,
		),
		range=lsp.Range(
			start=lsp.Position(line=position.line, character=word_range[0]),
			end=lsp.Position(line=position.line, character=word_range[1]),
		),
	)


def _get_word_range(line: str, character: int) -> tuple[int, int] | None:
	"""Get the range of the word at the given character position."""
	if character >= len(line):
		return None

	# Find word boundaries
	start = character
	while start > 0 and (line[start - 1].isalnum() or line[start - 1] == "_"):
		start -= 1

	end = character
	while end < len(line) and (line[end].isalnum() or line[end] == "_"):
		end += 1

	if start == end:
		return None

	return (start, end)


def _get_hover_content(word: str, line: str, document_content: str) -> str | None:
	"""Get hover content for a word based on context."""
	# Check if it's an entity keyword
	if _is_entity_keyword(word):
		return _get_entity_keyword_hover(word)

	# Check if it's an attribute key
	if _is_attribute_key(word, line):
		return _get_attribute_key_hover(word)

	# Check if it's an attribute value
	if _is_attribute_value(word, line):
		return _get_attribute_value_hover(word, line)

	# Check if it's an entity name - try to find its definition
	entity_info = _find_entity_definition(word, document_content)
	if entity_info:
		return _format_entity_hover(entity_info)

	return None


def _is_entity_keyword(word: str) -> bool:
	"""Check if word is an entity keyword."""
	keywords = {
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
		"doc",
		"impl",
	}
	return word in keywords


def _is_attribute_key(word: str, line: str) -> bool:
	"""Check if word is an attribute key."""
	# Look for pattern: [word: or [other, word:
	pattern = rf"\[(?:[^,]*,\s*)*{re.escape(word)}\s*:"
	return bool(re.search(pattern, line))


def _is_attribute_value(word: str, line: str) -> bool:
	"""Check if word is an attribute value."""
	# Look for pattern: [key: word or [key: word,
	pattern = rf"\[[^:]*:\s*{re.escape(word)}(?:\s*[,\]]|$)"
	return bool(re.search(pattern, line))


def _get_entity_keyword_hover(keyword: str) -> str:
	"""Get hover content for entity keywords."""
	descriptions = {
		"module": "**Module** - A collection of related code, typically representing a file or package.",
		"class": "**Class** - A blueprint for creating objects with shared attributes and methods.",
		"func": "**Function** - A reusable block of code that performs a specific task.",
		"param": "**Parameter** - An input value to a function or method.",
		"returns": "**Returns** - The output value from a function or method.",
		"var": "**Variable** - A named storage location that can hold a value.",
		"const": "**Constant** - A named value that cannot be changed after initialization.",
		"type_alias": "**Type Alias** - An alternative name for an existing type.",
		"union": "**Union Type** - A type that can be one of several different types.",
		"optional": "**Optional Type** - A type that can either be a specific type or null/undefined.",
		"import": "**Import** - A reference to code from another module or file.",
		"dir": "**Directory** - A filesystem directory containing related files.",
		"file": "**File** - A single file in the filesystem.",
		"namespace": "**Namespace** - A logical grouping of related entities.",
		"lambda": "**Lambda** - An anonymous function expression.",
		"attr": "**Attribute** - A property or characteristic of an entity.",
		"doc": "**Documentation** - Descriptive text explaining the purpose and usage.",
		"impl": "**Implementation** - The actual code implementation of an entity.",
	}

	return descriptions.get(keyword, f"**{keyword}** - CodeStruct entity keyword.")


def _get_attribute_key_hover(key: str) -> str:
	"""Get hover content for attribute keys."""
	descriptions = {
		"type": "**type** - Specifies the data type or category of the entity.",
		"default": "**default** - The default value used when no value is provided.",
		"source": "**source** - The source file or module where this entity is defined.",
		"ref": "**ref** - A reference to another entity in the codebase.",
		"visibility": "**visibility** - The access level (public, private, protected, internal).",
		"static": "**static** - Indicates whether the entity belongs to the class rather than instances.",
		"abstract": "**abstract** - Indicates whether the entity is abstract and must be implemented.",
		"final": "**final** - Indicates whether the entity cannot be overridden or extended.",
		"async": "**async** - Indicates whether the entity operates asynchronously.",
	}

	return descriptions.get(key, f"**{key}** - CodeStruct attribute key.")


def _get_attribute_value_hover(value: str, line: str) -> str:
	"""Get hover content for attribute values."""
	# Try to determine the attribute key this value belongs to
	match = re.search(rf"\[(?:[^,]*,\s*)*([^:]+):\s*{re.escape(value)}", line)
	if not match:
		return f"**{value}** - Attribute value."

	key = match.group(1).strip()

	if key == "type":
		type_descriptions = {
			"STRING": "Text data type",
			"INTEGER": "Whole number data type",
			"FLOAT": "Decimal number data type",
			"BOOLEAN": "True/false data type",
			"ARRAY": "Collection of elements",
			"OBJECT": "Complex data structure",
			"CLASS": "Class definition type",
			"FUNCTION": "Function definition type",
			"MODULE": "Module definition type",
		}
		description = type_descriptions.get(value, "Data type")
		return f"**{value}** - {description}"

	if key == "visibility":
		visibility_descriptions = {
			"public": "Accessible from anywhere",
			"private": "Accessible only within the same entity",
			"protected": "Accessible within the same entity and subentities",
			"internal": "Accessible within the same module",
		}
		description = visibility_descriptions.get(value, "Visibility level")
		return f"**{value}** - {description}"

	return f"**{value}** - Value for attribute '{key}'"


def _find_entity_definition(name: str, content: str) -> dict | None:
	"""Find the definition of an entity by name."""
	try:
		parser = CodeStructParser.get_instance()
		transformer = CodeStructTransformer.get_instance()

		tree = parser.parse_string(content)
		transformed = transformer.start(tree.children)

		# Search for entity with matching name
		for entity in _flatten_entities(transformed):
			if isinstance(entity, dict) and entity.get("name") == name:
				return entity

	except ParseError:
		pass

	return None


def _flatten_entities(entities: list) -> list:
	"""Flatten nested entity structure for searching."""
	result = []
	for entity in entities:
		if isinstance(entity, dict):
			result.append(entity)
			if "children" in entity:
				result.extend(_flatten_entities(entity["children"]))
	return result


def _format_entity_hover(entity: dict) -> str:
	"""Format entity information for hover display."""
	entity_type = entity.get("type", "entity")
	entity_name = entity.get("name", "unknown")

	content = f"**{entity_type}** `{entity_name}`"

	# Add documentation if available
	if "children" in entity:
		for child in entity["children"]:
			if isinstance(child, dict) and "doc" in child:
				content += f"\n\n{child['doc']}"
				break

	# Add attributes if available
	if entity.get("attributes"):
		content += "\n\n**Attributes:**"
		for key, value in entity["attributes"].items():
			content += f"\n- `{key}`: {value}"

	return content
