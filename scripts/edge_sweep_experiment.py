"""Sweep edge disk size with fixed parent and save metrics plus plots."""

import argparse
import csv
import json
import logging
import os
from pathlib import Path

import matplotlib.pyplot as plt

from src.simulator.engine.orchestrator import SimulationEngine
from src.simulator.models.lru_cache import ByteAwareLRUCache


GB = 1_000_000_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run fixed-parent edge-size sweep experiment.")
    parser.add_argument("--trace-file", default="data/request_seq_small")
    parser.add_argument("--parent-gb", type=int, default=120)
    parser.add_argument("--edge-sizes-gb", default="6,12,24,48,96,120")
    parser.add_argument("--experiment-name", default="edge_sweep")
    parser.add_argument("--output-root", default="experiments")
    return parser.parse_args()


def parse_edge_sizes(edge_sizes_raw: str) -> list[int]:
    return [int(value.strip()) for value in edge_sizes_raw.split(",") if value.strip()]


def setup_logging(run_dir: Path) -> logging.Logger:
    logger = logging.getLogger("edge_sweep_experiment")
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


def run_single(trace_file: str, parent_bytes: int, edge_bytes: int) -> dict[str, float]:
    edge_cache = ByteAwareLRUCache(edge_bytes)
    parent_cache = ByteAwareLRUCache(parent_bytes)
    engine = SimulationEngine(edge_cache, parent_cache, trace_file)
    return engine.run()


def save_csv(rows: list[dict[str, float]], output_path: Path) -> None:
    fieldnames = [
        "edge_gb",
        "total_requests",
        "edge_hits",
        "edge_misses",
        "parent_hits",
        "parent_misses",
        "edge_hit_rate",
        "parent_conditional_hit_rate",
        "global_hit_rate",
        "duplication_byte_rate",
    ]
    with open(output_path, "w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_plot(rows: list[dict[str, float]], parent_gb: int, output_path: Path) -> None:
    x = [int(row["edge_gb"]) for row in rows]
    edge_hit_rates = [row["edge_hit_rate"] for row in rows]
    parent_conditional_hit_rates = [row["parent_conditional_hit_rate"] for row in rows]
    global_hit_rates = [row["global_hit_rate"] for row in rows]
    duplication_byte_rates = [row["duplication_byte_rate"] for row in rows]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle(
        f"Hierarchical Cache Experiment\n(Parent fixed at {parent_gb} GB, Edge swept)",
        fontsize=13,
        fontweight="bold",
    )

    plots = [
        (axes[0, 0], edge_hit_rates, "Edge Hit Rate", "Hit Rate"),
        (axes[0, 1], parent_conditional_hit_rates, "Parent Conditional Hit Rate", "Hit Rate"),
        (axes[1, 0], global_hit_rates, "Global Hit Rate", "Hit Rate"),
        (
            axes[1, 1],
            duplication_byte_rates,
            "Duplication Byte Rate\n(parent bytes also in edge)",
            "Rate",
        ),
    ]

    for ax, values, title, ylabel in plots:
        ax.plot(x, values, marker="o", linewidth=2, markersize=6)
        ax.set_xscale("log")
        ax.set_xlabel("Edge Disk Size (GB)", fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_title(title, fontsize=11)
        ax.set_xticks(x)
        ax.set_xticklabels([str(size) for size in x])
        ax.set_ylim(0, 1)
        ax.grid(True, which="both", alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    edge_sizes_gb = parse_edge_sizes(args.edge_sizes_gb)
    trace_name = Path(args.trace_file).name
    run_dir = Path(args.output_root) / args.experiment_name / (
        f"trace_{trace_name}_parent_{args.parent_gb}GB_edges_{min(edge_sizes_gb)}-{max(edge_sizes_gb)}GB"
    )
    os.makedirs(run_dir, exist_ok=True)
    logger = setup_logging(run_dir)

    config = {
        "trace_file": args.trace_file,
        "parent_gb": args.parent_gb,
        "edge_sizes_gb": edge_sizes_gb,
        "experiment_name": args.experiment_name,
        "output_root": args.output_root,
    }
    with open(run_dir / "config_used.json", "w", encoding="utf-8") as config_file:
        json.dump(config, config_file, indent=2)

    rows: list[dict[str, float]] = []
    parent_bytes = args.parent_gb * GB

    for edge_gb in edge_sizes_gb:
        logger.info("Running edge=%d GB, parent=%d GB", edge_gb, args.parent_gb)
        metrics = run_single(args.trace_file, parent_bytes, edge_gb * GB)

        total_requests = metrics["total_requests"]
        edge_hits = metrics["edge_hits"]
        parent_hits = metrics["parent_hits"]
        edge_misses = total_requests - edge_hits

        row = {
            "edge_gb": edge_gb,
            "total_requests": total_requests,
            "edge_hits": edge_hits,
            "edge_misses": edge_misses,
            "parent_hits": parent_hits,
            "parent_misses": metrics["parent_misses"],
            "edge_hit_rate": edge_hits / total_requests,
            "parent_conditional_hit_rate": parent_hits / edge_misses if edge_misses > 0 else 0.0,
            "global_hit_rate": (edge_hits + parent_hits) / total_requests,
            "duplication_byte_rate": metrics["duplication_byte_rate"],
        }
        rows.append(row)
        logger.info(
            "edge_hr=%.4f parent_cond_hr=%.4f global_hr=%.4f dup_byte_rate=%.4f",
            row["edge_hit_rate"],
            row["parent_conditional_hit_rate"],
            row["global_hit_rate"],
            row["duplication_byte_rate"],
        )

    base_name = f"edge_sweep_trace_{trace_name}_parent_{args.parent_gb}GB"
    csv_path = run_dir / f"{base_name}.csv"
    json_path = run_dir / f"{base_name}.json"
    plot_path = run_dir / f"{base_name}.png"

    save_csv(rows, csv_path)
    with open(json_path, "w", encoding="utf-8") as json_file:
        json.dump(rows, json_file, indent=2)
    save_plot(rows, args.parent_gb, plot_path)

    logger.info("Saved raw CSV: %s", csv_path)
    logger.info("Saved raw JSON: %s", json_path)
    logger.info("Saved plot: %s", plot_path)


if __name__ == "__main__":
    main()
