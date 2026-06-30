from scripts.two_edge_parent_sweep_experiment import build_row, parse_parent_sizes


def test_parse_parent_sizes() -> None:
    assert parse_parent_sizes("12, 24,48") == [12, 24, 48]


def test_build_row_includes_parent_sweep_rates() -> None:
    metrics = {
        "total_requests": 10,
        "edge_hits": 4,
        "edge_misses": 6,
        "edge_1_total_requests": 4,
        "edge_1_hits": 1,
        "edge_1_misses": 3,
        "edge_2_total_requests": 6,
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
        "edge_1_duplication_byte_rate": 0.1,
        "edge_2_duplication_byte_rate": 0.2,
    }

    row = build_row(parent_gb=48, edge_1_gb=12, edge_2_gb=24, metrics=metrics)

    assert row["parent_gb"] == 48
    assert row["edge_1_gb"] == 12
    assert row["edge_2_gb"] == 24
    assert row["edge_1_total_requests"] == 4
    assert row["edge_2_total_requests"] == 6
    assert row["edge_1_hit_rate"] == 1 / 4
    assert row["edge_2_hit_rate"] == 3 / 6
    assert row["parent_hit_rate"] == 2 / 6
    assert row["edge_1_parent_hit_rate"] == 1 / 3
    assert row["edge_2_parent_hit_rate"] == 1 / 3
    assert row["edge_1_global_hit_rate"] == 2 / 4
    assert row["edge_2_global_hit_rate"] == 4 / 6
    assert row["global_hit_rate"] == 0.6
    assert row["duplication_byte_rate"] == 0.25
    assert row["edge_1_duplication_byte_rate"] == 0.1
    assert row["edge_2_duplication_byte_rate"] == 0.2