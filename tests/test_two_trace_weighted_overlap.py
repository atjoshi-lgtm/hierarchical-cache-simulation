from scripts.analyze_two_trace_weighted_overlap import (
    compute_bucket_ranges,
    compute_weighted_overlap_metrics,
)


def test_compute_weighted_overlap_metrics_basic() -> None:
    req_a = {"a": 3, "b": 1}
    req_b = {"a": 2, "c": 5}
    bytes_a = {"a": 300, "b": 100}
    bytes_b = {"a": 200, "c": 500}

    metrics = compute_weighted_overlap_metrics(req_a, req_b, bytes_a, bytes_b)

    assert metrics["req_common_min"] == 2.0
    assert metrics["req_total_a"] == 4.0
    assert metrics["req_total_b"] == 7.0
    assert metrics["req_frac_a_to_b"] == 0.5
    assert metrics["req_frac_b_to_a"] == 2.0 / 7.0
    assert metrics["req_jaccard"] == 2.0 / 9.0

    assert metrics["byte_common_min"] == 200.0
    assert metrics["byte_total_a"] == 400.0
    assert metrics["byte_total_b"] == 700.0
    assert metrics["byte_frac_a_to_b"] == 0.5
    assert metrics["byte_frac_b_to_a"] == 2.0 / 7.0
    assert metrics["byte_jaccard"] == 2.0 / 9.0


def test_compute_weighted_overlap_metrics_zero_denominator() -> None:
    metrics = compute_weighted_overlap_metrics({}, {}, {}, {})

    assert metrics["req_frac_a_to_b"] == 0.0
    assert metrics["req_frac_b_to_a"] == 0.0
    assert metrics["req_jaccard"] == 0.0
    assert metrics["byte_frac_a_to_b"] == 0.0
    assert metrics["byte_frac_b_to_a"] == 0.0
    assert metrics["byte_jaccard"] == 0.0


def test_compute_bucket_ranges_equal_width_with_short_last() -> None:
    # Span is 10 seconds [0,9], requested buckets is 3.
    # Equal width uses ceil(10/3)=4 -> [0,3], [4,7], [8,9].
    buckets = compute_bucket_ranges(0, 9, 3)

    assert buckets == [(0, 3), (4, 7), (8, 9)]


def test_compute_bucket_ranges_positive_validation() -> None:
    try:
        compute_bucket_ranges(0, 9, 0)
    except ValueError as exc:
        assert "positive integer" in str(exc)
    else:
        assert False, "Expected ValueError for non-positive num_buckets"