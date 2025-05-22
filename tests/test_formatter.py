"""Test the formatter module."""

import tempfile
from pathlib import Path

import pytest

from codestruct.formatter import CodeStructFormatter


@pytest.fixture
def formatter():
	"""Return a CodeStructFormatter instance."""
	return CodeStructFormatter()


@pytest.fixture
def formatter_4spaces():
	"""Return a CodeStructFormatter instance with 4-space indentation."""
	return CodeStructFormatter(indent_size=4)


class TestCodeStructFormatter:
	"""Test the CodeStructFormatter class."""

	def test_formatter_initialization(self, formatter):
		"""Test formatter is properly initialized."""
		assert formatter.indent_size == 2
		assert formatter.auto_add_docs is True

	def test_formatter_invalid_indent_size(self):
		"""Test formatter raises error for invalid indent size."""
		with pytest.raises(ValueError, match="indent_size must be 2 or 4"):
			CodeStructFormatter(indent_size=3)

	def test_normalize_line_endings(self, formatter):
		"""Test line ending normalization."""
		content = "module: Test\r\n  class: MyClass\r"
		formatted, _ = formatter.format_string(content, auto_fix=False)
		assert "\r" not in formatted
		assert formatted == "module: Test\n  class: MyClass"

	def test_remove_trailing_whitespace(self, formatter):
		"""Test trailing whitespace removal."""
		content = "module: Test   \n  class: MyClass\t\t\n"
		formatted, _ = formatter.format_string(content, auto_fix=False)
		assert formatted == "module: Test\n  class: MyClass\n"

	def test_normalize_indentation_tabs_to_spaces(self, formatter):
		"""Test tab to space conversion."""
		content = "module: Test\n\tclass: MyClass\n\t\tfunc: myMethod"
		formatted, _ = formatter.format_string(content, auto_fix=False)
		expected = "module: Test\n  class: MyClass\n    func: myMethod"
		assert formatted == expected

	def test_normalize_indentation_irregular_spacing(self, formatter):
		"""Test irregular indentation normalization."""
		content = "module: Test\n   class: MyClass\n     func: myMethod"
		formatted, _ = formatter.format_string(content, auto_fix=False)
		expected = "module: Test\n  class: MyClass\n    func: myMethod"
		assert formatted == expected

	def test_normalize_indentation_4_spaces(self, formatter_4spaces):
		"""Test 4-space indentation."""
		content = "module: Test\n  class: MyClass\n    func: myMethod"
		formatted, _ = formatter_4spaces.format_string(content, auto_fix=False)
		expected = "module: Test\n    class: MyClass\n        func: myMethod"
		assert formatted == expected

	def test_normalize_spacing_around_colons(self, formatter):
		"""Test spacing normalization around colons."""
		content = "module:Test\n  class:   MyClass\n    func:myMethod"
		formatted, _ = formatter.format_string(content, auto_fix=False)
		expected = "module: Test\n  class: MyClass\n    func: myMethod"
		assert formatted == expected

	def test_normalize_attribute_spacing(self, formatter):
		"""Test attribute spacing normalization."""
		content = "func: test[type:STRING,default:  'value'  ,  static:true]"
		formatted, _ = formatter.format_string(content, auto_fix=False)
		expected = "func: test [type:STRING, default:'value', static:true]"
		assert formatted == expected

	def test_fix_attribute_naming_pascal_case(self, formatter):
		"""Test fixing PascalCase attribute names."""
		content = "class: MyClass [Visibility:public, IsAbstract:true]"
		formatted, _ = formatter.format_string(content, auto_fix=True)
		expected = "class: MyClass [visibility:public, isAbstract:true]"
		assert formatted == expected

	def test_fix_attribute_naming_upper_case(self, formatter):
		"""Test fixing UPPER_CASE attribute names."""
		content = "var: count [MAX_VALUE:100, DEFAULT_NAME:'test']"
		formatted, _ = formatter.format_string(content, auto_fix=True)
		expected = "var: count [maxValue:100, defaultName:'test']"
		assert formatted == expected

	def test_fix_attribute_naming_preserve_valid(self, formatter):
		"""Test that valid attribute names are preserved."""
		content = "func: test [type:STRING, isStatic:true, max_count:10]"
		formatted, _ = formatter.format_string(content, auto_fix=True)
		expected = "func: test [type:STRING, isStatic:true, max_count:10]"
		assert formatted == expected

	def test_add_missing_docs_disabled(self):
		"""Test that missing docs are not added when disabled."""
		formatter = CodeStructFormatter(auto_add_docs=False)
		content = """
module: TestModule
  class: TestClass
    func: testFunction
"""
		formatted, _ = formatter.format_string(content, auto_fix=True)
		assert "doc:" not in formatted

	def test_add_missing_docs_enabled(self, formatter):
		"""Test adding missing documentation."""
		content = """
module: TestModule
  class: TestClass
    func: testFunction
"""
		formatted, _ = formatter.format_string(content, auto_fix=True)

		# Should add docs for module, class, and function
		assert "doc: TestModule module" in formatted
		assert "doc: TestClass class" in formatted
		assert "doc: testFunction function" in formatted

	def test_add_missing_docs_preserve_existing(self, formatter):
		"""Test that existing docs are preserved."""
		content = """
module: TestModule
  doc: Custom module documentation
  class: TestClass
    func: testFunction
"""
		formatted, _ = formatter.format_string(content, auto_fix=True)

		# Should preserve existing doc and add missing ones
		assert "doc: Custom module documentation" in formatted
		assert "doc: TestClass class" in formatted
		assert "doc: testFunction function" in formatted

	def test_add_missing_docs_skip_non_documentable(self, formatter):
		"""Test that non-documentable entities don't get docs."""
		content = """
var: myVariable
const: PI
enum: Status
"""
		formatted, _ = formatter.format_string(content, auto_fix=True)

		# Should not add docs for var, const, enum
		assert "doc:" not in formatted

	def test_comprehensive_formatting(self, formatter):
		"""Test comprehensive formatting with multiple issues."""
		content = """module:TestModule
	class:TestClass[Visibility:public,IsAbstract:true]
		func:testMethod
			param:name[Type:STRING]
"""
		formatted, _ = formatter.format_string(content, auto_fix=True)

		expected_lines = [
			"module: TestModule",
			"  doc: TestModule module",
			"  class: TestClass [visibility:public, isAbstract:true]",
			"    doc: TestClass class",
			"    func: testMethod",
			"      doc: testMethod function",
			"      param: name [type:STRING]",
		]

		for line in expected_lines:
			assert line in formatted

	def test_format_empty_content(self, formatter):
		"""Test formatting empty content."""
		formatted, messages = formatter.format_string("", auto_fix=True)
		assert formatted == ""
		assert len(messages) == 0

	def test_format_comments_preserved(self, formatter):
		"""Test that comments are preserved during formatting."""
		content = """
# This is a comment
module: TestModule
  # Another comment
  class: TestClass
"""
		formatted, _ = formatter.format_string(content, auto_fix=True)

		assert "# This is a comment" in formatted
		assert "# Another comment" in formatted

	def test_format_file_success(self, formatter):
		"""Test formatting a file successfully."""
		content = "module:Test\n\tclass:MyClass"

		with tempfile.NamedTemporaryFile(mode="w", suffix=".cst", delete=False) as f:
			f.write(content)
			f.flush()

			try:
				formatted, messages = formatter.format_file(f.name, auto_fix=True)
				assert "module: Test" in formatted
				assert "class: MyClass" in formatted
				assert len(messages) >= 0  # May have remaining issues
			finally:
				Path(f.name).unlink()

	def test_format_file_not_found(self, formatter):
		"""Test formatting non-existent file."""
		formatted, messages = formatter.format_file("non_existent.cst", auto_fix=True)
		assert formatted == ""
		assert len(messages) == 1
		assert messages[0].code == "CS002"

	def test_save_formatted_file(self, formatter):
		"""Test saving formatted file in place."""
		content = "module:Test\n\tclass:MyClass"

		with tempfile.NamedTemporaryFile(mode="w", suffix=".cst", delete=False) as f:
			f.write(content)
			f.flush()

			try:
				formatter.save_formatted_file(f.name, auto_fix=True)

				# Read back the formatted content
				formatted_content = Path(f.name).read_text()
				assert "module: Test" in formatted_content
				assert "class: MyClass" in formatted_content
			finally:
				Path(f.name).unlink()

	def test_parse_error_handling(self, formatter):
		"""Test handling of content that can't be parsed."""
		content = "invalid syntax here [[["
		formatted, messages = formatter.format_string(content, auto_fix=True)

		# Should return original content if formatting breaks parsing
		assert "invalid syntax" in formatted
		assert any(msg.code == "CS001" for msg in messages)

	def test_format_doc_lines_spacing(self, formatter):
		"""Test that doc: lines are handled properly in spacing."""
		content = "module: Test\n  doc:This is documentation"
		formatted, _ = formatter.format_string(content, auto_fix=False)

		# doc: lines should not have their spacing normalized
		assert "doc:This is documentation" in formatted

	def test_convert_to_camel_case_edge_cases(self, formatter):
		"""Test edge cases in camelCase conversion."""
		# Test various naming patterns
		assert formatter._convert_to_camel_case("validName") == "validName"
		assert formatter._convert_to_camel_case("ValidName") == "validName"
		assert formatter._convert_to_camel_case("VALID_NAME") == "validName"
		assert formatter._convert_to_camel_case("valid_name") == "valid_name"
		assert formatter._convert_to_camel_case("123invalid") == "123invalid"  # Keep as-is
		assert formatter._convert_to_camel_case("A") == "a"
		assert formatter._convert_to_camel_case("AB") == "aB"

	def test_generate_placeholder_doc(self, formatter):
		"""Test placeholder documentation generation."""
		assert formatter._generate_placeholder_doc("module", "MyModule") == "MyModule module"
		assert formatter._generate_placeholder_doc("class", "MyClass") == "MyClass class"
		assert formatter._generate_placeholder_doc("func", "myFunction") == "myFunction function"
		assert formatter._generate_placeholder_doc("unknown", "MyEntity") == "MyEntity unknown"
