"""Analyze trace statistics and save popularity-distribution artifacts."""

import argparse
import csv
import json
import logging
import os
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from src.simulator.data_access.parser import parse_trace_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze CDN request trace and save artifacts.")
    parser.add_argument("--trace-file", default="data/request_seq_small")
    parser.add_argument("--experiment-name", default="trace_analysis")
    parser.add_argument("--output-root", default="experiments")
    return parser.parse_args()


def setup_logging(run_dir: Path) -> logging.Logger:
    logger = logging.getLogger("analyze_trace")
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


def main() -> None:
    args = parse_args()
    trace_name = Path(args.trace_file).name
    run_dir = Path(args.output_root) / args.experiment_name / f"trace_{trace_name}"
    os.makedirs(run_dir, exist_ok=True)
    logger = setup_logging(run_dir)

    config = {
        "trace_file": args.trace_file,
        "experiment_name": args.experiment_name,
        "output_root": args.output_root,
    }
    with open(run_dir / "config_used.json", "w", encoding="utf-8") as config_file:
        json.dump(config, config_file, indent=2)

    total_requests = 0
    total_bytes_requested = 0
    min_ts = float("inf")
    max_ts = 0
    unique_objects: dict[str, int] = {}
    sizes_list: list[int] = []
    request_counts = Counter()

    logger.info("Parsing trace file: %s", args.trace_file)
    for trace in parse_trace_file(args.trace_file):
        total_requests += 1
        total_bytes_requested += trace.file_size
        min_ts = min(min_ts, trace.timestamp)
        max_ts = max(max_ts, trace.timestamp)

        if trace.cachekey not in unique_objects:
            sizes_list.append(trace.file_size)
        unique_objects[trace.cachekey] = trace.file_size
        request_counts[trace.cachekey] += 1

    wall_clock_seconds = max_ts - min_ts
    working_set_bytes = sum(unique_objects.values())
    min_size = min(sizes_list)
    max_size = max(sizes_list)
    avg_size = float(np.mean(sizes_list))

    summary = {
        "total_requests": total_requests,
        "total_bytes_requested": total_bytes_requested,
        "unique_objects": len(unique_objects),
        "wall_clock_seconds": wall_clock_seconds,
        "working_set_bytes": working_set_bytes,
        "min_object_size": min_size,
        "max_object_size": max_size,
        "avg_object_size": avg_size,
    }

    logger.info("Summary: %s", json.dumps(summary, sort_keys=True))

    frequencies = sorted(request_counts.values(), reverse=True)
    ranks = np.arange(1, len(frequencies) + 1)

    # Sort objects by request frequency and accumulate object bytes to build
    # request coverage as a function of byte budget (top-k bytes).
    popularity_rows = sorted(
        ((cachekey, freq, unique_objects[cachekey]) for cachekey, freq in request_counts.items()),
        key=lambda row: row[1],
        reverse=True,
    )
    cumulative_bytes = 0
    cumulative_requests = 0
    weighted_rows: list[tuple[int, int, int, float, int, float]] = []
    for rank, (_, frequency, object_size) in enumerate(popularity_rows, start=1):
        cumulative_bytes += object_size
        cumulative_requests += frequency
        byte_fraction = cumulative_bytes / working_set_bytes if working_set_bytes else 0.0
        request_fraction = cumulative_requests / total_requests if total_requests else 0.0
        weighted_rows.append(
            (
                rank,
                int(cumulative_bytes),
                int(cumulative_requests),
                float(byte_fraction),
                int(frequency),
                float(request_fraction),
            )
        )

    base_name = f"trace_analysis_{trace_name}"
    plot_path = run_dir / f"{base_name}.png"
    summary_json_path = run_dir / f"{base_name}_summary.json"
    popularity_csv_path = run_dir / f"{base_name}_popularity.csv"
    weighted_popularity_csv_path = run_dir / f"{base_name}_weighted_by_size.csv"
    weighted_plot_path = run_dir / f"{base_name}_weighted_by_size.png"

    with open(summary_json_path, "w", encoding="utf-8") as summary_file:
        json.dump(summary, summary_file, indent=2)

    with open(popularity_csv_path, "w", encoding="utf-8", newline="") as popularity_file:
        writer = csv.writer(popularity_file)
        writer.writerow(["rank", "frequency"])
        for rank, frequency in zip(ranks, frequencies):
            writer.writerow([int(rank), int(frequency)])

    with open(weighted_popularity_csv_path, "w", encoding="utf-8", newline="") as weighted_file:
        writer = csv.writer(weighted_file)
        writer.writerow(
            [
                "rank",
                "cumulative_bytes",
                "cumulative_requests",
                "cumulative_byte_fraction",
                "frequency",
                "cumulative_request_fraction",
            ]
        )
        for row in weighted_rows:
            writer.writerow(row)

    plt.figure(figsize=(10, 6))
    plt.loglog(ranks, frequencies, marker="o", markersize=3, linestyle="none", alpha=0.6)
    plt.xlabel("Object Rank", fontsize=12)
    plt.ylabel("Request Frequency", fontsize=12)
    plt.title("Complete Popularity Distribution", fontsize=14, fontweight="bold")
    plt.grid(True, which="both", alpha=0.3)
    plt.tight_layout()
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()

    if weighted_rows:
        byte_fractions = [row[3] for row in weighted_rows]
        request_fractions = [row[5] for row in weighted_rows]

        plt.figure(figsize=(10, 6))
        plt.plot(byte_fractions, request_fractions, linewidth=2.2)
        plt.xlabel("Cumulative Fraction of Working-Set Bytes", fontsize=12)
        plt.ylabel("Cumulative Fraction of Requests", fontsize=12)
        plt.title("Request Capture by Top-k Bytes (Popularity Ordered)", fontsize=14, fontweight="bold")
        plt.grid(True, alpha=0.3)
        plt.xlim(0, 1)
        plt.ylim(0, 1)
        plt.tight_layout()
        plt.savefig(weighted_plot_path, dpi=150, bbox_inches="tight")
        plt.close()

    logger.info("Saved summary JSON: %s", summary_json_path)
    logger.info("Saved raw popularity CSV: %s", popularity_csv_path)
    logger.info("Saved size-weighted popularity CSV: %s", weighted_popularity_csv_path)
    logger.info("Saved plot: %s", plot_path)
    logger.info("Saved size-weighted plot: %s", weighted_plot_path)


if __name__ == "__main__":
    main()
