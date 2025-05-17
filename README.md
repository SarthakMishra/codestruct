# CodeStruct

## 1. Overview

**CodeStruct** is a plain-text, human- and machine-readable, language-agnostic notation for describing the structure of software. It captures entities such as modules, classes, functions, parameters, variables, and more, in a concise, hierarchical, and extensible format. CodeStruct is designed for LLM context compression.

---

## 2. Syntax Rules

### 2.1. Hierarchy and Indentation

- **Hierarchy** is represented by indentation (spaces or tabs; consistent usage is required).
- **Parent entities** contain **child entities** indented beneath them.

### 2.2. Entity Declaration

- Each entity is declared on a new line with the format:  
  ```
  :  []
  ```
- **Keywords** identify the entity type (see section 3).
- **Attributes** are optional, enclosed in square brackets, and comma-separated.

### 2.3. Attributes

- Attributes are key-value pairs: `key: value`
- Multiple attributes are separated by commas: `[type: INTEGER, default: 0]`
- Complex type annotations containing special characters (like `[]|,(){}`) should be wrapped in double quotes: `[type: "List[Dict[str, Any]]"]`

### 2.4. Documentation

- Use the `doc:` field after an entity to provide a one-line summary (first line of the docstring, truncated with `...` if needed).

### 2.5. Comments

- Lines starting with `#` are comments and ignored by parsers.

### 2.6. Grouping Entities

- Use the ampersand (`&`) to group related entities of the same type under a common parent. This is especially useful for imports from the same source:
  ```
  import: logging & os & sys & pathlib
    source: stdlib
  ```
- Grouped entities remain separate logical entities but share common attributes, reducing repetition.
- Unlike comma-separated lists (which separate attributes), ampersand indicates entity grouping and doesn't conflict with minification.

### 2.7. Implementation Blocks

