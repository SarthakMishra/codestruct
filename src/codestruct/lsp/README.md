# CodeStruct Language Server

A Language Server Protocol (LSP) implementation for CodeStruct notation files, providing rich IDE features like syntax highlighting, code completion, diagnostics, formatting, and more.

## Features

The CodeStruct Language Server provides the following LSP features:

### 📋 Diagnostics (Linting)
- Real-time syntax error detection
- Style and convention checking
- Missing documentation warnings
- Attribute naming validation
- Hash ID format validation

### 🎯 Code Completion
- Entity keyword completion (`module:`, `class:`, `func:`, etc.)
- Attribute key completion (`type:`, `visibility:`, `default:`, etc.)
- Context-aware attribute value suggestions
- Smart completions based on current context

### 🔍 Hover Information
- Entity keyword documentation
- Attribute key explanations
- Type information display
- Entity definition lookup
- Rich markdown formatting

### 📖 Document Symbols
- Document outline view
- Hierarchical structure navigation
- Symbol kind mapping (module, class, function, etc.)
- Quick navigation to entities

### ✨ Code Actions
- Quick fixes for common issues
- Automatic documentation generation
- Entity name expansion suggestions
- Hash ID format fixes
- Attribute naming corrections
- Code template insertions

### 🎨 Formatting
- Automatic indentation correction
- Consistent style application
- Document-wide formatting
- Range formatting support

## Installation

### As a Python Package

```bash
# Install the codestruct package
pip install codestruct

# The language server is available as:
python -m codestruct.lsp
```

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/codestruct.git
cd codestruct

# Install dependencies
pip install -e .

# Run the language server
python -m codestruct.lsp
```

## Usage

### Command Line

```bash
# Start the language server on stdio (default)
python -m codestruct.lsp

# Start on TCP for debugging
python -m codestruct.lsp --tcp --port 2087

# Enable debug logging
python -m codestruct.lsp --debug
```

### VS Code Integration

1. Install the CodeStruct extension (when available)
2. Or configure manually in `settings.json`:

```json
{
  "codestruct.server.enabled": true,
  "codestruct.server.path": "python -m codestruct.lsp",
  "codestruct.linting.enabled": true,
  "codestruct.formatting.enabled": true,
  "codestruct.completion.enabled": true
}
```

### Vim/Neovim with COC

```json
{
  "languageserver": {
    "codestruct": {
      "command": "python",
      "args": ["-m", "codestruct.lsp"],
      "filetypes": ["codestruct"],
      "rootPatterns": ["*.cst", ".git"]
    }
  }
}
```

### Emacs with LSP Mode

```elisp
(use-package lsp-mode
  :config
  (add-to-list 'lsp-language-id-configuration '(codestruct-mode . "codestruct"))
  (lsp-register-client
   (make-lsp-client :new-connection (lsp-stdio-connection "python -m codestruct.lsp")
                    :major-modes '(codestruct-mode)
                    :server-id 'codestruct)))
```

## Configuration

The language server can be configured through LSP client settings:

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `codestruct.server.enabled` | boolean | `true` | Enable the language server |
| `codestruct.linting.enabled` | boolean | `true` | Enable linting diagnostics |
| `codestruct.formatting.enabled` | boolean | `true` | Enable document formatting |
| `codestruct.completion.enabled` | boolean | `true` | Enable code completion |

## Error Codes

The linter provides the following diagnostic codes:

| Code | Category | Description |
|------|----------|-------------|
| CS001 | Parse | Parse error in CodeStruct file |
| CS002 | File | File not found |
| CS003 | File | Permission denied |
| CS004 | File | Unicode decode error |
| CS005 | File | OS error |
| CS101 | Naming | Entity name is too short |
| CS201 | Documentation | Missing documentation |
| CS301 | Hash | Hash ID format violation |
| CS401 | Attributes | Attribute naming convention violation |

## Development

### Architecture

The language server is built using [pygls](https://github.com/openlawlibrary/pygls) and integrates with existing CodeStruct components:

- **Parser**: `codestruct.parser` - Parses CodeStruct notation
- **Linter**: `codestruct.linter` - Provides diagnostics
- **Formatter**: `codestruct.formatter` - Formats documents
- **Transformer**: `codestruct.transformer` - Transforms parse trees

### Feature Implementation

Features are organized in the `features/` directory:

- `diagnostics.py` - Linting and error reporting
- `completion.py` - Code completion suggestions
- `hover.py` - Hover information
- `document_symbols.py` - Document outline
- `code_actions.py` - Quick fixes and refactoring
- `formatting.py` - Document formatting

### Testing

```bash
# Run the language server tests
pytest tests/test_lsp/

# Test with a real client
python -m codestruct.lsp --tcp --port 2087
```

### Adding New Features

1. Create a new feature module in `features/`
2. Implement the LSP method handler
3. Register the feature in `server.py`
4. Add tests for the new feature

Example:

```python
# features/new_feature.py
from lsprotocol import types as lsp
from pygls.server import LanguageServer

def handle_new_feature(server: LanguageServer, params: lsp.SomeParams) -> lsp.SomeResult:
    """Handle new LSP feature."""
    # Implementation here
    pass

# server.py
from .features import new_feature

class CodeStructLanguageServer(LanguageServer):
    def _setup_features(self):
        # Add new feature registration
        self.feature(lsp.SOME_LSP_METHOD)(new_feature.handle_new_feature)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 