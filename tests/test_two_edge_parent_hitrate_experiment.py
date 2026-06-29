from scripts.two_edge_parent_hitrate_experiment import build_row, parse_edge_sizes


def test_parse_edge_sizes() -> None:
    assert parse_edge_sizes("6, 12,24") == [6, 12, 24]


def test_build_row_includes_parent_stream_rates() -> None:
    metrics = {
        "total_requests": 10,
        "edge_hits": 4,
        "edge_misses": 6,
        "edge_1_hits": 1,
        "edge_1_misses": 3,
        "edge_2_hits": 3,
        "edge_2_misses": 3,
        "parent_hits": 2,
        "parent_misses": 4,
        "parent_hit_rate": 2 / 6,
        "edge_1_parent_hits": 1,
        "edge_1_parent_misses": 2,
        "edge_1_parent_hit_rate": 1 / 3,
        "edge_2_parent_hits": 1,
        "edge_2_parent_misses": 2,
        "edge_2_parent_hit_rate": 1 / 3,
        "duplication_byte_rate": 0.25,
    }

    row = build_row(edge_1_gb=12, edge_2_gb=24, parent_gb=120, metrics=metrics)

    assert row["edge_1_gb"] == 12
    assert row["edge_2_gb"] == 24
    assert row["parent_gb"] == 120
    assert row["parent_hit_rate"] == 2 / 6
    assert row["edge_1_parent_hit_rate"] == 1 / 3
    assert row["edge_2_parent_hit_rate"] == 1 / 3
    assert row["global_hit_rate"] == 0.6