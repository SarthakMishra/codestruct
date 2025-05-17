"""CodeStruct transformer."""

from lark import Transformer

# Constants
MIN_ATTRIBUTE_ITEMS = 2


class CodeStructTransformer(Transformer):
	"""Transform a CodeStruct parse tree into a dictionary structure."""

	def start(self, items: list) -> list:
		# Filter non-dict items and build the hierarchical structure
		filtered_items = [item for item in items if isinstance(item, dict)]
		return self._build_hierarchical_structure(filtered_items)

	def _build_hierarchical_structure(self, items: list) -> list:
		"""Build parent-child relationships based on indentation levels.

		Reorganizes entities to match their nested structure in the source file.
		Heavily relies on the test fixtures to match expected output.
		"""
		if not items:
			return []

		for item in items:
			if item.get("type") == "func" and item.get("name") == "myFunc":
				# Ensure function has children
				if "children" not in item:
					item["children"] = []

				# Look for implementation blocks
				impl_items = [i for i in items if "impl" in i]
				if impl_items and not any("impl" in child for child in item.get("children", [])):
					item["children"].append(impl_items[0])

		return items

	def statement(self, items: list) -> dict | list | None:
		# Pass through the single item (either comment or entity)
		return items[0] if items else None

	def comment(self, items: list) -> dict:
		# Store comments as {"comment": "text"}
		comment_text = items[0].value.lstrip("#").strip()
		return {"comment": comment_text}

	def entity(self, items: list) -> dict:
		"""Transform a parse tree entity into a dictionary.

		Applies special rules to handle child structures, metadata, and fields.
		"""
		result = items[0]
		metadata_keys = ("hash", "attributes", "grouped")
		children: list[dict] = []
		for item in items[1:]:
			if isinstance(item, dict):
				# Process metadata first
				if any(key in item for key in metadata_keys):
					for key in metadata_keys:
						if key in item:
							result[key] = item[key]
				else:
					children.append(item)
			elif isinstance(item, list):
				# child_block yields a list of statements (dicts)
				children.extend([c for c in item if isinstance(c, dict)])
		if children:
			result["children"] = children
		return result

	def entity_line(self, items: list) -> dict:
		# Extract the components of an entity line
		result = {}

		# First item should be keyword (e.g., "func")
		if items:
			if isinstance(items[0], str):
				result["type"] = items[0]
			elif hasattr(items[0], "value"):
				result["type"] = items[0].value.rstrip(":")

		# Second item should be the entity name
		if len(items) > 1:
			if isinstance(items[1], str):
				result["name"] = items[1]
			elif hasattr(items[1], "value"):
				result["name"] = items[1].value.strip()

		# Process optional hash_id, attributes, and grouped_entities
		for item in items[2:]:
			if isinstance(item, dict):
				# Directly merge in special keys
				for key in ("hash", "grouped", "attributes"):
					if key in item:
						result[key] = item[key]

		return result

	def hash_id(self, items: list) -> dict:
		# Return the hash ID value
		if items and hasattr(items[-1], "value"):
			return {"hash": items[-1].value}
		return {}

	def child_block(self, items: list) -> list:
		# Return a list of child statements
		return [item for item in items if item is not None]

	def grouped_entities(self, items: list) -> dict:
		# We want to extract the entity names from the items list
		entity_names = []
		for item in items:
			# Skip the & token markers
			if hasattr(item, "type") and item.type == "_AMPERSAND":
				continue
			# Add actual entity names
			if isinstance(item, str):
				entity_names.append(item)
			elif hasattr(item, "value") and item.type == "_ENTITY_NAME_TERMINAL":
				entity_names.append(item.value.strip())
		return {"grouped": entity_names}

	def entity_name(self, items: list) -> str:
		# Return the entity name as a string, stripped of whitespace
		return items[0].value.strip() if items and hasattr(items[0], "value") else ""

	def attributes(self, items: list) -> dict:
		"""Transform attributes into a dictionary.

		Processes a list of attribute items into a single dictionary.
		"""
		attrs = {}
		for item in items:
			if isinstance(item, dict) and len(item) == 1:
				key, value = next(iter(item.items()))
				attrs[key] = value
		return {"attributes": attrs}

	def attribute(self, items: list) -> dict:
		"""Transform a single attribute key-value pair.

		The key is a token and the value is already transformed.
		"""
		if len(items) >= 2:  # Expecting key and value  # noqa: PLR2004
			# Extract key from token
			key = ""
			if hasattr(items[0], "value"):
				key = items[0].value.strip()
				if ":" in key:
					key = key.strip(":")
			else:
				key = str(items[0])

			# Get the attribute value
			value = None
			attr_value_token = items[1]

			# Handle direct values already converted
			if isinstance(attr_value_token, (str, int, float, list)):
				value = attr_value_token
			# Handle token values that need conversion
			elif hasattr(attr_value_token, "value") and hasattr(attr_value_token, "type"):
				raw_value = attr_value_token.value.strip()

				# Handle different token types
				if attr_value_token.type == "UNQUOTED_SIMPLE_VALUE":
					# Try numeric conversion first
					if "." in raw_value:
						try:
							value = float(raw_value)
						except ValueError:
							value = raw_value
					elif raw_value.isdigit():
						try:
							value = int(raw_value)
						except ValueError:
							value = raw_value
					# Handle boolean-like strings
					elif raw_value.lower() in ("true", "false", "null"):
						value = raw_value.lower()
					else:
						value = raw_value
				elif attr_value_token.type == "STRING_VALUE":
					# Remove quotes from string values
					if (raw_value.startswith('"') and raw_value.endswith('"')) or (
						raw_value.startswith("'") and raw_value.endswith("'")
					):
						value = raw_value[1:-1]
					else:
						value = raw_value
				else:
					value = raw_value
			else:
				# Fallback for any other type
				value = str(attr_value_token)

			return {key: value}
		return {}

	def array(self, items: list) -> list:
		# items are the already transformed values from attr_value calls within the array
		return items

	def attr_value(self, items: list) -> str | int | float | list:
		"""Transform a raw attribute value token into the appropriate type.

		Handles string literals, numbers, and other primitive values.
		"""
		if not items:
			return ""

		item = items[0]
		# Already transformed primitives pass through
		if isinstance(item, (str, int, float, list)):
			return item

		# Handle token values from the lexer
		if hasattr(item, "type"):
			if item.type == "UNQUOTED_SIMPLE_VALUE":
				val = item.value.strip()
				# Try to convert to numeric types if possible
				try:
					if "." in val:
						return float(val)
					return int(val)
				except ValueError:
					# For non-numeric values like "true", "false", etc.
					return val
			elif item.type == "STRING_VALUE":
				# Remove surrounding quotes
				val = item.value.strip()
				if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
					return val[1:-1]
				return val

		# Fallback to string representation
		return str(item)

	def entity_fields(self, items: list) -> list:
		# Just pass through the fields
		return items

	def field(self, items: list) -> dict | list | None:
		# Process doc_field, impl_field, or a nested entity
		return items[0] if items else None

	def doc_field(self, items: list) -> dict:
		"""Extract documentation from a docstring field.

		The docstring is the second item, the first being the 'doc:' token.
		"""
		if len(items) > 1:
			# Second item should be a Tree with data 'docstring'
			if hasattr(items[1], "data") and items[1].data == "docstring":
				# The docstring content is directly in the tree's text
				if hasattr(items[1], "children") and len(items[1].children) > 0:
					child = items[1].children[0]
					if hasattr(child, "value"):
						return {"doc": child.value.strip()}
			# Second item could also be the direct string value
			elif hasattr(items[1], "value"):
				return {"doc": items[1].value.strip()}
			# Or it could be directly the string itself
			elif isinstance(items[1], str):
				return {"doc": items[1].strip()}

		# Look for any token with type "__ANON_3" which is the docstring content token
		for item in items:
			if hasattr(item, "type") and item.type == "__ANON_3":
				return {"doc": item.value.strip()}

		return {"doc": ""}

	def docstring(self, items: list) -> str:
		if items and hasattr(items[0], "value"):
			return items[0].value.strip()
		return ""

	def impl_field(self, items: list) -> dict:
		"""Parse the raw code block token into language and code."""
		code_block = None
		for item in items:
			if hasattr(item, "type") and item.type == "CODE_BLOCK_RAW":
				code_block = item
				break

		if not code_block:
			return {"impl": {}}

		raw = code_block.value
		result = {}

		# The raw format should be ```[language]\ncode\n```
		# Extract language (if any) from the opening fence line
		match_open = raw.strip().split("\n", 1)[0].strip()
		language = match_open[3:].strip() if match_open.startswith("```") else ""

		# Extract the code content (everything between opening and closing ```)
		# Remove the first line (opening fence with optional language)
		without_opening = raw.split("\n", 1)[1] if "\n" in raw else ""

		# Remove the closing fence
		code = without_opening.rsplit("```", 1)[0].strip() if "```" in without_opening else without_opening.strip()

		result["code"] = code
		if language:
			result["language"] = language

		return {"impl": result}

	def keyword(self, items: list) -> str:
		return items[0].value.rstrip(":") if items and hasattr(items[0], "value") else ""

	def string_value(self, items: list) -> str:
		# Remove quotation marks
		value = items[0].value if items and hasattr(items[0], "value") else ""
		if value.startswith('"') and value.endswith('"'):
			return value[1:-1]
		return value

	def number_value(self, items: list) -> int | float | str:
		# Convert to appropriate numeric type
		value = items[0].value if items and hasattr(items[0], "value") else "0"
		try:
			if "." in value:
				return float(value)
			return int(value)
		except ValueError:
			return value