- Use the `impl:` field to provide the full implementation of an entity (such as a function or method).
- The value for `impl:` must be a fenced code block (triple backticks), similar to Markdown.
- The language for the code block should be specified (e.g., ```python).
- The implementation block is for documentation and context only and **must be ignored during minification**.
- Example:
  ```
  func: add
    impl:
      ```python
      def add(a, b):
          return a + b
      ```
  ```

---

## 3. Supported Entity Keywords

| Keyword      | Description                                 | Example Usage                        |
|--------------|---------------------------------------------|--------------------------------------|
| `dir:`       | Directory (for filesystem hierarchy)         | `dir: src`                           |
| `file:`      | File                                        | `file: main.py`                      |
| `module:`    | Module or package                           | `module: user_management`            |
| `namespace:` | Namespace (for languages with namespaces)    | `namespace: std`                     |
| `class:`     | Class or type definition                    | `class: User`                        |
| `func:`      | Function or method                          | `func: login [type: Async]`          |
| `lambda:`    | Lambda expression                           | `lambda: double`                     |
| `attr:`      | Attribute or class field                    | `attr: name [type: STRING]`          |
| `param:`     | Function/method parameter                   | `param: username [type: STRING]`     |
| `returns:`   | Function/method return type/value           | `returns: BOOLEAN`                   |
| `var:`       | Variable                                    | `var: counter [type: INTEGER]`       |
| `const:`     | Constant                                    | `const: PI [type: FLOAT]`            |
| `type_alias:`| Type alias                                  | `type_alias: UserID [type: INTEGER]` |
| `union:`     | Union type                                  | `union: Result`                      |
| `optional:`  | Optional value                              | `optional: nickname [type: STRING]`  |
| `import:`    | Import or dependency                        | `import: sys`                        |
| `doc:`       | Documentation summary                       | `doc: Handles user login...`         |
| `impl:`      | Full implementation in a code block         | `impl: ```python ... ``` `           |

### 3.1. Import Classification

Imports can be classified as internal (defined within the same file) or external (from libraries or other modules):

| Field     | Purpose                                   | Example Usage                      |
|-----------|-------------------------------------------|-----------------------------------|
| `type:`   | Classification as `internal` or `external`| `type: internal`                  |
| `ref:`    | Reference to internal entity definition   | `ref: class: User`                |
| `source:` | Source for external imports              | `source: stdlib` or `source: pypi` |

Examples:
```
import: User
  type: internal
  ref: class: User

import: os
  type: external
  source: stdlib
```

Grouped imports example:
```
import: os & sys & pathlib
  source: stdlib

import: numpy & pandas & sklearn
  source: external
  type: pip
```

### 3.2. Function and Method Types

Functions and methods can be assigned types to indicate special behavior:

| Type Value | Description                          | Example Usage                     |
|------------|--------------------------------------|-----------------------------------|
| `Async`    | Asynchronous function                | `func: fetch_data [type: Async]`  |
| `Generator`| Function that yields values          | `func: stream [type: Generator]`  |
| `Callback` | Function intended as a callback      | `func: on_event [type: Callback]` |

### 3.3. Complex Type Annotations

For type annotations containing special characters that might conflict with CodeStruct's own syntax:

- Wrap the type in double quotes: `[type: "List[Dict[str, Any]]"]`
- Special characters requiring quotes include: `[]|,(){}`
- This prevents parsing ambiguity while preserving the full type information

Examples:
```
param: users [type: "List[User]"]
param: config [type: "Dict[str, Any]"]
returns: "Union[str, None]"
```

### 3.4. Implementation Field

- The `impl:` field can be added to any entity (typically `func:`, `class:`, etc.) to provide the full implementation.
- The value must be a fenced code block (triple backticks) with the language specified.
- This field is for human/LLM context and **should be ignored by minifiers and parsers that compress context**.
- Example:
  ```
  func: add
    impl:
      ```python
      def add(a, b):
          return a + b
      ```
  ```

---

## 4. Example

### 4.1. Directory and Code Structure

```codestruct
dir: project_root
  dir: src
    file: main.py
      module: main
        doc: Entry point for the application...
        import: user
          type: internal
          ref: module: user
        func: main
          doc: Runs the main application logic...
          param: argv [type: LIST]
          returns: None
    file: user.py
      module: user
        class: User
          doc: Represents a user...
          attr: name [type: STRING]
          attr: age [type: INTEGER]
          func: greet
            doc: Greets the user...
            returns: STRING
            import: os
              type: external
              source: stdlib
  dir: tests
    file: test_user.py
      func: test_greet
        doc: Tests the greet function...
        returns: None
  file: README.md
```

### 4.2. Import Classification Example

```
module: user_management
  class: User
    doc: Represents a user in the system...
    attr: name [type: STRING]
    attr: age [type: INTEGER]

  func: create_user
    doc: Creates a new user...
    param: name [type: STRING]
    param: age [type: INTEGER]
    returns: User
    import: User
      type: internal
      ref: class: User

  func: get_home_directory
    doc: Returns the user's home directory...
    returns: STRING
    import: os & pathlib & sys
      type: external
      source: stdlib
```

### 4.3. Async Function Example

```
module: api_client
  func: fetch_data [type: Async]
    doc: Fetches data from the API asynchronously...
    param: endpoint [type: STRING]
    param: params [type: "Dict[str, Any]"]
    returns: "Dict[str, Any]"
    
  func: process_results
    doc: Processes the results returned from the API...
    param: data [type: "Dict[str, Any]"]
    returns: "List[Result]"
```

---

## 5. Reserved Keywords and Extensions

- Only listed keywords are reserved; users may extend with custom keywords as needed (e.g., `interface:`, `enum:`).
- Future extensions may add support for statements, decorators, or annotations.

---

## 6. Best Practices

- **Indentation:** Use 2 or 4 spaces for indentation; do not mix tabs and spaces.
- **Docstrings:** Always provide a `doc:` field for classes and functions for clarity.
- **Type Annotations:** Use `[type: ...]` for all parameters, attributes, and return values where possible.
  - Wrap complex type annotations in double quotes when they contain special characters.
- **Default Values:** Specify default values in attributes: `[default: ...]`.
- **Imports:** Use `import:` for dependencies at the file or module level.
  - Classify imports as `internal` or `external` using the `type:` field.
  - For internal imports, use `ref:` to link to the entity definition within the file.
  - For external imports, use `source:` to specify the origin (e.g., `stdlib`, `pypi`).
  - Group related imports with `&` when they share the same source or type.
- **Grouping:** Use ampersand (`&`) to group related entities that share common attributes.
  - Avoid comma-separated lists for entity names to prevent minification conflicts.

---

## 7. Hash Identifiers for Change Tracking

CodeStruct supports hash identifiers to enable efficient change tracking and comparison across versions of a codebase. This feature is implemented as an optional extension of the core notation.

### 7.1. Hash ID Format and Usage

Hash identifiers are appended to entity declarations using triple colons (`:::`) followed by a hexadecimal hash value:

```
dir: my_project ::: 56d375812962541bc30522febfa59c15
  file: math_utils.py ::: 56d375812962541bc30522febfa59c15
```

### 7.2. Merkle-Tree-Like Implementation

The hash system is implemented as a merkle-tree-like hierarchy where:

- Each entity (file, directory, module, class, etc.) has its own unique hash
- Parent entity hashes incorporate the hashes of all their children
- Any change to a child entity propagates upward, changing all parent hashes

This hierarchical structure enables efficient change detection:
1. Compare root-level hashes to quickly determine if any changes exist
2. If a change is detected, traverse the tree by comparing hashes at each level
3. Follow the path of changed hashes to precisely identify which entities were modified

### 7.3. Benefits of Hash Identifiers

- **Efficient Change Detection**: Quickly identify if and where changes occurred without full content comparison
- **Integrity Verification**: Verify that content has not been altered
- **Version Comparison**: Compare different versions of a codebase structure
- **Incremental Updates**: Support for updating only changed portions of a model or documentation

### 7.4. Implementation Notes

The hash system is an optional extension of CodeStruct. Implementations should:
- Generate hashes consistently using a deterministic algorithm (e.g., xxHash)
- Calculate file hashes based on content
- Calculate directory/module/class hashes based on name, type, and child hashes
- Normalize paths and content before hashing to ensure consistency across platforms

---

## 8. Parsing and Tooling

- CodeStruct is designed to be easily parsed by scripts or tools, enabling codebase analysis, documentation generation, and cross-language transformations.
- Parsers should ignore comments and handle missing optional fields gracefully.

---

## 9. Example with All Features

```
dir: my_project ::: 56d375812962541bc30522febfa59c15
  file: math_utils.py ::: 56d375812962541bc30522febfa59c15
    module: math_utils ::: a7c5e83bf61d49eb89f64aa3cc85121d
      doc: Math utilities module...
      import: numpy & scipy & matplotlib ::: 3e1fc985a72401d487ce4abad98e4a36
        type: external
        source: pypi
      func: add ::: 2b8a9cf7e1243f6a82f45c8b8ef28d7b
        doc: Adds two numbers...
        param: a [type: INTEGER]
        param: b [type: INTEGER]
        impl:
          ```python
            files_summary = []
            for file_path, info in file_info.items():
              extension = info.get("extension", "")
              directory = info.get("directory", "")
              module = info.get("module", "")
              summary = f"- {file_path} ({extension} file in {directory})"
              if module:
                summary += f", part of {module} module"
              files_summary.append(summary)
            return "\n".join(files_summary) if files_summary else "No file information available"
          ```
        returns: INTEGER
      func: multiply ::: 4f9a0c8d75b2461ea3e97fe72d81f5c0
        doc: Multiplies two numbers...
        param: a [type: INTEGER]
        param: b [type: INTEGER]
        returns: INTEGER
        import: add ::: 2b8a9cf7e1243f6a82f45c8b8ef28d7b
          type: internal
          ref: func: add
      const: PI ::: d3fa68c1e0584ab58e2c52e9ba187c95
        [type: FLOAT, default: 3.14159]
      func: process_data ::: 9c7412e8f6b34d80a1fc56c3d2ebf472
        doc: Processes data using numpy...
        param: data [type: "List[Dict[str, float]]"]
        returns: "numpy.ndarray"
  file: README.md ::: 1a4f5bcd78e96f201ac37985b9b67e29
```

---

## 10. Minification for LLM Context Compression

For scenarios requiring maximum context efficiency, CodeStruct can be minified while preserving its hierarchical structure and semantic information.

### 10.1. General Minification Principles

- Remove all blank lines.
- Replace indentation and line-breaks with delimiters: `;` to separate top-level entities, `|` to separate children, and `,` for attributes.
- Remove optional fields if not strictly needed.
- Use abbreviated forms for keywords (e.g., `cl:` for `class:`, `fn:` for `func:`, etc.).
- Truncate or omit docstrings where context is clear.
- Remove attribute names when the type provides sufficient context.
- **Omit all `impl:` implementation blocks from the minified output.**
- **Remove all hash identifiers (values after `:::`) during minification.**
- Include a legend/mapping to help LLMs interpret the minified format correctly.

### 10.2. Keyword Shortening Reference

| Original    | Minified |
|-------------|----------|
| dir:        | d:       |
| file:       | f:       |
| module:     | m:       |
| class:      | cl:      |
| func:       | fn:      |
| attr:       | at:      |
| param:      | p:       |
| returns:    | r:       |
| var:        | v:       |
| const:      | c:       |
| import:     | i:       |
| doc:        | dc:      |
| type:       | t:       |
| default:    | d:       |
| source:     | s:       |
| ref:        | rf:      |

### 10.3. Attribute Compression

- Inline attributes with minimal separators:  
  `attr: name [type: STRING, default: "John"]` → `at:name[t:STR,d:"John"]`
- Use standard abbreviations for common types:
  - `INTEGER` → `INT`
  - `STRING` → `STR`
  - `BOOLEAN` → `BOOL`
  - `FLOAT` → `FLT`

### 10.4. Minification Example

Original CodeStruct:
```
dir: my_project ::: 56d375812962541bc30522febfa59c15
  file: math_utils.py ::: 56d375812962541bc30522febfa59c15
    module: math_utils ::: a7c5e83bf61d49eb89f64aa3cc85121d
      doc: Math utilities module...
      import: numpy & scipy ::: 3e1fc985a72401d487ce4abad98e4a36
        type: external
        source: pypi
      func: add ::: 2b8a9cf7e1243f6a82f45c8b8ef28d7b
        doc: Adds two numbers...
        param: a [type: INTEGER]
        param: b [type: INTEGER]
        returns: INTEGER
      func: multiply ::: 4f9a0c8d75b2461ea3e97fe72d81f5c0
        doc: Multiplies two numbers...
        param: a [type: INTEGER]
        param: b [type: INTEGER]
        returns: INTEGER
        import: add ::: 2b8a9cf7e1243f6a82f45c8b8ef28d7b
          type: internal
          ref: func: add
      const: PI ::: d3fa68c1e0584ab58e2c52e9ba187c95
        [type: FLOAT, default: 3.14159]
  file: README.md ::: 1a4f5bcd78e96f201ac37985b9b67e29
```

Minified Version:
```
d:my_project;f:math_utils.py;m:math_utils;i:numpy&scipy[t:ext,s:pypi];fn:add|p:a[t:INT],p:b[t:INT],r:INT;fn:multiply|p:a[t:INT],p:b[t:INT],r:INT,i:add[t:int,rf:fn:add];c:PI[t:FLT,d:3.14159];f:README.md
```

### 10.5. Structure Legend

When using minified CodeStruct, include a legend to assist LLMs:
```
Format: Entity;Entity|Child,Child[Attribute,Attribute]
Keyword map: d=dir,f=file,m=module,cl=class,fn=func,at=attr,p=param,r=returns,v=var,c=const,i=import,t=type,s=source,rf=ref
Type map: INT=INTEGER,STR=STRING,BOOL=BOOLEAN,FLT=FLOAT,ext=external,int=internal
Delimiters: ;=entity separator, |=child separator, ,=attribute separator, &=entity grouping, []=attribute container
```