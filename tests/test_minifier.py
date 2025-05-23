"""Tests for the CodeStruct minifier."""

import pytest

from src.codestruct.minifier import CodeStructMinifier


class TestCodeStructMinifier:
	"""Test cases for the CodeStruct minifier."""

	def setup_method(self):
		"""Set up test fixtures."""
		self.minifier = CodeStructMinifier(include_legend=False)
		self.minifier_with_legend = CodeStructMinifier(include_legend=True)

	def test_basic_entity_minification(self):
		"""Test basic entity minification."""
		content = "module: test_module"
		result = self.minifier.minify_string(content)
		assert result == "m:test_module"

	def test_entity_with_attributes(self):
		"""Test entity with attributes."""
		content = "func: add [type: INTEGER, default: 0]"
		result = self.minifier.minify_string(content)
		assert result == "fn:add[t:INT,d:0]"

	def test_nested_entities(self):
		"""Test nested entity structure."""
		content = """module: math_utils
  func: add
    param: a [type: INTEGER]
    param: b [type: INTEGER]
    returns: INTEGER"""

		result = self.minifier.minify_string(content)
		expected = "m:math_utils|fn:add|p:a[t:INT],p:b[t:INT],r:INTEGER"
		assert result == expected

	def test_grouped_entities(self):
		"""Test grouped entities with ampersand."""
		content = "import: numpy & scipy & matplotlib"
		result = self.minifier.minify_string(content)
		assert result == "i:numpy&scipy&matplotlib"

	def test_grouped_entities_with_attributes(self):
		"""Test grouped entities with shared attributes."""
		content = """import: numpy & scipy & matplotlib
  type: external
  source: pypi"""

		result = self.minifier.minify_string(content)
		expected = "i:numpy&scipy&matplotlib[t:ext,s:pypi]"
		assert result == expected

	def test_complex_type_annotations(self):
		"""Test complex type annotations with quotes."""
		content = 'param: users [type: "List[User]"]'
		result = self.minifier.minify_string(content)
		assert result == "p:users[t:List[User]]"

	def test_remove_hash_ids(self):
		"""Test that hash IDs are removed."""
		content = "module: test ::: 56d375812962541bc30522febfa59c15"
		result = self.minifier.minify_string(content)
		assert result == "m:test"

	def test_skip_comments(self):
		"""Test that comments are skipped."""
		content = """# This is a comment
module: test
# Another comment
func: method"""

		result = self.minifier.minify_string(content)
		expected = "m:test;fn:method"
		assert result == expected

	def test_skip_impl_blocks(self):
		"""Test that impl blocks are omitted."""
		content = """func: add
  impl:
    ```python
    def add(a, b):
        return a + b
    ```
  param: a [type: INTEGER]"""

		result = self.minifier.minify_string(content)
		expected = "fn:add|p:a[t:INT]"
		assert result == expected

	def test_skip_doc_fields(self):
		"""Test that doc fields are optionally skipped."""
		content = """module: test
  doc: Test module documentation
  func: method"""

		result = self.minifier.minify_string(content)
		expected = "m:test|fn:method"
		assert result == expected

	def test_all_keyword_shortcuts(self):
		"""Test all keyword shortening mappings."""
		test_cases = [
			("dir: test", "d:test"),
			("file: test.py", "f:test.py"),
			("module: test", "m:test"),
			("namespace: std", "ns:std"),
			("class: MyClass", "cl:MyClass"),
			("func: method", "fn:method"),
			("lambda: double", "lm:double"),
			("attr: name", "at:name"),
			("param: value", "p:value"),
			("returns: INTEGER", "r:INTEGER"),
			("var: counter", "v:counter"),
			("const: PI", "c:PI"),
			("type_alias: UserID", "ta:UserID"),
			("union: Result", "u:Result"),
			("optional: nickname", "opt:nickname"),
			("import: sys", "i:sys"),
		]

		for input_str, expected in test_cases:
			result = self.minifier.minify_string(input_str)
			assert result == expected, f"Failed for {input_str}"

	def test_all_type_abbreviations(self):
		"""Test all type abbreviations."""
		test_cases = [
			("func: test [type: INTEGER]", "fn:test[t:INT]"),
			("func: test [type: STRING]", "fn:test[t:STR]"),
			("func: test [type: BOOLEAN]", "fn:test[t:BOOL]"),
			("func: test [type: FLOAT]", "fn:test[t:FLT]"),
			("import: test [type: external]", "i:test[t:ext]"),
			("import: test [type: internal]", "i:test[t:int]"),
		]

		for input_str, expected in test_cases:
			result = self.minifier.minify_string(input_str)
			assert result == expected, f"Failed for {input_str}"

	def test_attribute_key_shortcuts(self):
		"""Test attribute key shortening."""
		test_cases = [
			("func: test [type: STRING]", "fn:test[t:STR]"),
			("func: test [default: value]", "fn:test[d:value]"),
			("import: test [source: stdlib]", "i:test[s:stdlib]"),
			("import: test [ref: class: User]", "i:test[rf:class: User]"),
		]

		for input_str, expected in test_cases:
			result = self.minifier.minify_string(input_str)
			assert result == expected, f"Failed for {input_str}"

	def test_readme_example_minification(self):
		"""Test the README example minification."""
		content = """dir: my_project ::: 56d375812962541bc30522febfa59c15
  file: math_utils.py ::: 56d375812962541bc30522febfa59c15
    module: math_utils ::: a7c5e83bf61d49eb89f64aa3cc85121d
      import: numpy & scipy ::: 3e1fc985a72401d487ce4abad98e4a36
        type: external
        source: pypi
      func: add ::: 2b8a9cf7e1243f6a82f45c8b8ef28d7b
        param: a [type: INTEGER]
        param: b [type: INTEGER]
        returns: INTEGER
      func: multiply ::: 4f9a0c8d75b2461ea3e97fe72d81f5c0
        param: a [type: INTEGER]
        param: b [type: INTEGER]
        returns: INTEGER
        import: add ::: 2b8a9cf7e1243f6a82f45c8b8ef28d7b
          type: internal
          ref: func: add
      const: PI ::: d3fa68c1e0584ab58e2c52e9ba187c95
        [type: FLOAT, default: 3.14159]
  file: README.md ::: 1a4f5bcd78e96f201ac37985b9b67e29"""

		result = self.minifier.minify_string(content)
		expected = "d:my_project|f:math_utils.py|m:math_utils|i:numpy&scipy[t:ext,s:pypi],fn:add|p:a[t:INT],p:b[t:INT],r:INTEGER,fn:multiply|p:a[t:INT],p:b[t:INT],r:INTEGER,i:add[t:int,rf:func: add],c:PI[t:FLT,d:3.14159],f:README.md"
		assert result == expected

	def test_legend_generation(self):
		"""Test legend generation."""
		content = "module: test"
		result = self.minifier_with_legend.minify_string(content)

		assert "# CodeStruct Minified Format Legend" in result
		assert "# Keywords:" in result
		assert "# Attributes:" in result
		assert "# Types:" in result
		assert "# Delimiters:" in result
		assert "m:test" in result

	def test_empty_content(self):
		"""Test empty content handling."""
		result = self.minifier.minify_string("")
		assert result == ""

		result = self.minifier.minify_string("   \n\n   ")
		assert result == ""

	def test_parse_error_handling(self):
		"""Test handling of invalid content."""
		content = "invalid: syntax $$$ error"
		# The minifier should handle invalid content gracefully
		result = self.minifier.minify_string(content)
		# Should just treat it as a regular entity
		assert "invalid:syntax $$$ error" in result

	def test_file_operations(self, tmp_path):
		"""Test file reading and writing operations."""
		# Create a test file
		test_file = tmp_path / "test.cst"
		content = """module: test
  func: method [type: STRING]"""
		test_file.write_text(content)

		# Test minify_file
		result = self.minifier.minify_file(str(test_file))
		expected = "m:test|fn:method[t:STR]"
		assert result == expected

		# Test save_minified_file
		output_file = self.minifier.save_minified_file(str(test_file))
		assert output_file == str(test_file.with_suffix(".min.cst"))

		minified_content = tmp_path / "test.min.cst"
		assert minified_content.exists()
		assert minified_content.read_text().strip() == expected

	def test_file_not_found(self):
		"""Test file not found error."""
		with pytest.raises(FileNotFoundError):
			self.minifier.minify_file("nonexistent.cst")

	def test_multiple_attributes(self):
		"""Test multiple attributes in brackets."""
		content = "func: test [type: STRING, default: hello, source: external]"
		result = self.minifier.minify_string(content)
		expected = "fn:test[t:STR,d:hello,s:ext]"
		assert result == expected

	def test_quoted_attribute_values(self):
		"""Test quoted attribute values."""
		content = 'param: data [type: "List[Dict[str, Any]]"]'
		result = self.minifier.minify_string(content)
		expected = "p:data[t:List[Dict[str, Any]]]"
		assert result == expected

	def test_boolean_values(self):
		"""Test boolean value abbreviations."""
		content = """func: test [static: true]
attr: flag [default: false]"""
		result = self.minifier.minify_string(content)
		expected = "fn:test[st:T];at:flag[d:F]"
		assert result == expected
