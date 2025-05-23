"""Formatting feature for CodeStruct LSP."""

from lsprotocol import types as lsp
from pygls.server import LanguageServer

from codestruct.formatter import CodeStructFormatter


def format_document(server: LanguageServer, params: lsp.DocumentFormattingParams) -> list[lsp.TextEdit]:
	"""Format the entire document."""
	uri = params.text_document.uri
	return _format_document_content(server, uri)


def format_range(server: LanguageServer, params: lsp.DocumentRangeFormattingParams) -> list[lsp.TextEdit]:
	"""Format a range of the document."""
	# For now, we'll format the entire document since CodeStruct formatting
	# is best done at the document level to maintain proper structure
	uri = params.text_document.uri
	return _format_document_content(server, uri)


def _format_document_content(server: LanguageServer, uri: str) -> list[lsp.TextEdit]:
	"""Common formatting logic."""
	document = server.workspace.get_text_document(uri)

	formatter = CodeStructFormatter.get_instance()
	formatted_content, _ = formatter.format_string(document.source)

	if formatted_content == document.source:
		return []

	# Return a single edit that replaces the entire document
	return [
		lsp.TextEdit(
			range=lsp.Range(
				start=lsp.Position(line=0, character=0),
				end=lsp.Position(line=len(document.lines), character=0),
			),
			new_text=formatted_content,
		)
	]
