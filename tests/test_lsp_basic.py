"""Basic tests for CodeStruct Language Server."""

from lsprotocol import types as lsp

from src.codestruct.lsp.server import CodeStructLanguageServer


class TestCodeStructLanguageServer:
	"""Test the CodeStruct Language Server."""

	def test_server_creation(self):
		"""Test that the server can be created."""
		server = CodeStructLanguageServer()
		assert server is not None
		assert server.name == "codestruct-lsp"
		assert server.version == "0.1.0"

	def test_server_has_components(self):
		"""Test that the server has all required components."""
		server = CodeStructLanguageServer()

		assert server.parser is not None
		assert server.linter is not None
		assert server.formatter is not None
		assert server.transformer is not None

	def test_diagnostic_severity_mapping(self):
		"""Test diagnostic severity mapping."""
		server = CodeStructLanguageServer()

		# Test error codes
		assert server._get_diagnostic_severity("CS001") == lsp.DiagnosticSeverity.Error
		assert server._get_diagnostic_severity("CS101") == lsp.DiagnosticSeverity.Warning
		assert server._get_diagnostic_severity("CS201") == lsp.DiagnosticSeverity.Information
		assert server._get_diagnostic_severity("CS301") == lsp.DiagnosticSeverity.Warning
		assert server._get_diagnostic_severity("CS401") == lsp.DiagnosticSeverity.Warning

	def test_document_caching(self):
		"""Test document caching functionality."""
		server = CodeStructLanguageServer()

		# Test caching a valid document
		uri = "file:///test.cst"
		content = """module: TestModule
  doc: "A test module"
  class: TestClass
    doc: "A test class"
"""

		server._parse_and_cache_document(uri, content)
		cached = server.get_cached_document(uri)

		assert cached is not None
		assert cached["content"] == content
		assert cached["tree"] is not None
		assert cached["transformed"] is not None

	def test_document_caching_with_error(self):
		"""Test document caching with parse errors."""
		server = CodeStructLanguageServer()

		# Test caching an invalid document
		uri = "file:///test.cst"
		content = "invalid syntax: [[[["

		server._parse_and_cache_document(uri, content)
		cached = server.get_cached_document(uri)

		assert cached is not None
		assert cached["content"] == content
		assert cached["tree"] is None
		assert cached["transformed"] is None
		assert "parse_error" in cached
