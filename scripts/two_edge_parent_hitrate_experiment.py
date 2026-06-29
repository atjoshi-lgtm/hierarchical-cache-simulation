"""Sweep edge_1 disk size in a two-edge shared-parent simulation."""

import argparse
import csv
import json
import logging
import os
from pathlib import Path

import matplotlib.pyplot as plt

from src.simulator.data_access.trace_aligner import compute_overlap_window, merge_aligned_traces
from src.simulator.engine.multi_edge_orchestrator import MultiEdgeSimulationEngine
from src.simulator.models.lru_cache import ByteAwareLRUCache


GB = 1_000_000_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sweep edge_1 size for a two-edge shared-parent experiment."
    )
    parser.add_argument(
        "--trace-files",
        nargs=2,
        default=[
            "data/three_edges/request_seq_edge_1",
            "data/three_edges/request_seq_edge_2",
        ],
        help="Exactly two edge trace files, ordered as edge_1 then edge_2.",
    )
    parser.add_argument("--parent-gb", type=int, default=120)
    parser.add_argument("--edge-1-sizes-gb", default="6,12,24,48,96,120")
    parser.add_argument("--edge-2-gb", type=int, default=24)
    parser.add_argument("--assume-sorted", action="store_true")
    parser.add_argument("--experiment-name", default="two_edge_parent_hitrate")
    parser.add_argument("--output-root", default="experiments")
    return parser.parse_args()


def parse_edge_sizes(edge_sizes_raw: str) -> list[int]:
    return [int(value.strip()) for value in edge_sizes_raw.split(",") if value.strip()]


def setup_logging(run_dir: Path) -> logging.Logger:
    logger = logging.getLogger("two_edge_parent_hitrate_experiment")
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


def run_single(
    trace_files: list[str],
    parent_bytes: int,
    edge_1_bytes: int,
    edge_2_bytes: int,
    assume_sorted: bool,
) -> tuple[dict[str, float], dict[str, int | list[dict[str, int | str]]]]:
    overlap = compute_overlap_window(trace_files)
    merged_requests = merge_aligned_traces(
        trace_files,
        overlap.start_timestamp,
        overlap.end_timestamp,
        assume_sorted=assume_sorted,
    )
    engine = MultiEdgeSimulationEngine(
        edge_caches={
            1: ByteAwareLRUCache(edge_1_bytes),
            2: ByteAwareLRUCache(edge_2_bytes),
        },
        parent_cache=ByteAwareLRUCache(parent_bytes),
        merged_requests=merged_requests,
    )
    metrics = engine.run()
    metadata = {
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
    }
    return metrics, metadata


def build_row(
    edge_1_gb: int,
    edge_2_gb: int,
    parent_gb: int,
    metrics: dict[str, float],
) -> dict[str, float]:
    total_requests = metrics["total_requests"]
    edge_hits = metrics["edge_hits"]
    parent_hits = metrics["parent_hits"]

    return {
        "edge_1_gb": edge_1_gb,
        "edge_2_gb": edge_2_gb,
        "parent_gb": parent_gb,
        "total_requests": total_requests,
        "edge_hits": edge_hits,
        "edge_misses": metrics["edge_misses"],
        "edge_1_hits": metrics["edge_1_hits"],
        "edge_1_misses": metrics["edge_1_misses"],
        "edge_2_hits": metrics["edge_2_hits"],
        "edge_2_misses": metrics["edge_2_misses"],
        "parent_hits": parent_hits,
        "parent_misses": metrics["parent_misses"],
        "parent_hit_rate": metrics["parent_hit_rate"],
        "edge_1_parent_hits": metrics["edge_1_parent_hits"],
        "edge_1_parent_misses": metrics["edge_1_parent_misses"],
        "edge_1_parent_hit_rate": metrics["edge_1_parent_hit_rate"],
        "edge_2_parent_hits": metrics["edge_2_parent_hits"],
        "edge_2_parent_misses": metrics["edge_2_parent_misses"],
        "edge_2_parent_hit_rate": metrics["edge_2_parent_hit_rate"],
        "global_hit_rate": (edge_hits + parent_hits) / total_requests if total_requests > 0 else 0.0,
        "duplication_byte_rate": metrics["duplication_byte_rate"],
    }


