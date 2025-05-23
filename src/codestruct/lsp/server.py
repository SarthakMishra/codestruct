"""CodeStruct Language Server Protocol implementation."""

import asyncio
import logging
from pathlib import Path
from typing import Any

from lsprotocol import types as lsp
from pygls.server import LanguageServer

from codestruct.formatter import CodeStructFormatter
from codestruct.linter import CodeStructLinter
from codestruct.parser import CodeStructParser, ParseError
from codestruct.transformer import CodeStructTransformer

from .features import (
	code_actions,
	completion,
	diagnostics,
	document_symbols,
	formatting,
	hover,
)

logger = logging.getLogger(__name__)


class CodeStructLanguageServer(LanguageServer):
	"""Language Server for CodeStruct files."""

	def __init__(self, name: str = "codestruct-lsp", version: str = "0.1.0") -> None:
		"""Initialize the CodeStruct Language Server."""
		super().__init__(name, version)

		# Initialize CodeStruct components
		self.parser = CodeStructParser.get_instance()
		self.linter = CodeStructLinter.get_instance()
		self.formatter = CodeStructFormatter.get_instance()
		self.transformer = CodeStructTransformer.get_instance()

		# Cache for parsed documents
		self._document_cache: dict[str, Any] = {}

		# Track background tasks
		self._background_tasks: set[asyncio.Task] = set()

	def setup_features(self) -> None:
		"""Setup all LSP features."""

		# Text document synchronization
		@self.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
		def on_text_document_did_open(params: lsp.DidOpenTextDocumentParams) -> None:
			self._on_text_document_did_open(params)

		@self.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
		def on_text_document_did_change(params: lsp.DidChangeTextDocumentParams) -> None:
			self._on_text_document_did_change(params)

		@self.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
		def on_text_document_did_save(params: lsp.DidSaveTextDocumentParams) -> None:
			self._on_text_document_did_save(params)

		@self.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)
		def on_text_document_did_close(params: lsp.DidCloseTextDocumentParams) -> None:
			self._on_text_document_did_close(params)

		# Diagnostics (linting)
		@self.feature(lsp.TEXT_DOCUMENT_DIAGNOSTIC)
		def get_diagnostics_handler(params: lsp.DocumentDiagnosticParams) -> lsp.RelatedFullDocumentDiagnosticReport:
			return diagnostics.get_diagnostics(self, params)

		# Formatting
		@self.feature(lsp.TEXT_DOCUMENT_FORMATTING)
		def format_document_handler(params: lsp.DocumentFormattingParams) -> list[lsp.TextEdit]:
			return formatting.format_document(self, params)

		@self.feature(lsp.TEXT_DOCUMENT_RANGE_FORMATTING)
		def format_range_handler(params: lsp.DocumentRangeFormattingParams) -> list[lsp.TextEdit]:
			return formatting.format_range(self, params)

		# Document symbols
		@self.feature(lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
		def get_document_symbols_handler(params: lsp.DocumentSymbolParams) -> list[lsp.DocumentSymbol]:
			return document_symbols.get_document_symbols(self, params)

		# Hover information
		@self.feature(lsp.TEXT_DOCUMENT_HOVER)
		def get_hover_handler(params: lsp.HoverParams) -> lsp.Hover | None:
			return hover.get_hover(self, params)

		# Code completion
		@self.feature(
			lsp.TEXT_DOCUMENT_COMPLETION,
			lsp.CompletionOptions(
				trigger_characters=[":", "[", ",", " "],
				resolve_provider=False,
			),
		)
		def get_completion_handler(params: lsp.CompletionParams) -> lsp.CompletionList:
			return completion.get_completion(self, params)

		# Code actions
		@self.feature(lsp.TEXT_DOCUMENT_CODE_ACTION)
		def get_code_actions_handler(params: lsp.CodeActionParams) -> list[lsp.CodeAction]:
			return code_actions.get_code_actions(self, params)

	def _on_text_document_did_open(self, params: lsp.DidOpenTextDocumentParams) -> None:
		"""Handle text document open event."""
		uri = params.text_document.uri
		content = params.text_document.text

		logger.info(f"Document opened: {uri}")
		self._parse_and_cache_document(uri, content)
		self._publish_diagnostics(uri, content)

	def _on_text_document_did_change(self, params: lsp.DidChangeTextDocumentParams) -> None:
		"""Handle text document change event."""
		# Get the document from the workspace
		document = self.workspace.get_text_document(params.text_document.uri)
		uri = document.uri
		content = document.source

		logger.debug(f"Document changed: {uri}")
		self._parse_and_cache_document(uri, content)

		# Debounce diagnostics updates
		task = asyncio.create_task(self._debounced_diagnostics(uri, content))
		self._background_tasks.add(task)
		task.add_done_callback(self._background_tasks.discard)

	def _on_text_document_did_save(self, params: lsp.DidSaveTextDocumentParams) -> None:
		"""Handle text document save event."""
		document = self.workspace.get_text_document(params.text_document.uri)
		uri = document.uri
		content = document.source

		logger.info(f"Document saved: {uri}")
		self._parse_and_cache_document(uri, content)
		self._publish_diagnostics(uri, content)

	def _on_text_document_did_close(self, params: lsp.DidCloseTextDocumentParams) -> None:
		"""Handle text document close event."""
		uri = params.text_document.uri
		logger.info(f"Document closed: {uri}")

		# Clear cache and diagnostics
		self._document_cache.pop(uri, None)
		self.publish_diagnostics(uri, [])

	def _parse_and_cache_document(self, uri: str, content: str) -> None:
		"""Parse document and cache the result."""
		try:
			tree = self.parser.parse_string(content)
			transformed = self.transformer.start(tree.children)
			self._document_cache[uri] = {
				"tree": tree,
				"transformed": transformed,
				"content": content,
			}
		except ParseError as e:
			logger.warning(f"Parse error in {uri}: {e}")
			# Cache the error so we can show diagnostics
			self._document_cache[uri] = {
				"tree": None,
				"transformed": None,
				"content": content,
				"parse_error": e,
			}

	def _publish_diagnostics(self, uri: str, content: str) -> None:
		"""Publish diagnostics for a document."""
		diagnostics_list = []

		# Get lint messages
		lint_messages = self.linter.lint_file(Path(uri).name) if Path(uri).exists() else []
		if not lint_messages:
			# Try linting the content directly
			try:
				tree = self.parser.parse_string(content)
				lint_messages = self.linter.lint_tree(tree, uri)
			except ParseError:
				# Parser errors will be handled separately
				pass

		# Convert lint messages to LSP diagnostics
		for msg in lint_messages:
			diagnostic = lsp.Diagnostic(
				range=lsp.Range(
					start=lsp.Position(line=max(0, msg.line - 1), character=max(0, msg.col)),
					end=lsp.Position(line=max(0, msg.line - 1), character=max(0, msg.col + 10)),
				),
				message=msg.message,
				severity=self._get_diagnostic_severity(msg.code),
				code=msg.code,
				source="codestruct",
			)
			diagnostics_list.append(diagnostic)

		# Check for parse errors
		cached_doc = self._document_cache.get(uri)
		if cached_doc and "parse_error" in cached_doc:
			parse_error = cached_doc["parse_error"]
			diagnostic = lsp.Diagnostic(
				range=lsp.Range(
					start=lsp.Position(line=0, character=0),
					end=lsp.Position(line=0, character=100),
				),
				message=str(parse_error),
				severity=lsp.DiagnosticSeverity.Error,
				code="parse_error",
				source="codestruct",
			)
			diagnostics_list.append(diagnostic)

		self.publish_diagnostics(uri, diagnostics_list)

	async def _debounced_diagnostics(self, uri: str, content: str) -> None:
		"""Debounced diagnostics updates for better performance."""
		await asyncio.sleep(0.5)  # 500ms debounce
		self._publish_diagnostics(uri, content)

	def _get_diagnostic_severity(self, code: str) -> lsp.DiagnosticSeverity:
		"""Map error codes to LSP diagnostic severity."""
		if code.startswith("CS00"):  # File/parse errors
			return lsp.DiagnosticSeverity.Error
		if code.startswith("CS1"):  # Naming issues
			return lsp.DiagnosticSeverity.Warning
		if code.startswith("CS2"):  # Documentation issues
			return lsp.DiagnosticSeverity.Information
		if code.startswith(("CS3", "CS4")):  # Hash format issues
			return lsp.DiagnosticSeverity.Warning
		return lsp.DiagnosticSeverity.Information

	def get_cached_document(self, uri: str) -> dict[str, Any] | None:
		"""Get cached document data."""
		return self._document_cache.get(uri)


def create_server() -> CodeStructLanguageServer:
	"""Create and configure the language server."""
	server = CodeStructLanguageServer()
	server.setup_features()
	return server


def main() -> None:
	"""Main entry point for the language server."""
	logging.basicConfig(level=logging.INFO)
	server = create_server()
	server.start_io()
