"""Test the parser module."""

from pathlib import Path

import pytest
from lark import Tree, logger
from lark.exceptions import ParseError

import codestruct  # For __init__.py functions
from codestruct.parser import CodeStructParser
from codestruct.transformer import CodeStructTransformer

# Define paths to test files
BASE_TEST_PATH = Path(__file__).parent
TEST_CASES_PATH = BASE_TEST_PATH / "test_cases"
SIMPLE_CSTXT_PATH = TEST_CASES_PATH / "simple.cst"
COMPLEX_CSTXT_PATH = TEST_CASES_PATH / "complex.cst"
EDGE_CASES_CSTXT_PATH = TEST_CASES_PATH / "edge_cases.cst"

VALID_CSTXT_FILES = [SIMPLE_CSTXT_PATH, COMPLEX_CSTXT_PATH, EDGE_CASES_CSTXT_PATH]
VALID_CSTXT_CONTENTS_AND_NAMES = [
	(SIMPLE_CSTXT_PATH.read_text(), "simple.cst"),
	(COMPLEX_CSTXT_PATH.read_text(), "complex.cst"),
	(EDGE_CASES_CSTXT_PATH.read_text(), "edge_cases.cst"),
]


@pytest.fixture(scope="module")
def parser():
	"""Return a CodeStructParser instance."""
	return CodeStructParser()


@pytest.fixture(scope="module")
def transformer():
	"""Return a CodeStructTransformer instance."""
	return CodeStructTransformer()


@pytest.fixture(params=[p.read_text() for p in VALID_CSTXT_FILES], ids=[p.name for p in VALID_CSTXT_FILES])
def valid_cstxt_content(request):
	"""Provide content from each valid .cstxt file."""
	return request.param


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


# --- Tests for the transformer ---


@pytest.mark.parametrize(
	("content", "name"), VALID_CSTXT_CONTENTS_AND_NAMES, ids=[name for _, name in VALID_CSTXT_CONTENTS_AND_NAMES]
)
def test_transform_valid_tree_produces_list(parser, transformer, content, name):
	tree = parser.parse_string(content)
	transformed_data = transformer.transform(tree)
	assert isinstance(transformed_data, list)
	# Check if content is not just whitespace or comments
	if content.strip() and not all(line.strip().startswith("#") or not line.strip() for line in content.splitlines()):
		assert len(transformed_data) > 0, f"Transformed data for {name} should not be empty for non-empty content"
		for item in transformed_data:
			assert isinstance(item, dict), f"Each item in transformed data for {name} should be a dict"
	elif not content.strip():  # Truly empty content
		assert len(transformed_data) == 0, f"Transformed data for empty content {name} should be empty"


def test_transform_simple_structure(parser, transformer):
	# Using simple.cstxt content directly for clarity in this specific test
	content = SIMPLE_CSTXT_PATH.read_text()
	tree = parser.parse_string(content)
	logger.debug(tree)
	result = transformer.transform(tree)
	logger.debug(result)

	assert result[0] == {"comment": "Simple CodeStruct Test File"}

	test_module = result[1]
	assert test_module["type"] == "module"
	assert test_module["name"] == "TestModule"
	assert "children" in test_module

	module_children = test_module["children"]
	assert module_children[0] == {"comment": "Module comment"}

	simple_class = module_children[1]
	assert simple_class["type"] == "class"
	assert simple_class["name"] == "SimpleClass"
	assert "attributes" not in simple_class  # No [...] attributes

	assert "children" in simple_class
	simple_class_children = simple_class["children"]

	assert simple_class_children[0] == {"doc": "A simple class for testing"}

	test_method_entity = simple_class_children[1]
	assert test_method_entity["type"] == "func"
	assert test_method_entity["name"] == "test_method"

	assert "children" in test_method_entity
	test_method_children = test_method_entity["children"]
	assert test_method_children[0] == {"doc": "A test method"}

	impl_field = test_method_children[1]
	assert "impl" in impl_field
	assert impl_field["impl"]["language"] == "python"
	assert "def test_method():" in impl_field["impl"]["code"]

	my_test_module = result[2]
	test_class = my_test_module["children"][1]
	assert test_class["type"] == "class"
	assert test_class["name"] == "TestClass"
	assert test_class.get("attributes", {}) == {"visibility": "public", "abstract": "true"}
	assert test_class.get("grouped") == ["BaseClass", "ITestable"]


def test_transform_attributes(parser, transformer):
	content = """class: MyClass [attr1:value1, attr2:"a string", attr3:123, attr4:true, attr5:false, attr6:null, attr7:1.23]"""
	tree = parser.parse_string(content)
	result = transformer.transform(tree)

	my_class = result[0]
	assert my_class.get("attributes", {}) == {
		"attr1": "value1",
		"attr2": "a string",
		"attr3": 123,
		"attr4": "true",
		"attr5": "false",
		"attr6": "null",
		"attr7": 1.23,
	}


def test_transform_hash_id(parser, transformer):
	content = "module: MyModule ::: myhash123"
	tree = parser.parse_string(content)
	result = transformer.transform(tree)
	assert result[0]["hash"] == "myhash123"


def test_transform_grouped_entities(parser, transformer):
	content = "class: MyClass &Group1 &Group2"
	tree = parser.parse_string(content)
	result = transformer.transform(tree)
	assert result[0]["grouped"] == ["Group1", "Group2"]


def test_transform_empty_impl_block(parser, transformer):
	content = "func: myFunc\n  impl:\n    ```\n    ```"
	tree = parser.parse_string(content)
	result = transformer.transform(tree)
	my_func = result[0]
	assert "children" in my_func
	impl_field = my_func["children"][0]  # impl is a child field
	assert "impl" in impl_field
	assert impl_field["impl"]["code"] == ""
	assert "language" not in impl_field["impl"]


def test_transform_impl_block_with_lang(parser, transformer):
	content = "func: myFunc\n  impl:\n    ```python\nprint('hello')\n    ```"
	tree = parser.parse_string(content)
	result = transformer.transform(tree)
	my_func = result[0]
	assert "children" in my_func
	impl_field = my_func["children"][0]  # impl is a child field
	assert "impl" in impl_field
	assert impl_field["impl"]["language"] == "python"
	assert impl_field["impl"]["code"] == "print('hello')"


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
