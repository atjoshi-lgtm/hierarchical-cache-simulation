"""Run a three-edge simulation with strict common-window alignment."""

import argparse
import json
import logging
import os
from pathlib import Path
import time

from src.simulator.data_access.trace_aligner import (
    compute_overlap_window,
    merge_aligned_traces,
)
from src.simulator.engine.multi_edge_orchestrator import MultiEdgeSimulationEngine
from src.simulator.models.lru_cache import ByteAwareLRUCache


GB = 1_000_000_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a multi-edge CDN hierarchy simulation with strict overlap filtering."
    )
    parser.add_argument(
        "--trace-files",
        nargs="+",
        default=[
            "data/three_edges/request_seq_edge_1",
            "data/three_edges/request_seq_edge_2",
            "data/three_edges/request_seq_edge_3",
        ],
        help="One or more edge trace files.",
    )
    parser.add_argument("--edge-gb", type=int, default=1000)
    parser.add_argument("--parent-gb", type=int, default=5000)
    parser.add_argument(
        "--log-every",
        type=int,
        default=1_000_000,
        help="Emit progress after this many processed requests (0 disables periodic logs).",
    )
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
    if not args.trace_files:
        raise ValueError("At least one trace file must be provided via --trace-files.")

    run_dir = Path(args.output_root) / args.experiment_name / (
        f"{len(args.trace_files)}_edges_edge_{args.edge_gb}GB_parent_{args.parent_gb}GB"
    )
    os.makedirs(run_dir, exist_ok=True)
    logger = setup_logging(run_dir)

    logger.info("Starting multi-edge simulation run")
    logger.info("Number of edges: %d", len(args.trace_files))
    logger.info("Trace files: %s", ", ".join(args.trace_files))
    logger.info(
        "Capacities: edge=%d GB (each), parent=%d GB",
        args.edge_gb,
        args.parent_gb,
    )
    logger.info("Computing common overlap window...")

    overlap = compute_overlap_window(args.trace_files)
    logger.info(
        "Overlap window [start,end]: [%d,%d]",
        overlap.start_timestamp,
        overlap.end_timestamp,
    )
    for item in overlap.trace_bounds:
        logger.info(
            "Trace bounds %s -> min=%d max=%d parsed=%d skipped=%d",
            item.file_path,
            item.min_timestamp,
            item.max_timestamp,
            item.parsed_records,
            item.skipped_records,
        )

    logger.info("Preparing merged request stream (assume_sorted=%s)...", args.assume_sorted)
    merged_requests = merge_aligned_traces(
        args.trace_files,
        overlap.start_timestamp,
        overlap.end_timestamp,
        assume_sorted=args.assume_sorted,
    )
    logger.info("Merged stream ready. Running simulation engine...")

    start_time = time.perf_counter()

    def _log_progress(progress: dict[str, float]) -> None:
        elapsed = time.perf_counter() - start_time
        throughput = (
            progress["processed_requests"] / elapsed if elapsed > 0 else 0.0
        )
        logger.info(
            "Progress processed=%d edge_hits=%d parent_hits=%d global_hit_rate=%.6f throughput=%.0f req/s",
            int(progress["processed_requests"]),
            int(progress["edge_hits"]),
            int(progress["parent_hits"]),
            progress["global_hit_rate"],
            throughput,
        )

    edge_caches = {
        edge_id: ByteAwareLRUCache(args.edge_gb * GB)
        for edge_id in range(1, len(args.trace_files) + 1)
    }
    parent_cache = ByteAwareLRUCache(args.parent_gb * GB)

    engine = MultiEdgeSimulationEngine(
        edge_caches=edge_caches,
        parent_cache=parent_cache,
        merged_requests=merged_requests,
        progress_interval=args.log_every,
        progress_callback=_log_progress,
    )
    metrics = engine.run()
    elapsed_seconds = time.perf_counter() - start_time

    config = {
        "trace_files": args.trace_files,
        "edge_gb": args.edge_gb,
        "parent_gb": args.parent_gb,
        "log_every": args.log_every,
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
        f"metrics_{len(args.trace_files)}_edges_edge_{args.edge_gb}GB_parent_{args.parent_gb}GB.json"
    )
    with open(metrics_path, "w", encoding="utf-8") as metrics_file:
        json.dump(metrics, metrics_file, indent=2)

    logger.info("Multi-edge simulation completed")
    logger.info(
        "Common overlap window [start,end]: [%d,%d]",
        overlap.start_timestamp,
        overlap.end_timestamp,
    )
    logger.info("Elapsed time: %.2f seconds", elapsed_seconds)
    logger.info("Metrics: %s", json.dumps(metrics, sort_keys=True))
    logger.info("Saved metrics JSON: %s", metrics_path)


if __name__ == "__main__":
    main()
