"""Parsing utilities for streaming CDN request trace files into typed records."""

from dataclasses import dataclass
from typing import Iterator
import logging


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RequestTrace:
	timestamp: int
	cachekey: str
	file_size: int


def parse_trace_file(file_path: str) -> Iterator[RequestTrace]:
	"""Yield parsed request traces from a colon-delimited trace file."""
	with open(file_path, "r", encoding="utf-8") as trace_file:
		for line_number, raw_line in enumerate(trace_file, start=1):
			if raw_line.startswith("#"):
				continue

			line = raw_line.strip()
			if not line:
				continue

			parts = line.split(":")

			try:
				timestamp = int(parts[2])
				cachekey = parts[3]
				file_size = int(parts[4])
			except (ValueError, IndexError):
				logger.debug(
					"Skipping malformed trace line %d: %r",
					line_number,
					raw_line.rstrip("\n"),
				)
				continue

			yield RequestTrace(
				timestamp=timestamp,
				cachekey=cachekey,
				file_size=file_size,
			)
