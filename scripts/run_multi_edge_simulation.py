"""Run a three-edge simulation with strict common-window alignment."""

import argparse
import json
import logging
import os
from pathlib import Path

from src.simulator.data_access.trace_aligner import (
    compute_overlap_window,
    merge_aligned_traces,
)
from src.simulator.engine.multi_edge_orchestrator import MultiEdgeSimulationEngine
from src.simulator.models.lru_cache import ByteAwareLRUCache


GB = 1_000_000_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a three-edge CDN hierarchy simulation with strict overlap filtering."
    )
    parser.add_argument(
        "--trace-files",
        nargs=3,
        default=[
            "data/three_edges/request_seq_edge_1",
            "data/three_edges/request_seq_edge_2",
            "data/three_edges/request_seq_edge_3",
        ],
    )
    parser.add_argument("--edge-gb", type=int, default=1000)
    parser.add_argument("--parent-gb", type=int, default=5000)
    parser.add_argument(
        "--assume-sorted",
        action="store_true",
        help="Use streaming merge that assumes each input trace is timestamp-sorted.",
    )
    parser.add_argument("--experiment-name", default="three_edge_run")
    parser.add_argument("--output-root", default="experiments")
    return parser.parse_args()


def setup_logging(run_dir: Path) -> logging.Logger:
    logger = logging.getLogger("run_multi_edge_simulation")
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

    run_dir = Path(args.output_root) / args.experiment_name / (
        f"three_edges_edge_{args.edge_gb}GB_parent_{args.parent_gb}GB"
    )
    os.makedirs(run_dir, exist_ok=True)
    logger = setup_logging(run_dir)

    overlap = compute_overlap_window(args.trace_files)
    merged_requests = merge_aligned_traces(
        args.trace_files,
        overlap.start_timestamp,
        overlap.end_timestamp,
        assume_sorted=args.assume_sorted,
    )

    edge_caches = {
        edge_id: ByteAwareLRUCache(args.edge_gb * GB)
        for edge_id in range(1, len(args.trace_files) + 1)
    }
    parent_cache = ByteAwareLRUCache(args.parent_gb * GB)

    engine = MultiEdgeSimulationEngine(edge_caches, parent_cache, merged_requests)
    metrics = engine.run()

    config = {
        "trace_files": args.trace_files,
        "edge_gb": args.edge_gb,
        "parent_gb": args.parent_gb,
        "assume_sorted": args.assume_sorted,
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
    }

    with open(run_dir / "config_used.json", "w", encoding="utf-8") as config_file:
        json.dump(config, config_file, indent=2)

    metrics_path = run_dir / (
        f"metrics_three_edges_edge_{args.edge_gb}GB_parent_{args.parent_gb}GB.json"
    )
    with open(metrics_path, "w", encoding="utf-8") as metrics_file:
        json.dump(metrics, metrics_file, indent=2)

    logger.info("Three-edge simulation completed")
    logger.info(
        "Common overlap window [start,end]: [%d,%d]",
        overlap.start_timestamp,
        overlap.end_timestamp,
    )
    logger.info("Metrics: %s", json.dumps(metrics, sort_keys=True))
    logger.info("Saved metrics JSON: %s", metrics_path)


if __name__ == "__main__":
    main()
