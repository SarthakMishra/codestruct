"""Test the parser module."""

import pytest
from lark import Tree
from lark.exceptions import ParseError

from codestruct.parser import CodeStructParser

from .conftest import BASE_TEST_PATH, VALID_CSTXT_FILES


# --- Tests for the parser ---
def test_parser_instantiation(parser):
	assert isinstance(parser, CodeStructParser)


def test_parse_string_valid(parser, valid_cstxt_content, request):
	if "simple.cstxt" in request.node.name:
		pass

	tree = parser.parse_string(valid_cstxt_content)
	assert isinstance(tree, Tree)


def test_parse_string_empty(parser):
	tree = parser.parse_string("")
	assert isinstance(tree, Tree)


def test_parse_string_only_comments_and_newlines(parser):
	content = "# This is a comment\n\n# Another comment\n"
	tree = parser.parse_string(content)
	assert isinstance(tree, Tree)


def test_parse_string_invalid_syntax(parser):
	invalid_content = "module: MyModule\n  class Oops No Colon"
	with pytest.raises(ParseError) as excinfo:
		parser.parse_string(invalid_content)
	assert "Line 2:" in str(excinfo.value)
	assert "class Oops No Colon" in str(excinfo.value)
	assert "Unexpected token" in str(excinfo.value)


@pytest.mark.parametrize("file_path", VALID_CSTXT_FILES, ids=[p.name for p in VALID_CSTXT_FILES])
def test_parse_file_valid(parser, file_path):
	assert file_path.exists(), f"Test file {file_path} not found."
	tree = parser.parse_file(file_path)
	assert isinstance(tree, Tree)


def test_parse_file_not_found(parser):
	non_existent_file = BASE_TEST_PATH / "non_existent_file.cstxt"
	with pytest.raises(ParseError) as excinfo:
		parser.parse_file(non_existent_file)
	assert "File not found" in str(excinfo.value)
	assert str(non_existent_file) in str(excinfo.value)


def test_parse_file_invalid_content(parser, tmp_path):
	invalid_content_file = tmp_path / "invalid.cstxt"
	invalid_content_file.write_text("module Bad Module Syntax :::\n  func missing_colon")
	with pytest.raises(ParseError) as excinfo:
		parser.parse_file(invalid_content_file)
	assert "Error parsing CodeStruct" in str(excinfo.value)
