from pathlib import Path

import pytest

from src.simulator.data_access.trace_aligner import (
    compute_overlap_window,
    merge_aligned_traces,
    parse_trace_file_within_window,
)


def _make_trace_line(timestamp: int, cachekey: str, file_size: int) -> str:
    return (
        f"map:serial:{timestamp}:{cachekey}:{file_size}:bytes:cp:status:arlid:net:"
        "mapname:region:vcd:product\n"
    )


def _write_trace(path: Path, events: list[tuple[int, str, int]], malformed: bool = False) -> str:
    with open(path, "w", encoding="utf-8") as trace_file:
        trace_file.write("# metadata\n")
        for timestamp, cachekey, file_size in events:
            trace_file.write(_make_trace_line(timestamp, cachekey, file_size))
        if malformed:
            trace_file.write("bad:line\n")
    return str(path)


def test_compute_overlap_window_success(tmp_path: Path) -> None:
    edge_1 = _write_trace(tmp_path / "edge_1", [(100, "a", 10), (200, "b", 11)])
    edge_2 = _write_trace(tmp_path / "edge_2", [(150, "c", 12), (160, "d", 13)])
    edge_3 = _write_trace(tmp_path / "edge_3", [(120, "e", 14), (180, "f", 15)], malformed=True)

    overlap = compute_overlap_window([edge_1, edge_2, edge_3])

    assert overlap.start_timestamp == 150
    assert overlap.end_timestamp == 160
    assert len(overlap.trace_bounds) == 3
    assert overlap.trace_bounds[2].skipped_records == 1


def test_compute_overlap_window_no_shared_range(tmp_path: Path) -> None:
    edge_1 = _write_trace(tmp_path / "edge_1", [(1, "a", 10), (5, "b", 10)])
    edge_2 = _write_trace(tmp_path / "edge_2", [(8, "c", 10), (10, "d", 10)])
    edge_3 = _write_trace(tmp_path / "edge_3", [(11, "e", 10), (12, "f", 10)])

    with pytest.raises(ValueError, match="No shared overlap window"):
        compute_overlap_window([edge_1, edge_2, edge_3])


def test_parse_trace_file_within_window_is_inclusive(tmp_path: Path) -> None:
    trace = _write_trace(
        tmp_path / "edge_1",
        [(99, "pre", 1), (100, "start", 2), (150, "middle", 3), (200, "end", 4), (201, "post", 5)],
    )

    rows = list(parse_trace_file_within_window(trace, 100, 200))

    assert [row.timestamp for row in rows] == [100, 150, 200]
    assert [row.cachekey for row in rows] == ["start", "middle", "end"]


def test_merge_aligned_traces_ordering_and_tiebreak(tmp_path: Path) -> None:
    edge_1 = _write_trace(tmp_path / "edge_1", [(100, "a", 1), (101, "b", 1)])
    edge_2 = _write_trace(tmp_path / "edge_2", [(100, "c", 1), (102, "d", 1)])
    edge_3 = _write_trace(tmp_path / "edge_3", [(100, "e", 1), (103, "f", 1)])

    merged = list(merge_aligned_traces([edge_1, edge_2, edge_3], 100, 103))

    assert [(edge_id, row.cachekey) for edge_id, row in merged[:3]] == [
        (1, "a"),
        (2, "c"),
        (3, "e"),
    ]
    assert [row.timestamp for _, row in merged] == [100, 100, 100, 101, 102, 103]
