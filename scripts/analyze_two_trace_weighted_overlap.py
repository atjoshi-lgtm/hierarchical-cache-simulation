"""Analyze weighted overlap between two traces across equal-width time buckets."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import os
from pathlib import Path
import statistics

import matplotlib.pyplot as plt

from src.simulator.data_access.parser import parse_trace_file
from src.simulator.data_access.trace_aligner import compute_overlap_window


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze request- and byte-weighted overlap between two traces over time buckets."
    )
    parser.add_argument(
        "--trace-files",
        nargs=2,
        default=[
            "data/three_edges/request_seq_edge_1",
            "data/three_edges/request_seq_edge_2",
        ],
        help="Exactly two trace files, ordered as trace_a trace_b.",
    )
    parser.add_argument(
        "--num-buckets",
        type=int,
        default=24,
        help=(
            "Target number of equal-width buckets. "
            "Actual bucket count may be lower while preserving equal width and allowing only a shorter last bucket."
        ),
    )
    parser.add_argument("--experiment-name", default="two_trace_weighted_overlap")
    parser.add_argument("--output-root", default="experiments")
    return parser.parse_args()


def setup_logging(run_dir: Path) -> logging.Logger:
    logger = logging.getLogger("analyze_two_trace_weighted_overlap")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler = logging.FileHandler(run_dir / "run.log")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def compute_bucket_ranges(start_timestamp: int, end_timestamp: int, num_buckets: int) -> list[tuple[int, int]]:
    """Build equal-width buckets with a potentially shorter last bucket.

    Width is fixed as ceil(span / num_buckets), so the generated bucket count can
    be <= requested count for some spans.
    """
    if num_buckets <= 0:
        raise ValueError("num_buckets must be a positive integer.")
    if end_timestamp < start_timestamp:
        raise ValueError("Invalid time window: end_timestamp < start_timestamp")

    span_seconds = end_timestamp - start_timestamp + 1
    bucket_width = max(1, math.ceil(span_seconds / num_buckets))
    ranges: list[tuple[int, int]] = []

    current_start = start_timestamp
    while current_start <= end_timestamp:
        current_end = min(current_start + bucket_width - 1, end_timestamp)
        ranges.append((current_start, current_end))
        current_start += bucket_width

    return ranges


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator > 0 else 0.0


def compute_weighted_overlap_metrics(
    req_a: dict[str, int],
    req_b: dict[str, int],
    bytes_a: dict[str, int],
    bytes_b: dict[str, int],
) -> dict[str, float]:
    req_total_a = float(sum(req_a.values()))
    req_total_b = float(sum(req_b.values()))
    req_common_min = 0.0

    if len(req_a) <= len(req_b):
        for key, count_a in req_a.items():
            count_b = req_b.get(key)
            if count_b is not None:
                req_common_min += min(count_a, count_b)
    else:
        for key, count_b in req_b.items():
            count_a = req_a.get(key)
            if count_a is not None:
                req_common_min += min(count_a, count_b)

    req_union_max = req_total_a + req_total_b - req_common_min

    byte_total_a = float(sum(bytes_a.values()))
    byte_total_b = float(sum(bytes_b.values()))
    byte_common_min = 0.0

    if len(bytes_a) <= len(bytes_b):
        for key, value_a in bytes_a.items():
            value_b = bytes_b.get(key)
            if value_b is not None:
                byte_common_min += min(value_a, value_b)
    else:
        for key, value_b in bytes_b.items():
            value_a = bytes_a.get(key)
            if value_a is not None:
                byte_common_min += min(value_a, value_b)

    byte_union_max = byte_total_a + byte_total_b - byte_common_min

    return {
        "req_total_a": req_total_a,
        "req_total_b": req_total_b,
        "req_common_min": req_common_min,
        "req_union_max": req_union_max,
        "req_frac_a_to_b": _safe_div(req_common_min, req_total_a),
        "req_frac_b_to_a": _safe_div(req_common_min, req_total_b),
        "req_jaccard": _safe_div(req_common_min, req_union_max),
        "byte_total_a": byte_total_a,
        "byte_total_b": byte_total_b,
        "byte_common_min": byte_common_min,
        "byte_union_max": byte_union_max,
        "byte_frac_a_to_b": _safe_div(byte_common_min, byte_total_a),
        "byte_frac_b_to_a": _safe_div(byte_common_min, byte_total_b),
        "byte_jaccard": _safe_div(byte_common_min, byte_union_max),
    }


def _bucket_index(timestamp: int, start_timestamp: int, bucket_width: int) -> int:
    return (timestamp - start_timestamp) // bucket_width


def _accumulate_trace(
    file_path: str,
    start_timestamp: int,
    end_timestamp: int,
    bucket_width: int,
    bucket_count: int,
) -> tuple[list[dict[str, int]], list[dict[str, int]], int, int]:
    req_by_bucket: list[dict[str, int]] = [dict() for _ in range(bucket_count)]
    bytes_by_bucket: list[dict[str, int]] = [dict() for _ in range(bucket_count)]
    parsed_in_window = 0
    size_mutation_events = 0
    first_seen_size: dict[str, int] = {}

    for trace in parse_trace_file(file_path):
        if trace.timestamp < start_timestamp or trace.timestamp > end_timestamp:
            continue

        parsed_in_window += 1
        idx = _bucket_index(trace.timestamp, start_timestamp, bucket_width)
        if idx >= bucket_count:
            idx = bucket_count - 1

        req_bucket = req_by_bucket[idx]
        bytes_bucket = bytes_by_bucket[idx]

        req_bucket[trace.cachekey] = req_bucket.get(trace.cachekey, 0) + 1
        bytes_bucket[trace.cachekey] = bytes_bucket.get(trace.cachekey, 0) + trace.file_size

        known_size = first_seen_size.get(trace.cachekey)
        if known_size is None:
            first_seen_size[trace.cachekey] = trace.file_size
        elif known_size != trace.file_size:
            size_mutation_events += 1

    return req_by_bucket, bytes_by_bucket, parsed_in_window, size_mutation_events


def analyze_two_traces(
    trace_a: str,
    trace_b: str,
    bucket_ranges: list[tuple[int, int]],
) -> tuple[list[dict[str, float]], dict[str, int]]:
    start_timestamp = bucket_ranges[0][0]
    end_timestamp = bucket_ranges[-1][1]
    bucket_width = bucket_ranges[0][1] - bucket_ranges[0][0] + 1
    bucket_count = len(bucket_ranges)

    req_a, bytes_a, parsed_a, mutations_a = _accumulate_trace(
        trace_a, start_timestamp, end_timestamp, bucket_width, bucket_count
    )
    req_b, bytes_b, parsed_b, mutations_b = _accumulate_trace(
        trace_b, start_timestamp, end_timestamp, bucket_width, bucket_count
    )

    rows: list[dict[str, float]] = []
    for idx, (bucket_start, bucket_end) in enumerate(bucket_ranges):
        metrics = compute_weighted_overlap_metrics(req_a[idx], req_b[idx], bytes_a[idx], bytes_b[idx])
        row = {
            "bucket_index": idx,
            "bucket_start_timestamp": bucket_start,
            "bucket_end_timestamp": bucket_end,
            "bucket_span_seconds": bucket_end - bucket_start + 1,
            **metrics,
        }
        rows.append(row)

    metadata = {
        "parsed_records_trace_a_in_window": parsed_a,
        "parsed_records_trace_b_in_window": parsed_b,
        "size_mutation_events_trace_a": mutations_a,
        "size_mutation_events_trace_b": mutations_b,
    }
    return rows, metadata


def summarize_rows(rows: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    metric_names = [
        "req_frac_a_to_b",
        "req_frac_b_to_a",
        "req_jaccard",
        "byte_frac_a_to_b",
        "byte_frac_b_to_a",
        "byte_jaccard",
        "req_total_a",
        "req_total_b",
        "byte_total_a",
        "byte_total_b",
    ]
    summary: dict[str, dict[str, float]] = {}

    for name in metric_names:
        values = [float(row[name]) for row in rows]
        if not values:
            summary[name] = {"mean": 0.0, "min": 0.0, "max": 0.0, "std": 0.0}
            continue

        summary[name] = {
            "mean": float(statistics.fmean(values)),
            "min": float(min(values)),
            "max": float(max(values)),
            "std": float(statistics.pstdev(values)),
        }

    return summary


def save_csv(rows: list[dict[str, float]], output_path: Path) -> None:
    fieldnames = [
        "bucket_index",
        "bucket_start_timestamp",
        "bucket_end_timestamp",
        "bucket_span_seconds",
        "req_total_a",
        "req_total_b",
        "req_common_min",
        "req_union_max",
        "req_frac_a_to_b",
        "req_frac_b_to_a",
        "req_jaccard",
        "byte_total_a",
        "byte_total_b",
        "byte_common_min",
        "byte_union_max",
        "byte_frac_a_to_b",
        "byte_frac_b_to_a",
        "byte_jaccard",
    ]
    with open(output_path, "w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_request_plot(rows: list[dict[str, float]], output_path: Path) -> None:
    x = [int(row["bucket_index"]) for row in rows]
    plt.figure(figsize=(10, 6))
    plt.plot(x, [row["req_frac_a_to_b"] for row in rows], marker="o", linewidth=2, label="Request A->B")
    plt.plot(x, [row["req_frac_b_to_a"] for row in rows], marker="s", linewidth=2, label="Request B->A")
    plt.plot(x, [row["req_jaccard"] for row in rows], marker="^", linewidth=2, label="Request Jaccard")
    plt.ylim(0, 1)
    plt.xlabel("Bucket Index")
    plt.ylabel("Request-Weighted Overlap")
    plt.title("Request-Weighted Overlap by Time Bucket", fontsize=12, fontweight="bold")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def save_byte_plot(rows: list[dict[str, float]], output_path: Path) -> None:
    x = [int(row["bucket_index"]) for row in rows]
    plt.figure(figsize=(10, 6))
    plt.plot(x, [row["byte_frac_a_to_b"] for row in rows], marker="o", linewidth=2, label="Byte A->B")
    plt.plot(x, [row["byte_frac_b_to_a"] for row in rows], marker="s", linewidth=2, label="Byte B->A")
    plt.plot(x, [row["byte_jaccard"] for row in rows], marker="^", linewidth=2, label="Byte Jaccard")
    plt.ylim(0, 1)
    plt.xlabel("Bucket Index")
    plt.ylabel("Byte-Weighted Overlap")
    plt.title("Byte-Weighted Overlap by Time Bucket", fontsize=12, fontweight="bold")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def save_volume_plot(rows: list[dict[str, float]], output_path: Path) -> None:
    x = [int(row["bucket_index"]) for row in rows]

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    axes[0].plot(x, [row["req_total_a"] for row in rows], marker="o", linewidth=2, label="Req Total A")
    axes[0].plot(x, [row["req_total_b"] for row in rows], marker="s", linewidth=2, label="Req Total B")
    axes[0].set_ylabel("Request Count")
    axes[0].set_title("Per-Bucket Request Volumes", fontsize=11)
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    axes[1].plot(x, [row["byte_total_a"] for row in rows], marker="o", linewidth=2, label="Byte Total A")
    axes[1].plot(x, [row["byte_total_b"] for row in rows], marker="s", linewidth=2, label="Byte Total B")
    axes[1].set_xlabel("Bucket Index")
    axes[1].set_ylabel("Requested Bytes")
    axes[1].set_title("Per-Bucket Byte Volumes", fontsize=11)
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    overlap = compute_overlap_window(args.trace_files)
    bucket_ranges = compute_bucket_ranges(
        overlap.start_timestamp,
        overlap.end_timestamp,
        args.num_buckets,
    )

    trace_names = [Path(path).name for path in args.trace_files]
    run_dir = Path(args.output_root) / args.experiment_name / (
        f"trace_{trace_names[0]}_{trace_names[1]}_buckets_{len(bucket_ranges)}"
    )
    os.makedirs(run_dir, exist_ok=True)
    logger = setup_logging(run_dir)

    logger.info("Starting two-trace weighted overlap analysis")
    logger.info("Trace files: %s", ", ".join(args.trace_files))
    logger.info(
        "Pairwise overlap window [start,end]=[%d,%d]",
        overlap.start_timestamp,
        overlap.end_timestamp,
    )
    logger.info("Requested buckets: %d", args.num_buckets)
    logger.info("Actual equal-width buckets: %d", len(bucket_ranges))
    logger.info("Bucket width seconds: %d", bucket_ranges[0][1] - bucket_ranges[0][0] + 1)

    rows, analysis_metadata = analyze_two_traces(
        trace_a=args.trace_files[0],
        trace_b=args.trace_files[1],
        bucket_ranges=bucket_ranges,
    )
    summary = summarize_rows(rows)

    config = {
        "trace_files": args.trace_files,
        "num_buckets_requested": args.num_buckets,
        "num_buckets_actual": len(bucket_ranges),
        "bucket_width_seconds": bucket_ranges[0][1] - bucket_ranges[0][0] + 1,
        "experiment_name": args.experiment_name,
        "output_root": args.output_root,
        "overlap_start_timestamp": overlap.start_timestamp,
        "overlap_end_timestamp": overlap.end_timestamp,
        "trace_bounds": [
            {
                "file_path": item.file_path,
                "min_timestamp": item.min_timestamp,
                "max_timestamp": item.max_timestamp,
                "parsed_records": item.parsed_records,
                "skipped_records": item.skipped_records,
            }
            for item in overlap.trace_bounds
        ],
        "analysis_metadata": analysis_metadata,
    }
    with open(run_dir / "config_used.json", "w", encoding="utf-8") as config_file:
        json.dump(config, config_file, indent=2)

    base_name = f"weighted_overlap_{trace_names[0]}_{trace_names[1]}"
    csv_path = run_dir / f"{base_name}.csv"
    rows_json_path = run_dir / f"{base_name}.json"
    summary_json_path = run_dir / f"{base_name}_summary.json"
    request_plot_path = run_dir / f"{base_name}_request.png"
    byte_plot_path = run_dir / f"{base_name}_byte.png"
    volume_plot_path = run_dir / f"{base_name}_volume.png"

    save_csv(rows, csv_path)
    with open(rows_json_path, "w", encoding="utf-8") as rows_json_file:
        json.dump(rows, rows_json_file, indent=2)
    with open(summary_json_path, "w", encoding="utf-8") as summary_json_file:
        json.dump(summary, summary_json_file, indent=2)
    save_request_plot(rows, request_plot_path)
    save_byte_plot(rows, byte_plot_path)
    save_volume_plot(rows, volume_plot_path)

    logger.info("Saved raw CSV: %s", csv_path)
    logger.info("Saved raw JSON: %s", rows_json_path)
    logger.info("Saved summary JSON: %s", summary_json_path)
    logger.info("Saved request overlap plot: %s", request_plot_path)
    logger.info("Saved byte overlap plot: %s", byte_plot_path)
    logger.info("Saved volume plot: %s", volume_plot_path)


if __name__ == "__main__":
    main()
