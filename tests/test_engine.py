from pathlib import Path

from src.simulator.data_access.trace_aligner import merge_aligned_traces
from src.simulator.engine.multi_edge_orchestrator import MultiEdgeSimulationEngine
from src.simulator.models.lru_cache import ByteAwareLRUCache


def _make_trace_line(timestamp: int, cachekey: str, file_size: int) -> str:
    return (
        f"map:serial:{timestamp}:{cachekey}:{file_size}:bytes:cp:status:arlid:net:"
        "mapname:region:vcd:product\n"
    )


def _write_trace(path: Path, events: list[tuple[int, str, int]]) -> str:
    with open(path, "w", encoding="utf-8") as trace_file:
        for timestamp, cachekey, file_size in events:
            trace_file.write(_make_trace_line(timestamp, cachekey, file_size))
    return str(path)


def test_multi_edge_engine_shared_parent_hits(tmp_path: Path) -> None:
    edge_1 = _write_trace(tmp_path / "edge_1", [(1, "A", 10)])
    edge_2 = _write_trace(tmp_path / "edge_2", [(2, "A", 10)])
    edge_3 = _write_trace(tmp_path / "edge_3", [(3, "B", 20)])

    merged = merge_aligned_traces([edge_1, edge_2, edge_3], 1, 3)
    engine = MultiEdgeSimulationEngine(
        edge_caches={1: ByteAwareLRUCache(100), 2: ByteAwareLRUCache(100), 3: ByteAwareLRUCache(100)},
        parent_cache=ByteAwareLRUCache(100),
        merged_requests=merged,
    )

    metrics = engine.run()

    assert metrics["total_requests"] == 3
    assert metrics["parent_hits"] == 1
    assert metrics["parent_misses"] == 2
    assert metrics["parent_hit_rate"] == 1 / 3
    assert metrics["edge_1_misses"] == 1
    assert metrics["edge_2_misses"] == 1
    assert metrics["edge_3_misses"] == 1
    assert metrics["edge_1_parent_hits"] == 0
    assert metrics["edge_1_parent_misses"] == 1
    assert metrics["edge_1_parent_hit_rate"] == 0.0
    assert metrics["edge_2_parent_hits"] == 1
    assert metrics["edge_2_parent_misses"] == 0
    assert metrics["edge_2_parent_hit_rate"] == 1.0
    assert metrics["edge_3_parent_hits"] == 0
    assert metrics["edge_3_parent_misses"] == 1
    assert metrics["edge_3_parent_hit_rate"] == 0.0
    assert metrics["duplication_overlap_union_bytes"] == 30
    assert metrics["duplication_byte_rate"] == 1.0


def test_multi_edge_tiebreak_is_deterministic(tmp_path: Path) -> None:
    edge_1 = _write_trace(tmp_path / "edge_1", [(1, "A", 10)])
    edge_2 = _write_trace(tmp_path / "edge_2", [(1, "B", 10)])
    edge_3 = _write_trace(tmp_path / "edge_3", [(1, "A", 10)])

    merged = merge_aligned_traces([edge_1, edge_2, edge_3], 1, 1)
    engine = MultiEdgeSimulationEngine(
        edge_caches={1: ByteAwareLRUCache(100), 2: ByteAwareLRUCache(100), 3: ByteAwareLRUCache(100)},
        parent_cache=ByteAwareLRUCache(10),
        merged_requests=merged,
    )

    metrics = engine.run()

    assert metrics["total_requests"] == 3
    assert metrics["parent_hits"] == 0
    assert metrics["parent_misses"] == 3
    assert metrics["parent_hit_rate"] == 0.0
