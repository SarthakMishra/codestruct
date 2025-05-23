"""Main entry point for CodeStruct Language Server."""

import argparse
import logging
import sys
import tempfile
from pathlib import Path

from .server import create_server, main


def setup_logging(level: int = logging.INFO) -> None:
	"""Setup logging configuration."""
	# Use a more secure temporary directory approach
	log_dir = Path(tempfile.gettempdir()) / "codestruct"
	log_dir.mkdir(exist_ok=True)
	log_file = log_dir / "codestruct-lsp.log"

	logging.basicConfig(
		level=level,
		format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
		handlers=[
			logging.FileHandler(log_file),
			logging.StreamHandler(sys.stderr),
		],
	)


def parse_args() -> argparse.Namespace:
	"""Parse command line arguments."""
	parser = argparse.ArgumentParser(description="CodeStruct Language Server")
	parser.add_argument(
		"--tcp",
		action="store_true",
		help="Use TCP server instead of stdio",
	)
	parser.add_argument(
		"--host",
		default="localhost",
		help="TCP host (default: localhost)",
	)
	parser.add_argument(
		"--port",
		type=int,
		default=2087,
		help="TCP port (default: 2087)",
	)
	parser.add_argument(
		"--debug",
		action="store_true",
		help="Enable debug logging",
	)
	return parser.parse_args()


if __name__ == "__main__":
	args = parse_args()

	# Setup logging
	log_level = logging.DEBUG if args.debug else logging.INFO
	setup_logging(log_level)

	logger = logging.getLogger(__name__)
	logger.info("Starting CodeStruct Language Server")

	if args.tcp:
		logger.info(f"Starting TCP server on {args.host}:{args.port}")
		server = create_server()
		server.start_tcp(args.host, args.port)
	else:
		logger.info("Starting stdio server")
		main()
