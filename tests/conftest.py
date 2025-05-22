"""Pytest configuration file."""

from pathlib import Path

import pytest
from lark import logger

from codestruct.parser import CodeStructParser
from codestruct.transformer import CodeStructTransformer

logger.setLevel("DEBUG")

# Define paths to test files
BASE_TEST_PATH = Path(__file__).parent
TEST_CASES_PATH = BASE_TEST_PATH / "test_cases"
SIMPLE_CSTXT_PATH = TEST_CASES_PATH / "simple.cst"
COMPLEX_CSTXT_PATH = TEST_CASES_PATH / "complex.cst"
EDGE_CASES_CSTXT_PATH = TEST_CASES_PATH / "edge_cases.cst"

VALID_CSTXT_FILES = [SIMPLE_CSTXT_PATH, COMPLEX_CSTXT_PATH, EDGE_CASES_CSTXT_PATH]
VALID_CSTXT_CONTENTS_AND_NAMES = [
	(SIMPLE_CSTXT_PATH.read_text(), "simple.cst"),
	(COMPLEX_CSTXT_PATH.read_text(), "complex.cst"),
	(EDGE_CASES_CSTXT_PATH.read_text(), "edge_cases.cst"),
]


@pytest.fixture(scope="module")
def parser():
	"""Return a CodeStructParser instance."""
	return CodeStructParser()


@pytest.fixture(scope="module")
def transformer():
	"""Return a CodeStructTransformer instance."""
	return CodeStructTransformer()


@pytest.fixture(params=[p.read_text() for p in VALID_CSTXT_FILES], ids=[p.name for p in VALID_CSTXT_FILES])
def valid_cstxt_content(request):
	"""Provide content from each valid .cstxt file."""
	return request.param
