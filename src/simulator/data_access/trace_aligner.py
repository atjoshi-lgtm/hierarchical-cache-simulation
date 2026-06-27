"""Helpers for aligning multiple edge traces to a shared wall-clock window."""

from __future__ import annotations

from dataclasses import dataclass
import heapq
from typing import Iterator, Sequence

from src.simulator.data_access.parser import RequestTrace, parse_trace_file


@dataclass(slots=True)
class TraceBounds:
    file_path: str
    min_timestamp: int
    max_timestamp: int
    parsed_records: int
    skipped_records: int


@dataclass(slots=True)
class OverlapWindow:
    start_timestamp: int
    end_timestamp: int
    trace_bounds: list[TraceBounds]


def _scan_trace_bounds(file_path: str) -> TraceBounds:
    """Read a trace once to extract min/max timestamp and basic quality counters."""
    min_timestamp: int | None = None
    max_timestamp: int | None = None
    parsed_records = 0
    skipped_records = 0

    with open(file_path, "r", encoding="utf-8") as trace_file:
        for raw_line in trace_file:
            if raw_line.startswith("#"):
                continue

            line = raw_line.strip()
            if not line:
                continue

            parts = line.split(":")
            try:
                timestamp = int(parts[2])
            except (ValueError, IndexError):
                skipped_records += 1
                continue

            parsed_records += 1
            if min_timestamp is None or timestamp < min_timestamp:
                min_timestamp = timestamp
            if max_timestamp is None or timestamp > max_timestamp:
                max_timestamp = timestamp

    if parsed_records == 0 or min_timestamp is None or max_timestamp is None:
        raise ValueError(f"Trace file has no valid records: {file_path}")

    return TraceBounds(
        file_path=file_path,
        min_timestamp=min_timestamp,
        max_timestamp=max_timestamp,
        parsed_records=parsed_records,
        skipped_records=skipped_records,
    )


def compute_overlap_window(trace_files: Sequence[str]) -> OverlapWindow:
    """Compute the strict shared inclusive [start, end] timestamp window."""
    if not trace_files:
        raise ValueError("At least one trace file is required.")

    bounds = [_scan_trace_bounds(trace_file) for trace_file in trace_files]
    start_timestamp = max(item.min_timestamp for item in bounds)
    end_timestamp = min(item.max_timestamp for item in bounds)

    if start_timestamp > end_timestamp:
        details = ", ".join(
            f"{item.file_path}[{item.min_timestamp},{item.max_timestamp}]" for item in bounds
        )
        raise ValueError(
            "No shared overlap window across traces. "
            f"Computed ranges: {details}"
        )

    return OverlapWindow(
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        trace_bounds=bounds,
    )


def parse_trace_file_within_window(
    file_path: str,
    start_timestamp: int,
    end_timestamp: int,
) -> Iterator[RequestTrace]:
    """Yield only records whose timestamp lies in the inclusive shared window."""
    for record in parse_trace_file(file_path):
        if record.timestamp < start_timestamp:
            continue
        if record.timestamp > end_timestamp:
            continue

        yield record


def merge_aligned_traces(
    trace_files: Sequence[str],
    start_timestamp: int,
    end_timestamp: int,
    assume_sorted: bool = False,
) -> Iterator[tuple[int, RequestTrace]]:
    """Merge filtered traces in timestamp order with deterministic edge ties.

    When assume_sorted=False, this performs a deterministic in-memory sort of all
    in-window records. This is correct for unsorted traces but can be memory heavy
    on very large windows.
    """
    if not trace_files:
        return

    if not assume_sorted:
        all_records: list[tuple[int, int, int, RequestTrace]] = []
        for edge_id, path in enumerate(trace_files, start=1):
            for sequence_id, record in enumerate(
                parse_trace_file_within_window(path, start_timestamp, end_timestamp)
            ):
                all_records.append((record.timestamp, edge_id, sequence_id, record))

        all_records.sort(key=lambda item: (item[0], item[1], item[2]))
        for _, edge_id, _, record in all_records:
            yield edge_id, record
        return

    iterators: dict[int, Iterator[RequestTrace]] = {
        edge_id: parse_trace_file_within_window(path, start_timestamp, end_timestamp)
        for edge_id, path in enumerate(trace_files, start=1)
    }

    heap: list[tuple[int, int, RequestTrace]] = []
    for edge_id, iterator in iterators.items():
        try:
            first = next(iterator)
        except StopIteration:
            continue
        heapq.heappush(heap, (first.timestamp, edge_id, first))

    while heap:
        _, edge_id, record = heapq.heappop(heap)
        yield edge_id, record

        iterator = iterators[edge_id]
        try:
            nxt = next(iterator)
        except StopIteration:
            continue

        heapq.heappush(heap, (nxt.timestamp, edge_id, nxt))
