"""Test the parser module."""

import pytest
from lark import Tree
from lark.exceptions import ParseError

import codestruct  # For __init__.py functions
from codestruct.parser import CodeStructParser

from .conftest import BASE_TEST_PATH, SIMPLE_CSTXT_PATH, VALID_CSTXT_FILES


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


# --- Tests for the codestruct/__init__.py module ---

# NOTE: The tests in this class target the functions `parse_string` and `parse_file`
# from the `codestruct/__init__.py` module.
# Currently, these __init__ functions pass an `as_dict` argument to
# `CodeStructParser.parse_string` and `CodeStructParser.parse_file`.
# However, the parser methods (in `src/codestruct/parser.py`) do not accept this argument.
# This will cause a TypeError when these __init__ functions are called.
#
# The tests below are written to verify the *intended behavior* where:
#  - `as_dict=False` returns a Lark Tree.
#  - `as_dict=True` returns a list of dictionaries (transformed output).
#
# If these tests fail with a TypeError related to an unexpected 'as_dict' argument,
# it indicates that `codestruct/__init__.py` needs to be modified to correctly
# handle the `as_dict` flag, for example, by conditionally applying
# `CodeStructToDict().transform()` to the parser's output.


def test_init_parse_string_tree_output():  # Use parser fixture to get simple content
	content = SIMPLE_CSTXT_PATH.read_text()
	result = codestruct.parse_string(content, as_dict=False)
	assert isinstance(result, Tree)


def test_init_parse_string_dict_output():
	content = SIMPLE_CSTXT_PATH.read_text()
	result = codestruct.parse_string(content, as_dict=True)
	assert isinstance(result, list)
	if result:
		assert isinstance(result[0], dict)


@pytest.mark.parametrize("file_path", VALID_CSTXT_FILES, ids=[p.name for p in VALID_CSTXT_FILES])
def test_init_parse_file_tree_output(file_path):
	result = codestruct.parse_file(file_path, as_dict=False)
	assert isinstance(result, Tree)


@pytest.mark.parametrize("file_path", VALID_CSTXT_FILES, ids=[p.name for p in VALID_CSTXT_FILES])
def test_init_parse_file_dict_output(file_path):
	result = codestruct.parse_file(file_path, as_dict=True)
	assert isinstance(result, list)
	if result and result[0] is not None:  # Ensure result[0] is not None from empty lines processing
		assert isinstance(result[0], dict)


def test_init_parse_string_invalid_syntax_raises_parse_error():
	invalid_content = "module: MyModule\n  class Oops No Colon"
	with pytest.raises(ParseError):
		codestruct.parse_string(invalid_content, as_dict=False)


def test_init_parse_file_not_found_raises_parse_error():
	non_existent_file = BASE_TEST_PATH / "non_existent_file_for_init.cstxt"
	with pytest.raises(ParseError):
		codestruct.parse_file(non_existent_file, as_dict=False)


def test_init_parse_file_invalid_content_raises_parse_error(tmp_path):
	invalid_content_file = tmp_path / "invalid_init.cstxt"
	invalid_content_file.write_text("module Bad Module Syntax :::\n  func missing_colon")
	with pytest.raises(ParseError):
		codestruct.parse_file(invalid_content_file, as_dict=False)
