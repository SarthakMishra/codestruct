# CodeStruct CLI

The CodeStruct CLI provides tools for linting, formatting, and minifying CodeStruct files.

## Installation

Install CodeStruct with the CLI:

```bash
pip install codestruct
```

## Usage

The CLI provides several commands organized into subcommands:

```bash
codestruct --help
```

### Main Commands

- `codestruct lint` - Lint CodeStruct files for issues
- `codestruct format` - Format and auto-fix CodeStruct files  
- `codestruct minify` - Minify CodeStruct files for LLM context compression
- `codestruct version` - Show version information
- `codestruct info` - Show information about CodeStruct components

## Linting

### Check files for issues

```bash
# Lint single file
codestruct lint check example.cst

# Lint multiple files
codestruct lint check src/**/*.cst

# Output as JSON
codestruct lint check --format json example.cst

# Filter by error codes
codestruct lint check --filter CS101,CS201 example.cst

# Show statistics
codestruct lint check --stats example.cst

# Don't exit with error code
codestruct lint check --no-exit-code example.cst
```

### Show available error codes

```bash
codestruct lint codes
```

## Formatting

### Format files

```bash
# Format and show output (doesn't modify files)
codestruct format fix example.cst

# Format files in place
codestruct format fix --in-place example.cst

# Format with 4-space indentation
codestruct format fix --indent 4 --in-place example.cst

# Show diff of changes
codestruct format fix --diff example.cst

# Check if files need formatting
codestruct format fix --check example.cst

# Disable auto-documentation
codestruct format fix --no-auto-docs --in-place example.cst

# Create backups when modifying in place
codestruct format fix --in-place --backup example.cst
```

### Check formatting

```bash
# Check if files are properly formatted
codestruct format check example.cst

# Check with 4-space indentation
codestruct format check --indent 4 example.cst
```

## Minification

### Compress files

```bash
# Minify to stdout
codestruct minify compress example.cst

# Minify to specific file
codestruct minify compress --output example.min.cst example.cst

# Minify multiple files
codestruct minify compress src/**/*.cst

# Minify without legend
codestruct minify compress --no-legend example.cst

# Show compression statistics
codestruct minify compress --stats example.cst

# Overwrite existing files
codestruct minify compress --overwrite example.cst
```

### Analyze compression

```bash
# Analyze potential compression
codestruct minify analyze example.cst

# Show detailed mappings
codestruct minify analyze --mappings example.cst
```

### Show minification legend

```bash
codestruct minify legend
```

## Examples

### Complete workflow

```bash
# 1. Lint files
codestruct lint check src/**/*.cst

# 2. Format files
codestruct format fix --in-place --backup src/**/*.cst

# 3. Verify formatting
codestruct format check src/**/*.cst

# 4. Minify for LLM context
codestruct minify compress --output compressed.min.cst src/**/*.cst
```

### CI/CD Integration

```bash
# Check formatting in CI
codestruct format check src/**/*.cst

# Lint with specific error codes
codestruct lint check --filter CS101,CS201 --exit-code src/**/*.cst

# Generate minified version for deployment
codestruct minify compress --no-legend --output dist/structure.min.cst src/**/*.cst
```

## Error Codes

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

## Configuration

The CLI tools use sensible defaults but can be configured:

- **Indentation**: 2 or 4 spaces (default: 2)
- **Auto-documentation**: Automatically add placeholder docs (default: true)
- **Auto-fix**: Apply automatic fixes during formatting (default: true)
- **Legend**: Include legend in minified output (default: true)

## Development

Run the CLI during development:

```bash
# Run as module
python -m codestruct.cli --help

# Run specific commands
python -m codestruct.cli lint check example.cst
python -m codestruct.cli format fix --in-place example.cst
python -m codestruct.cli minify compress example.cst
``` 