"""Code actions feature for CodeStruct LSP."""

from lsprotocol import types as lsp
from pygls.server import LanguageServer
from pygls.workspace import TextDocument


def get_code_actions(server: LanguageServer, params: lsp.CodeActionParams) -> list[lsp.CodeAction]:
	"""Provide code actions for quick fixes and refactoring."""
	uri = params.text_document.uri
	document = server.workspace.get_text_document(uri)
	range_start = params.range.start
	range_end = params.range.end

	actions = []

	# Get diagnostics for the current range
	diagnostics = params.context.diagnostics

	# Add fixes for diagnostics
	for diagnostic in diagnostics:
		if hasattr(diagnostic, "code") and diagnostic.code:
			code_fixes = _get_diagnostic_fixes(diagnostic, document)
			actions.extend(code_fixes)

	# Add general code actions based on context
	context_actions = _get_context_actions(document, range_start, range_end)
	actions.extend(context_actions)

	return actions


def _get_diagnostic_fixes(diagnostic: lsp.Diagnostic, document: TextDocument) -> list[lsp.CodeAction]:
	"""Get code action fixes for a specific diagnostic."""
	fixes = []
	code = diagnostic.code

	if code == "CS101":  # Short entity name
		fixes.append(_create_expand_name_action(diagnostic, document))
	elif code == "CS201":  # Missing documentation
		fixes.append(_create_add_documentation_action(diagnostic, document))
	elif code == "CS301":  # Hash format
		fixes.append(_create_fix_hash_format_action(diagnostic, document))
	elif code == "CS401":  # Attribute naming
		fixes.append(_create_fix_attribute_naming_action(diagnostic, document))

	return [fix for fix in fixes if fix is not None]


def _create_expand_name_action(diagnostic: lsp.Diagnostic, document: TextDocument) -> lsp.CodeAction | None:
	"""Create action to expand short entity names."""
	line_idx = diagnostic.range.start.line
	if line_idx >= len(document.lines):
		return None

	line = document.lines[line_idx]

	# Try to suggest a better name
	if ": a " in line:
		new_line = line.replace(": a ", ": action ")
	elif ": b " in line:
		new_line = line.replace(": b ", ": button ")
	elif ": c " in line:
		new_line = line.replace(": c ", ": component ")
	elif ": d " in line:
		new_line = line.replace(": d ", ": data ")
	elif ": e " in line:
		new_line = line.replace(": e ", ": element ")
	elif ": f " in line:
		new_line = line.replace(": f ", ": function ")
	elif ": i " in line:
		new_line = line.replace(": i ", ": item ")
	elif ": m " in line:
		new_line = line.replace(": m ", ": method ")
	elif ": p " in line:
		new_line = line.replace(": p ", ": parameter ")
	elif ": r " in line:
		new_line = line.replace(": r ", ": result ")
	elif ": s " in line:
		new_line = line.replace(": s ", ": service ")
	elif ": t " in line:
		new_line = line.replace(": t ", ": type ")
	elif ": v " in line:
		new_line = line.replace(": v ", ": value ")
	else:
		return None

	return lsp.CodeAction(
		title="Expand short entity name",
		kind=lsp.CodeActionKind.QuickFix,
		edit=lsp.WorkspaceEdit(
			changes={
				document.uri: [
					lsp.TextEdit(
						range=lsp.Range(
							start=lsp.Position(line=line_idx, character=0),
							end=lsp.Position(line=line_idx, character=len(line)),
						),
						new_text=new_line,
					)
				]
			}
		),
	)


def _create_add_documentation_action(diagnostic: lsp.Diagnostic, document: TextDocument) -> lsp.CodeAction | None:
	"""Create action to add documentation to entities."""
	line_idx = diagnostic.range.start.line
	if line_idx >= len(document.lines):
		return None

	line = document.lines[line_idx]
	indent = len(line) - len(line.lstrip())
	doc_indent = " " * (indent + 2)

	# Extract entity name for documentation template
	entity_name = "entity"
	if ":" in line:
		parts = line.split(":")
		if len(parts) > 1:
			entity_name = parts[1].strip().split()[0]

	doc_line = f'{doc_indent}doc: "Description of {entity_name}"\n'

	return lsp.CodeAction(
		title="Add documentation",
		kind=lsp.CodeActionKind.QuickFix,
		edit=lsp.WorkspaceEdit(
			changes={
				document.uri: [
					lsp.TextEdit(
						range=lsp.Range(
							start=lsp.Position(line=line_idx + 1, character=0),
							end=lsp.Position(line=line_idx + 1, character=0),
						),
						new_text=doc_line,
					)
				]
			}
		),
	)


