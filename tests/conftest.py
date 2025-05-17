"""Pytest configuration file."""

import sys
from pathlib import Path

from lark import logger

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.joinpath("src").resolve()))
logger.setLevel("DEBUG")
