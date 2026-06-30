"""Sweep parent disk size in a two-edge shared-parent simulation."""

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
        description="Sweep parent size for a two-edge shared-parent experiment."
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
    parser.add_argument("--edge-1-gb", type=int, default=24)
    parser.add_argument("--edge-2-gb", type=int, default=24)
    parser.add_argument("--parent-sizes-gb", default="12,24,48,96,120")
    parser.add_argument("--assume-sorted", action="store_true")
    parser.add_argument("--experiment-name", default="two_edge_parent_sweep")
    parser.add_argument("--output-root", default="experiments")
    return parser.parse_args()


def parse_parent_sizes(parent_sizes_raw: str) -> list[int]:
    return [int(value.strip()) for value in parent_sizes_raw.split(",") if value.strip()]


def setup_logging(run_dir: Path) -> logging.Logger:
    logger = logging.getLogger("two_edge_parent_sweep_experiment")
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
    parent_gb: int,
    edge_1_gb: int,
    edge_2_gb: int,
    metrics: dict[str, float],
) -> dict[str, float]:
    total_requests = metrics["total_requests"]
    edge_hits = metrics["edge_hits"]
    parent_hits = metrics["parent_hits"]
    edge_1_total_requests = metrics["edge_1_total_requests"]
    edge_2_total_requests = metrics["edge_2_total_requests"]
    edge_1_hits = metrics["edge_1_hits"]
    edge_2_hits = metrics["edge_2_hits"]
    edge_1_parent_hits = metrics["edge_1_parent_hits"]
    edge_2_parent_hits = metrics["edge_2_parent_hits"]

    return {
        "parent_gb": parent_gb,
        "edge_1_gb": edge_1_gb,
        "edge_2_gb": edge_2_gb,
        "total_requests": total_requests,
        "edge_hits": edge_hits,
        "edge_misses": metrics["edge_misses"],
        "edge_1_total_requests": edge_1_total_requests,
        "edge_1_hits": edge_1_hits,
        "edge_1_misses": metrics["edge_1_misses"],
        "edge_1_hit_rate": edge_1_hits / edge_1_total_requests if edge_1_total_requests > 0 else 0.0,
        "edge_2_total_requests": edge_2_total_requests,
        "edge_2_hits": edge_2_hits,
        "edge_2_misses": metrics["edge_2_misses"],
        "edge_2_hit_rate": edge_2_hits / edge_2_total_requests if edge_2_total_requests > 0 else 0.0,
        "parent_hits": parent_hits,
        "parent_misses": metrics["parent_misses"],
        "parent_hit_rate": metrics["parent_hit_rate"],
        "edge_1_parent_hits": edge_1_parent_hits,
        "edge_1_parent_misses": metrics["edge_1_parent_misses"],
        "edge_1_parent_hit_rate": metrics["edge_1_parent_hit_rate"],
        "edge_1_global_hit_rate": (
            (edge_1_hits + edge_1_parent_hits) / edge_1_total_requests
            if edge_1_total_requests > 0
            else 0.0
        ),
        "edge_2_parent_hits": edge_2_parent_hits,
        "edge_2_parent_misses": metrics["edge_2_parent_misses"],
        "edge_2_parent_hit_rate": metrics["edge_2_parent_hit_rate"],
        "edge_2_global_hit_rate": (
            (edge_2_hits + edge_2_parent_hits) / edge_2_total_requests
            if edge_2_total_requests > 0
            else 0.0
        ),
        "global_hit_rate": (edge_hits + parent_hits) / total_requests if total_requests > 0 else 0.0,
        "duplication_byte_rate": metrics["duplication_byte_rate"],
        "edge_1_duplication_byte_rate": metrics["edge_1_duplication_byte_rate"],
        "edge_2_duplication_byte_rate": metrics["edge_2_duplication_byte_rate"],
    }


