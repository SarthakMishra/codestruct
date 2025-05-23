"""Completion feature for CodeStruct LSP."""

import re

from lsprotocol import types as lsp
from pygls.server import LanguageServer


def get_completion(server: LanguageServer, params: lsp.CompletionParams) -> lsp.CompletionList:
	"""Provide code completion suggestions."""
	uri = params.text_document.uri
	document = server.workspace.get_text_document(uri)
	position = params.position

	# Get the current line and context
	current_line = document.lines[position.line]
	line_prefix = current_line[: position.character]

	completions = []

	# Determine context and provide appropriate completions
	if _is_entity_keyword_context(line_prefix):
		completions.extend(_get_entity_keyword_completions())
	elif _is_attribute_context(line_prefix):
		completions.extend(_get_attribute_completions())
	elif _is_attribute_value_context(line_prefix):
		completions.extend(_get_attribute_value_completions(line_prefix))
	else:
		# Default completions
		completions.extend(_get_general_completions())

	return lsp.CompletionList(is_incomplete=False, items=completions)


def _is_entity_keyword_context(line_prefix: str) -> bool:
	"""Check if we're in an entity keyword context."""
	# Beginning of line or after indentation
	return re.match(r"^\s*[a-z]*$", line_prefix) is not None


def _is_attribute_context(line_prefix: str) -> bool:
	"""Check if we're in an attribute key context."""
	# Inside brackets, looking for attribute key
	return "[" in line_prefix and not re.search(r"\[[^:]*:", line_prefix)


def _is_attribute_value_context(line_prefix: str) -> bool:
	"""Check if we're in an attribute value context."""
	# After colon in attributes
	return re.search(r"\[[^:]*:[^,\]]*$", line_prefix) is not None


def _get_entity_keyword_completions() -> list[lsp.CompletionItem]:
	"""Get entity keyword completions."""
	keywords = [
		("module", "Module definition"),
		("class", "Class definition"),
		("func", "Function definition"),
		("param", "Parameter definition"),
		("returns", "Return value definition"),
		("var", "Variable definition"),
		("const", "Constant definition"),
		("type_alias", "Type alias definition"),
		("union", "Union type definition"),
		("optional", "Optional type definition"),
		("import", "Import statement"),
		("dir", "Directory definition"),
		("file", "File definition"),
		("namespace", "Namespace definition"),
		("lambda", "Lambda function definition"),
		("attr", "Attribute definition"),
		("doc", "Documentation"),
		("impl", "Implementation block"),
	]

	return [
		lsp.CompletionItem(
			label=keyword,
			kind=lsp.CompletionItemKind.Keyword,
			detail=description,
			insert_text=f"{keyword}: ",
		)
		for keyword, description in keywords
	]


def _get_attribute_completions() -> list[lsp.CompletionItem]:
	"""Get attribute key completions."""
	attributes = [
		("type", "Type specification"),
		("default", "Default value"),
		("source", "Source file or module"),
		("ref", "Reference to another entity"),
		("visibility", "Visibility modifier"),
		("static", "Static modifier"),
		("abstract", "Abstract modifier"),
		("final", "Final modifier"),
		("async", "Async modifier"),
	]

	return [
		lsp.CompletionItem(
			label=attr,
			kind=lsp.CompletionItemKind.Property,
			detail=description,
			insert_text=f"{attr}:",
		)
		for attr, description in attributes
	]


def _get_attribute_value_completions(line_prefix: str) -> list[lsp.CompletionItem]:
	"""Get attribute value completions based on attribute key."""
	# Extract attribute key
	match = re.search(r"\[(?:[^,]*,\s*)*([^:]+):", line_prefix)
	if not match:
		return []

	attr_key = match.group(1).strip()

	if attr_key == "type":
		return _get_type_completions()
	if attr_key == "visibility":
		return _get_visibility_completions()
	if attr_key in ["static", "abstract", "final", "async"]:
		return _get_boolean_completions()
	return []


def _get_type_completions() -> list[lsp.CompletionItem]:
	"""Get type value completions."""
	types = [
		"STRING",
		"INTEGER",
		"FLOAT",
		"BOOLEAN",
		"ARRAY",
		"OBJECT",
		"CLASS",
		"FUNCTION",
		"MODULE",
		"NAMESPACE",
		"INTERFACE",
		"ENUM",
		"UNION",
		"OPTIONAL",
		"ANY",
	]

	return [
		lsp.CompletionItem(
			label=type_name,
			kind=lsp.CompletionItemKind.Enum,
			detail=f"{type_name} type",
		)
		for type_name in types
	]


def _get_visibility_completions() -> list[lsp.CompletionItem]:
	"""Get visibility value completions."""
	visibilities = ["public", "private", "protected", "internal"]

	return [
		lsp.CompletionItem(
			label=vis,
			kind=lsp.CompletionItemKind.Enum,
			detail=f"{vis} visibility",
		)
		for vis in visibilities
	]


def _get_boolean_completions() -> list[lsp.CompletionItem]:
	"""Get boolean value completions."""
	return [
		lsp.CompletionItem(
			label="true",
			kind=lsp.CompletionItemKind.Enum,
			detail="Boolean true value",
		),
		lsp.CompletionItem(
			label="false",
			kind=lsp.CompletionItemKind.Enum,
			detail="Boolean false value",
		),
	]


def _get_general_completions() -> list[lsp.CompletionItem]:
	"""Get general completions for any context."""
	return [
		lsp.CompletionItem(
			label="# Comment",
			kind=lsp.CompletionItemKind.Text,
			detail="Add a comment",
			insert_text="# ",
		),
	]
