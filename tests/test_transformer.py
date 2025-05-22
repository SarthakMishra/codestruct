"""Test the transformer module."""

import pytest
from lark import logger

from .conftest import SIMPLE_CSTXT_PATH, VALID_CSTXT_CONTENTS_AND_NAMES

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
