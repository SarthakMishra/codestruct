"""Document symbols feature for CodeStruct LSP."""

from lsprotocol import types as lsp
from pygls.server import LanguageServer

from codestruct.parser import CodeStructParser, ParseError
from codestruct.transformer import CodeStructTransformer

# Constants
MAX_DOC_LENGTH = 50
DOC_TRUNCATE_LENGTH = 47


def get_document_symbols(server: LanguageServer, params: lsp.DocumentSymbolParams) -> list[lsp.DocumentSymbol]:
	"""Get document symbols for outline/structure view."""
	uri = params.text_document.uri
	document = server.workspace.get_text_document(uri)

	try:
		parser = CodeStructParser.get_instance()
		transformer = CodeStructTransformer.get_instance()

		tree = parser.parse_string(document.source)
		transformed = transformer.start(tree.children)

		return _convert_to_document_symbols(transformed, document.lines)

	except ParseError:
		return []


def _convert_to_document_symbols(entities: list, document_lines: list[str]) -> list[lsp.DocumentSymbol]:
	"""Convert transformed entities to LSP document symbols."""
	symbols = []

	for entity in entities:
		if isinstance(entity, dict) and "type" in entity and "name" in entity:
			symbol = _create_document_symbol(entity, document_lines)
			if symbol:
				symbols.append(symbol)

	return symbols


def _create_document_symbol(entity: dict, document_lines: list[str]) -> lsp.DocumentSymbol | None:
	"""Create a document symbol from an entity."""
	entity_type = entity.get("type")
	entity_name = entity.get("name")

	if not entity_type or not entity_name:
		return None

	# Map entity types to LSP symbol kinds
	symbol_kind = _get_symbol_kind(entity_type)

	# Find the line where this entity is defined
	entity_line = _find_entity_line(entity_name, entity_type, document_lines)

	# Create range for the entity
	start_line = max(0, entity_line)
	end_line = start_line

	# If entity has children, extend range to include them
	if entity.get("children"):
		# Estimate end line based on children
		end_line = min(len(document_lines) - 1, start_line + len(entity["children"]) + 1)

	# Get detail information
	detail = _get_symbol_detail(entity)

	# Create child symbols
	children = []
	if "children" in entity:
		children = _convert_to_document_symbols(entity["children"], document_lines)

	return lsp.DocumentSymbol(
		name=entity_name,
		detail=detail,
		kind=symbol_kind,
		range=lsp.Range(
			start=lsp.Position(line=start_line, character=0),
			end=lsp.Position(
				line=end_line, character=len(document_lines[end_line]) if end_line < len(document_lines) else 0
			),
		),
		selection_range=lsp.Range(
			start=lsp.Position(line=start_line, character=0),
			end=lsp.Position(
				line=start_line, character=len(document_lines[start_line]) if start_line < len(document_lines) else 0
			),
		),
		children=children,
	)


def _get_symbol_kind(entity_type: str) -> lsp.SymbolKind:
	"""Map entity type to LSP symbol kind."""
	mapping = {
		"module": lsp.SymbolKind.Module,
		"class": lsp.SymbolKind.Class,
		"func": lsp.SymbolKind.Function,
		"param": lsp.SymbolKind.Variable,
		"returns": lsp.SymbolKind.Variable,
		"var": lsp.SymbolKind.Variable,
		"const": lsp.SymbolKind.Constant,
		"type_alias": lsp.SymbolKind.TypeParameter,
		"union": lsp.SymbolKind.TypeParameter,
		"optional": lsp.SymbolKind.TypeParameter,
		"import": lsp.SymbolKind.Package,
		"dir": lsp.SymbolKind.Package,
		"file": lsp.SymbolKind.File,
		"namespace": lsp.SymbolKind.Namespace,
		"lambda": lsp.SymbolKind.Function,
		"attr": lsp.SymbolKind.Property,
		"doc": lsp.SymbolKind.String,
		"impl": lsp.SymbolKind.Method,
	}

	return mapping.get(entity_type, lsp.SymbolKind.Object)


def _find_entity_line(entity_name: str, entity_type: str, document_lines: list[str]) -> int:
	"""Find the line number where an entity is defined."""
	# Look for pattern: "entity_type: entity_name"
	pattern = f"{entity_type}: {entity_name}"

	for i, line in enumerate(document_lines):
		if pattern in line:
			return i

	# Fallback: look for just the name
	for i, line in enumerate(document_lines):
		if entity_name in line:
			return i

	return 0


def _get_symbol_detail(entity: dict) -> str:
	"""Get detail string for symbol."""
	details = []

	# Add type information from attributes
	if "attributes" in entity:
		attrs = entity["attributes"]
		if "type" in attrs:
			details.append(f"type: {attrs['type']}")
		if "visibility" in attrs:
			details.append(f"visibility: {attrs['visibility']}")

	# Add documentation summary
	if "children" in entity:
		for child in entity["children"]:
			if isinstance(child, dict) and "doc" in child:
				doc = child["doc"]
				# Truncate long documentation
				if len(doc) > MAX_DOC_LENGTH:
					doc = doc[:DOC_TRUNCATE_LENGTH] + "..."
				details.append(f"doc: {doc}")
				break

	return " | ".join(details) if details else ""
