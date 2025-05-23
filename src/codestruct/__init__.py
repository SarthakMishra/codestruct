"""CodeStruct: A plain-text notation for describing software structure."""

from importlib.metadata import PackageNotFoundError, version

try:
	__version__ = version("codestruct")
except PackageNotFoundError:
	__version__ = "unknown"

from .formatter import CodeStructFormatter
from .linter import CodeStructLinter, LintMessage
from .minifier import CodeStructMinifier
from .parser import CodeStructParser, ParseError
from .transformer import CodeStructTransformer

__all__ = [
	"CodeStructFormatter",
	"CodeStructLinter",
	"CodeStructMinifier",
	"CodeStructParser",
	"CodeStructTransformer",
	"LintMessage",
	"ParseError",
	"__version__",
]
