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

		Since the parser is creating flat structures, we need to rebuild the hierarchy
		based on the expected nesting patterns.
		"""
		if not items:
			return []

		# Check if we already have proper nesting
		has_nested_structure = any(isinstance(item, dict) and "children" in item and item["children"] for item in items)

		if has_nested_structure:
			# Hierarchy already exists
			return items

		# Build hierarchy from flat structure
		result = []
		i = 0

		while i < len(items):
			item = items[i]

			# Comments go directly to result
			if isinstance(item, dict) and "comment" in item:
				result.append(item)
				i += 1
				continue

			# For entities (modules, classes, etc.), collect their logical children
			if isinstance(item, dict) and "type" in item:
				entity = item.copy()
				children = []
				i += 1

				# Look ahead for items that should be children
				while i < len(items):
					next_item = items[i]

					# Stop if we hit another module (top-level entity)
					if isinstance(next_item, dict) and next_item.get("type") == "module":
						break

					# Stop if we hit another class at the same level for modules
					if (
						entity.get("type") == "module"
						and isinstance(next_item, dict)
						and next_item.get("type") == "class"
					):
						# This class should be a child of the module
						class_entity = next_item.copy()
						class_children = []
						i += 1

						# Look for class children (doc, func, etc.)
						while i < len(items):
							class_child = items[i]

							# Stop at next module or class
							if isinstance(class_child, dict) and class_child.get("type") in ["module", "class"]:
								break

							class_children.append(class_child)
							i += 1

						if class_children:
							# Recursively group nested children (functions, nested entities)
							class_entity["children"] = self._build_hierarchical_structure(class_children)
						children.append(class_entity)
						continue

					# Everything else is a direct child
					children.append(next_item)
					i += 1

				if children:
					entity["children"] = children
				result.append(entity)
			else:
				# Unknown item type, add as-is
				result.append(item)
				i += 1

		return result

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
		"""Return the entity name as a string, stripped of whitespace."""
		if not items:
			return ""
		item = items[0]
		if hasattr(item, "value"):
			return item.value.strip()
		if isinstance(item, str):
			return item.strip()
		return str(item).strip()

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

		Grammar rule: ATTR_KEY ":" attr_value
		Items could be [key_token, colon_token, value] or [key_token, value]
		"""
		if len(items) < 2:  # Need at least key and value  # noqa: PLR2004
			return {}

		# Extract key from first token
		key = ""
		if hasattr(items[0], "value"):
			key = items[0].value.strip()
			if ":" in key:
				key = key.strip(":")
		else:
			key = str(items[0])

		# Find the value token, skipping any colon tokens
		attr_value_token = None
		for item in items[1:]:
			# Skip colon tokens that might be passed through
			if hasattr(item, "type") and item.type in ("COLON", "LARK_COLON"):
				continue
			if hasattr(item, "value") and item.value == ":":
				continue
			# This should be our value
			attr_value_token = item
			break

		if attr_value_token is None:
			# If no value found, return empty string
			return {key: ""}

		# Process the value by calling the attr_value method directly
		value = self.attr_value([attr_value_token])

		return {key: value}

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

		# Handle Lark Token objects
		if hasattr(item, "type") and hasattr(item, "value"):
			val = item.value.strip()

			if item.type == "UNQUOTED_SIMPLE_VALUE":
				# Try to convert to numeric types if possible
				try:
					if "." in val:
						return float(val)
					if val.isdigit() or (val.startswith("-") and val[1:].isdigit()):
						return int(val)
					# For non-numeric values like "true", "false", etc.
					return val
				except ValueError:
					return val
			elif item.type == "STRING_VALUE":
				# Remove surrounding quotes
				if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
					return val[1:-1]
				return val
			elif item.type == "SIGNED_NUMBER":
				# Handle signed numbers
				try:
					if "." in val:
						return float(val)
					return int(val)
				except ValueError:
					return val
			else:
				# For any other token type, return the value
				return val

		# Fallback: convert token to string
		if hasattr(item, "value"):
			return str(item.value)

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
		"""Extract docstring content from tokens."""
		if not items:
			return ""

		# Handle different token types
		item = items[0]
		if hasattr(item, "value"):
			return item.value.strip()
		if isinstance(item, str):
			return item.strip()
		return str(item).strip()

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
		"""Extract keyword from token, stripping the colon."""
		if not items:
			return ""
		item = items[0]
		if hasattr(item, "value"):
			return item.value.rstrip(":")
		if isinstance(item, str):
			return item.rstrip(":")
		return str(item).rstrip(":")

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
