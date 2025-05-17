"""CodeStruct transformer."""

from lark import Transformer

# Constants
MIN_ATTRIBUTE_ITEMS = 2


class CodeStructTransformer(Transformer):
	"""Transform a CodeStruct parse tree into a dictionary structure."""

	def start(self, items: list) -> list:
		# Check for sibling entities with indentation relationships
		result = []
		current_entity = None

		for item in items:
			if isinstance(item, dict):
				# If we have an entity and get another one, store the previous one
				if current_entity is not None:
					result.append(current_entity)
					current_entity = item
				else:
					current_entity = item
			# Skip if it's a token
			elif not hasattr(item, "type"):
				continue

		# Add the last entity if there was one
		if current_entity is not None:
			result.append(current_entity)

		# Process the list to build parent-child relationships
		return self._build_hierarchical_structure(result)

	def _build_hierarchical_structure(self, items: list) -> list:
		# Build parent-child relationships by checking if subsequent items are children
		# of previous items based on their indentation level in the original source.
		if not items:
			return []

		# First pass: fix up the grouped_entities processing
		for item in items:
			if "grouped" in item and isinstance(item["grouped"], list):
				# Filter out any tokens and keep only string values
				item["grouped"] = [
					x
					for x in item["grouped"]
					if isinstance(x, str)
					and not (
						hasattr(x, "type")  # This checks if it's an object with type attribute
					)
				]

		# Second pass: build hierarchy from tokens in the parse tree
		result = []

		# Build a tree from our entities
		i = 0

		while i < len(items):
			item = items[i]

			# Case 1: New module/class/function entity with potential children
			if "type" in item:
				# Look ahead for entities that should be its children
				j = i + 1
				children = []

				# Collect consecutive fields (impl, doc) and nested entities
				while j < len(items):
					candidate = items[j]
					# Fields like impl/doc or any nested entity
					if (
						"impl" in candidate
						or "doc" in candidate
						or ("type" in candidate and j > i + 1)  # Not first item after parent
					):
						children.append(candidate)
						j += 1
					else:
						break

				# If we found children, attach them
				if children:
					if "children" not in item:
						item["children"] = []
					item["children"].extend(children)
					i = j  # Skip the items we've processed as children
				else:
					i += 1

				result.append(item)
			else:
				# Case 2: Top-level non-entity (like comments)
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
		# Start with the basic entity_line dict…
		result = items[0]
		# Define metadata keys to exclude from children
		metadata_keys = ("hash", "attributes", "grouped")
		# Merge metadata dicts into the entity
		for item in items[1:]:
			if isinstance(item, dict):
				for key in metadata_keys:
					if key in item:
						result[key] = item[key]
		# Collect all non-metadata dict items as children (including comments, doc, impl, nested entities)
		children = []
		children = [
			item for item in items[1:] if isinstance(item, dict) and not any(key in item for key in metadata_keys)
		]
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
				if "hash" in item:
					result["hash"] = item["hash"]
				elif "attributes" in item:
					result["attributes"] = item["attributes"]
			elif isinstance(item, list) and all(isinstance(x, str) for x in item):
				result["grouped"] = item

		return result

	def hash_id(self, items: list) -> dict:
		# Return the hash ID value
		if items and hasattr(items[-1], "value"):
			return {"hash": items[-1].value}
		return {}

	def child_block(self, items: list) -> list:
		# Return a list of child statements
		return [item for item in items if item is not None]

	def grouped_entities(self, items: list) -> list:
		# We want to extract the entity names from the items list
		entity_names = []
		for item in items:
			if isinstance(item, str):
				# Already a string value
				entity_names.append(item)
			elif hasattr(item, "value") and item.type == "_ENTITY_NAME_TERMINAL":
				entity_names.append(item.value.strip())
		return entity_names

	def entity_name(self, items: list) -> str:
		# Return the entity name as a string, stripped of whitespace
		return items[0].value.strip() if items and hasattr(items[0], "value") else ""

	def attributes(self, items: list) -> dict:
		# Transform attributes into a dictionary
		attrs = {}
		for item in items:
			if isinstance(item, dict) and len(item) == 1:
				key, value = next(iter(item.items()))
				attrs[key] = value
		return {"attributes": attrs}

	def attribute(self, items: list) -> dict:
		# items should be [key_token, value_transformed]
		if len(items) == 2:  # Expecting key and value  # noqa: PLR2004
			key = items[0].value if hasattr(items[0], "value") else str(items[0])
			value = items[1]
			return {key: value}
		return {}

	def array(self, items: list) -> list:
		# items are the already transformed values from attr_value calls within the array
		return items

	def attr_value(self, items: list) -> str | int | float | list:
		if not items:
			return ""
		item = items[0]
		# Check if it's a token that needs its value extracted (e.g., UNQUOTED_SIMPLE_VALUE)
		# string_value, number_value, and array would have already transformed their children.
		if isinstance(item, (str, int, float, list)):
			return item  # Already transformed by string_value, number_value, or array itself
		if hasattr(item, "type") and item.type == "UNQUOTED_SIMPLE_VALUE":
			return item.value
		# Fallback for unexpected cases, though ideally should not be reached if grammar/transformer align
		return str(item)

	def entity_fields(self, items: list) -> list:
		# Just pass through the fields
		return items

	def field(self, items: list) -> dict | list | None:
		# Process doc_field, impl_field, or a nested entity
		return items[0] if items else None

	def doc_field(self, items: list) -> dict:
		# Return the docstring
		return {"doc": items[0].value if items and hasattr(items[0], "value") else ""}

	def docstring(self, items: list) -> str:
		return items[0] if items else ""

	def impl_field(self, items: list) -> dict:
		# Parse the raw code block token into language and code
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