def save_csv(rows: list[dict[str, float]], output_path: Path) -> None:
    fieldnames = [
        "parent_gb",
        "edge_1_gb",
        "edge_2_gb",
        "total_requests",
        "edge_hits",
        "edge_misses",
        "edge_1_total_requests",
        "edge_1_hits",
        "edge_1_misses",
        "edge_1_hit_rate",
        "edge_2_total_requests",
        "edge_2_hits",
        "edge_2_misses",
        "edge_2_hit_rate",
        "parent_hits",
        "parent_misses",
        "parent_hit_rate",
        "edge_1_parent_hits",
        "edge_1_parent_misses",
        "edge_1_parent_hit_rate",
        "edge_1_global_hit_rate",
        "edge_2_parent_hits",
        "edge_2_parent_misses",
        "edge_2_parent_hit_rate",
        "edge_2_global_hit_rate",
        "global_hit_rate",
        "duplication_byte_rate",
        "edge_1_duplication_byte_rate",
        "edge_2_duplication_byte_rate",
    ]
    with open(output_path, "w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_plot(rows: list[dict[str, float]], edge_1_gb: int, edge_2_gb: int, output_path: Path) -> None:
    x = [int(row["parent_gb"]) for row in rows]
    parent_hit_rates = [row["parent_hit_rate"] for row in rows]
    edge_1_parent_hit_rates = [row["edge_1_parent_hit_rate"] for row in rows]
    edge_2_parent_hit_rates = [row["edge_2_parent_hit_rate"] for row in rows]
    edge_1_hit_rates = [row["edge_1_hit_rate"] for row in rows]
    edge_2_hit_rates = [row["edge_2_hit_rate"] for row in rows]
    global_hit_rates = [row["global_hit_rate"] for row in rows]
    edge_1_global_hit_rates = [row["edge_1_global_hit_rate"] for row in rows]
    edge_2_global_hit_rates = [row["edge_2_global_hit_rate"] for row in rows]
    duplication_byte_rates = [row["duplication_byte_rate"] for row in rows]
    edge_1_duplication_byte_rates = [row["edge_1_duplication_byte_rate"] for row in rows]
    edge_2_duplication_byte_rates = [row["edge_2_duplication_byte_rate"] for row in rows]

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle(
        f"Two-Edge Parent Sweep\n(Edge 1 fixed at {edge_1_gb} GB, Edge 2 fixed at {edge_2_gb} GB)",
        fontsize=13,
        fontweight="bold",
    )

    plots = [
        (
            axes[0, 0],
            [
                (parent_hit_rates, "Aggregate Parent Hit Rate", "o"),
                (edge_1_parent_hit_rates, "Edge 1 Parent Hit Rate", "s"),
                (edge_2_parent_hit_rates, "Edge 2 Parent Hit Rate", "^"),
            ],
            "Parent Hit Rates",
            "Rate",
        ),
        (
            axes[0, 1],
            [
                (edge_1_hit_rates, "Edge 1 Hit Rate", "o"),
                (edge_2_hit_rates, "Edge 2 Hit Rate", "s"),
            ],
            "Edge Hit Rates",
            "Rate",
        ),
        (
            axes[1, 0],
            [
                (global_hit_rates, "Aggregate Global Hit Rate", "o"),
                (edge_1_global_hit_rates, "Edge 1 Global Hit Rate", "s"),
                (edge_2_global_hit_rates, "Edge 2 Global Hit Rate", "^"),
            ],
            "Global Hit Rates",
            "Rate",
        ),
        (
            axes[1, 1],
            [
                (duplication_byte_rates, "Aggregate Duplication Rate", "o"),
                (edge_1_duplication_byte_rates, "Edge 1 Duplication Rate", "s"),
                (edge_2_duplication_byte_rates, "Edge 2 Duplication Rate", "^"),
            ],
            "Duplication Byte Rates",
            "Rate",
        ),
    ]

    for ax, series, title, ylabel in plots:
        for values, label, marker in series:
            ax.plot(x, values, marker=marker, linewidth=2, markersize=6, label=label)
        ax.set_xscale("log")
        ax.set_xticks(x)
        ax.set_xticklabels([str(size) for size in x])
        ax.set_ylim(0, 1)
        ax.set_xlabel("Parent Disk Size (GB)")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(True, which="both", alpha=0.3)
        ax.legend()

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    parent_sizes_gb = parse_parent_sizes(args.parent_sizes_gb)
    trace_names = [Path(trace_file).name for trace_file in args.trace_files]
    run_dir = Path(args.output_root) / args.experiment_name / (
        "trace_"
        f"{trace_names[0]}_{trace_names[1]}_"
        f"parents_{min(parent_sizes_gb)}-{max(parent_sizes_gb)}GB_"
        f"edge1_{args.edge_1_gb}GB_"
        f"edge2_{args.edge_2_gb}GB"
    )
    os.makedirs(run_dir, exist_ok=True)
    logger = setup_logging(run_dir)

    logger.info("Starting two-edge parent sweep")
    logger.info("Trace files: %s", ", ".join(args.trace_files))
    logger.info(
        "Capacities: edge_1=%d GB fixed, edge_2=%d GB fixed, parent sweep=%s",
        args.edge_1_gb,
        args.edge_2_gb,
        ",".join(str(size) for size in parent_sizes_gb),
    )

    rows: list[dict[str, float]] = []
    run_summaries: list[dict[str, object]] = []
    edge_1_bytes = args.edge_1_gb * GB
    edge_2_bytes = args.edge_2_gb * GB
    overlap_metadata: dict[str, object] | None = None

    for parent_gb in parent_sizes_gb:
        logger.info(
            "Running edge_1=%d GB, edge_2=%d GB, parent=%d GB",
            args.edge_1_gb,
            args.edge_2_gb,
            parent_gb,
        )
        metrics, metadata = run_single(
            trace_files=args.trace_files,
            parent_bytes=parent_gb * GB,
            edge_1_bytes=edge_1_bytes,
            edge_2_bytes=edge_2_bytes,
            assume_sorted=args.assume_sorted,
        )
        overlap_metadata = metadata # type: ignore
        row = build_row(parent_gb, args.edge_1_gb, args.edge_2_gb, metrics)
        rows.append(row)
        run_summaries.append({
            "parent_gb": parent_gb,
            "metrics": metrics,
        })
        logger.info(
            (
                "parent_hr=%.4f edge1_parent_hr=%.4f edge2_parent_hr=%.4f "
                "edge1_hr=%.4f edge2_hr=%.4f edge1_global_hr=%.4f edge2_global_hr=%.4f "
                "global_hr=%.4f dup_byte_rate=%.4f edge1_dup_byte_rate=%.4f edge2_dup_byte_rate=%.4f"
            ),
            row["parent_hit_rate"],
            row["edge_1_parent_hit_rate"],
            row["edge_2_parent_hit_rate"],
            row["edge_1_hit_rate"],
            row["edge_2_hit_rate"],
            row["edge_1_global_hit_rate"],
            row["edge_2_global_hit_rate"],
            row["global_hit_rate"],
            row["duplication_byte_rate"],
            row["edge_1_duplication_byte_rate"],
            row["edge_2_duplication_byte_rate"],
        )

    config = {
        "trace_files": args.trace_files,
        "edge_1_gb": args.edge_1_gb,
        "edge_2_gb": args.edge_2_gb,
        "parent_sizes_gb": parent_sizes_gb,
        "assume_sorted": args.assume_sorted,
        "experiment_name": args.experiment_name,
        "output_root": args.output_root,
        "overlap": overlap_metadata,
    }
    with open(run_dir / "config_used.json", "w", encoding="utf-8") as config_file:
        json.dump(config, config_file, indent=2)

    base_name = (
        f"two_edge_parent_sweep_{trace_names[0]}_{trace_names[1]}_"
        f"edge1_{args.edge_1_gb}GB_edge2_{args.edge_2_gb}GB"
    )
    csv_path = run_dir / f"{base_name}.csv"
    json_path = run_dir / f"{base_name}.json"
    plot_path = run_dir / f"{base_name}.png"

    save_csv(rows, csv_path)
    with open(json_path, "w", encoding="utf-8") as json_file:
        json.dump(run_summaries, json_file, indent=2)
    save_plot(rows, args.edge_1_gb, args.edge_2_gb, plot_path)

    logger.info("Saved raw CSV: %s", csv_path)
    logger.info("Saved raw JSON: %s", json_path)
    logger.info("Saved plot: %s", plot_path)


if __name__ == "__main__":
    main()