def _create_fix_hash_format_action(diagnostic: lsp.Diagnostic, document: TextDocument) -> lsp.CodeAction | None:
	"""Create action to fix hash format violations."""
	line_idx = diagnostic.range.start.line
	if line_idx >= len(document.lines):
		return None

	line = document.lines[line_idx]

	# Find hash ID and suggest a fix
	import re

	hash_match = re.search(r":::([\w-]+)", line)
	if not hash_match:
		return None

	old_hash = hash_match.group(1)
	# Convert to valid format (alphanumeric + underscore)
	new_hash = re.sub(r"[^a-zA-Z0-9_]", "_", old_hash)
	if new_hash and not new_hash[0].isalpha():
		new_hash = "h_" + new_hash

	new_line = line.replace(f":::{old_hash}", f":::{new_hash}")

	return lsp.CodeAction(
		title="Fix hash ID format",
		kind=lsp.CodeActionKind.QuickFix,
		edit=lsp.WorkspaceEdit(
			changes={
				document.uri: [
					lsp.TextEdit(
						range=lsp.Range(
							start=lsp.Position(line=line_idx, character=0),
							end=lsp.Position(line=line_idx, character=len(line)),
						),
						new_text=new_line,
					)
				]
			}
		),
	)


def _create_fix_attribute_naming_action(diagnostic: lsp.Diagnostic, document: TextDocument) -> lsp.CodeAction | None:
	"""Create action to fix attribute naming violations."""
	line_idx = diagnostic.range.start.line
	if line_idx >= len(document.lines):
		return None

	line = document.lines[line_idx]

	# Find attribute key and suggest a fix
	import re

	attr_match = re.search(r"\[([^:]+):", line)
	if not attr_match:
		return None

	old_attr = attr_match.group(1).strip()
	# Convert to camelCase
	new_attr = _to_camel_case(old_attr)

	new_line = line.replace(f"[{old_attr}:", f"[{new_attr}:")

	return lsp.CodeAction(
		title="Fix attribute naming",
		kind=lsp.CodeActionKind.QuickFix,
		edit=lsp.WorkspaceEdit(
			changes={
				document.uri: [
					lsp.TextEdit(
						range=lsp.Range(
							start=lsp.Position(line=line_idx, character=0),
							end=lsp.Position(line=line_idx, character=len(line)),
						),
						new_text=new_line,
					)
				]
			}
		),
	)


def _get_context_actions(
	document: TextDocument, range_start: lsp.Position, _range_end: lsp.Position
) -> list[lsp.CodeAction]:
	"""Get context-specific code actions."""
	actions = []

	# Add entity template actions
	actions.append(_create_add_class_template_action(document, range_start))
	actions.append(_create_add_function_template_action(document, range_start))
	actions.append(_create_add_module_template_action(document, range_start))

	return [action for action in actions if action is not None]


def _create_add_class_template_action(document: TextDocument, position: lsp.Position) -> lsp.CodeAction:
	"""Create action to add a class template."""
	template = """class: NewClass
  doc: "Description of NewClass"
  func: constructor
    doc: "Initialize new instance"
  func: method
    doc: "A method of this class"
"""

	return lsp.CodeAction(
		title="Insert class template",
		kind=lsp.CodeActionKind.Source,
		edit=lsp.WorkspaceEdit(
			changes={
				document.uri: [
					lsp.TextEdit(
						range=lsp.Range(
							start=position,
							end=position,
						),
						new_text=template,
					)
				]
			}
		),
	)


def _create_add_function_template_action(document: TextDocument, position: lsp.Position) -> lsp.CodeAction:
	"""Create action to add a function template."""
	template = """func: newFunction
  doc: "Description of newFunction"
  param: input [type: STRING]
    doc: "Input parameter"
  returns: output [type: STRING]
    doc: "Return value"
"""

	return lsp.CodeAction(
		title="Insert function template",
		kind=lsp.CodeActionKind.Source,
		edit=lsp.WorkspaceEdit(
			changes={
				document.uri: [
					lsp.TextEdit(
						range=lsp.Range(
							start=position,
							end=position,
						),
						new_text=template,
					)
				]
			}
		),
	)


def _create_add_module_template_action(document: TextDocument, position: lsp.Position) -> lsp.CodeAction:
	"""Create action to add a module template."""
	template = """module: NewModule
  doc: "Description of NewModule"
  class: ExampleClass
    doc: "An example class in this module"
    func: exampleMethod
      doc: "An example method"
"""

	return lsp.CodeAction(
		title="Insert module template",
		kind=lsp.CodeActionKind.Source,
		edit=lsp.WorkspaceEdit(
			changes={
				document.uri: [
					lsp.TextEdit(
						range=lsp.Range(
							start=position,
							end=position,
						),
						new_text=template,
					)
				]
			}
		),
	)


def _to_camel_case(snake_str: str) -> str:
	"""Convert snake_case to camelCase."""
	components = snake_str.split("_")
	return components[0].lower() + "".join(word.capitalize() for word in components[1:])
