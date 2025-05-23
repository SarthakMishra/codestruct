"""Diagnostics feature for CodeStruct LSP."""

from lsprotocol import types as lsp
from pygls.server import LanguageServer

from codestruct.linter import CodeStructLinter
from codestruct.parser import CodeStructParser, ParseError


def get_diagnostics(
	server: LanguageServer, params: lsp.DocumentDiagnosticParams
) -> lsp.RelatedFullDocumentDiagnosticReport:
	"""Get diagnostics for a document."""
	uri = params.text_document.uri
	document = server.workspace.get_text_document(uri)

	diagnostics = []

	try:
		# Parse the document
		parser = CodeStructParser.get_instance()
		tree = parser.parse_string(document.source)

		# Get lint messages
		linter = CodeStructLinter.get_instance()
		lint_messages = linter.lint_tree(tree, uri)

		# Convert to LSP diagnostics
		for msg in lint_messages:
			diagnostic = lsp.Diagnostic(
				range=lsp.Range(
					start=lsp.Position(line=max(0, msg.line - 1), character=max(0, msg.col)),
					end=lsp.Position(line=max(0, msg.line - 1), character=max(0, msg.col + 10)),
				),
				message=msg.message,
				severity=_get_diagnostic_severity(msg.code),
				code=msg.code,
				source="codestruct",
			)
			diagnostics.append(diagnostic)

	except ParseError as e:
		# Add parse error as diagnostic
		diagnostic = lsp.Diagnostic(
			range=lsp.Range(
				start=lsp.Position(line=0, character=0),
				end=lsp.Position(line=0, character=100),
			),
			message=str(e),
			severity=lsp.DiagnosticSeverity.Error,
			code="parse_error",
			source="codestruct",
		)
		diagnostics.append(diagnostic)

	return lsp.RelatedFullDocumentDiagnosticReport(kind="full", items=diagnostics)


def _get_diagnostic_severity(code: str) -> lsp.DiagnosticSeverity:
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