def save_csv(rows: list[dict[str, float]], output_path: Path) -> None:
    fieldnames = [
        "edge_1_gb",
        "edge_2_gb",
        "parent_gb",
        "total_requests",
        "edge_hits",
        "edge_misses",
        "edge_1_hits",
        "edge_1_misses",
        "edge_2_hits",
        "edge_2_misses",
        "parent_hits",
        "parent_misses",
        "parent_hit_rate",
        "edge_1_parent_hits",
        "edge_1_parent_misses",
        "edge_1_parent_hit_rate",
        "edge_2_parent_hits",
        "edge_2_parent_misses",
        "edge_2_parent_hit_rate",
        "global_hit_rate",
        "duplication_byte_rate",
    ]
    with open(output_path, "w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_plot(rows: list[dict[str, float]], edge_2_gb: int, parent_gb: int, output_path: Path) -> None:
    x = [int(row["edge_1_gb"]) for row in rows]
    parent_hit_rates = [row["parent_hit_rate"] for row in rows]
    edge_1_parent_hit_rates = [row["edge_1_parent_hit_rate"] for row in rows]
    edge_2_parent_hit_rates = [row["edge_2_parent_hit_rate"] for row in rows]

    plt.figure(figsize=(10, 6))
    plt.plot(x, parent_hit_rates, marker="o", linewidth=2, label="Aggregate Parent Hit Rate")
    plt.plot(x, edge_1_parent_hit_rates, marker="s", linewidth=2, label="Parent Hit Rate on Edge 1 Misses")
    plt.plot(x, edge_2_parent_hit_rates, marker="^", linewidth=2, label="Parent Hit Rate on Edge 2 Misses")
    plt.xscale("log")
    plt.xticks(x, [str(size) for size in x])
    plt.ylim(0, 1)
    plt.xlabel("Edge 1 Disk Size (GB)")
    plt.ylabel("Parent Hit Rate")
    plt.title(
        f"Two-Edge Parent Hit-Rate Sweep\n(Edge 2 fixed at {edge_2_gb} GB, Parent fixed at {parent_gb} GB)",
        fontsize=12,
        fontweight="bold",
    )
    plt.grid(True, which="both", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def main() -> None:
    args = parse_args()
    edge_1_sizes_gb = parse_edge_sizes(args.edge_1_sizes_gb)
    trace_names = [Path(trace_file).name for trace_file in args.trace_files]
    run_dir = Path(args.output_root) / args.experiment_name / (
        "trace_"
        f"{trace_names[0]}_{trace_names[1]}_"
        f"parent_{args.parent_gb}GB_"
        f"edge1_{min(edge_1_sizes_gb)}-{max(edge_1_sizes_gb)}GB_"
        f"edge2_{args.edge_2_gb}GB"
    )
    os.makedirs(run_dir, exist_ok=True)
    logger = setup_logging(run_dir)

    logger.info("Starting two-edge parent hit-rate sweep")
    logger.info("Trace files: %s", ", ".join(args.trace_files))
    logger.info(
        "Capacities: edge_2=%d GB fixed, parent=%d GB fixed, edge_1 sweep=%s",
        args.edge_2_gb,
        args.parent_gb,
        ",".join(str(size) for size in edge_1_sizes_gb),
    )

    rows: list[dict[str, float]] = []
    run_summaries: list[dict[str, object]] = []
    parent_bytes = args.parent_gb * GB
    edge_2_bytes = args.edge_2_gb * GB
    overlap_metadata: dict[str, object] | None = None

    for edge_1_gb in edge_1_sizes_gb:
        logger.info(
            "Running edge_1=%d GB, edge_2=%d GB, parent=%d GB",
            edge_1_gb,
            args.edge_2_gb,
            args.parent_gb,
        )
        metrics, metadata = run_single(
            trace_files=args.trace_files,
            parent_bytes=parent_bytes,
            edge_1_bytes=edge_1_gb * GB,
            edge_2_bytes=edge_2_bytes,
            assume_sorted=args.assume_sorted,
        )
        overlap_metadata = metadata
        row = build_row(edge_1_gb, args.edge_2_gb, args.parent_gb, metrics)
        rows.append(row)
        run_summaries.append({
            "edge_1_gb": edge_1_gb,
            "metrics": metrics,
        })
        logger.info(
            "parent_hr=%.4f edge1_parent_hr=%.4f edge2_parent_hr=%.4f global_hr=%.4f dup_byte_rate=%.4f",
            row["parent_hit_rate"],
            row["edge_1_parent_hit_rate"],
            row["edge_2_parent_hit_rate"],
            row["global_hit_rate"],
            row["duplication_byte_rate"],
        )

    config = {
        "trace_files": args.trace_files,
        "parent_gb": args.parent_gb,
        "edge_1_sizes_gb": edge_1_sizes_gb,
        "edge_2_gb": args.edge_2_gb,
        "assume_sorted": args.assume_sorted,
        "experiment_name": args.experiment_name,
        "output_root": args.output_root,
        "overlap": overlap_metadata,
    }
    with open(run_dir / "config_used.json", "w", encoding="utf-8") as config_file:
        json.dump(config, config_file, indent=2)

    base_name = (
        f"two_edge_parent_hitrate_{trace_names[0]}_{trace_names[1]}_"
        f"parent_{args.parent_gb}GB_edge2_{args.edge_2_gb}GB"
    )
    csv_path = run_dir / f"{base_name}.csv"
    json_path = run_dir / f"{base_name}.json"
    plot_path = run_dir / f"{base_name}.png"

    save_csv(rows, csv_path)
    with open(json_path, "w", encoding="utf-8") as json_file:
        json.dump(run_summaries, json_file, indent=2)
    save_plot(rows, args.edge_2_gb, args.parent_gb, plot_path)

    logger.info("Saved raw CSV: %s", csv_path)
    logger.info("Saved raw JSON: %s", json_path)
    logger.info("Saved plot: %s", plot_path)


if __name__ == "__main__":
    main()