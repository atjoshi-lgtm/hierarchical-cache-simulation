"""Run a single simulation configuration and save reproducible artifacts."""

import argparse
import json
import logging
import os
from pathlib import Path

from src.simulator.engine.orchestrator import SimulationEngine
from src.simulator.models.lru_cache import ByteAwareLRUCache


GB = 1_000_000_000


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Run a single CDN hierarchy simulation.")
	parser.add_argument("--trace-file", default="data/request_seq_small")
	parser.add_argument("--edge-gb", type=int, default=1000)
	parser.add_argument("--parent-gb", type=int, default=5000)
	parser.add_argument("--experiment-name", default="single_run")
	parser.add_argument("--output-root", default="experiments")
	return parser.parse_args()


def setup_logging(run_dir: Path) -> logging.Logger:
	logger = logging.getLogger("run_simulation_demo")
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
	run_dir = Path(args.output_root) / args.experiment_name / (
		f"trace_{trace_name}_edge_{args.edge_gb}GB_parent_{args.parent_gb}GB"
	)
	os.makedirs(run_dir, exist_ok=True)
	logger = setup_logging(run_dir)

	config = {
		"trace_file": args.trace_file,
		"edge_gb": args.edge_gb,
		"parent_gb": args.parent_gb,
		"experiment_name": args.experiment_name,
		"output_root": args.output_root,
	}
	with open(run_dir / "config_used.json", "w", encoding="utf-8") as config_file:
		json.dump(config, config_file, indent=2)

	edge_cache = ByteAwareLRUCache(args.edge_gb * GB)
	parent_cache = ByteAwareLRUCache(args.parent_gb * GB)
	engine = SimulationEngine(edge_cache, parent_cache, args.trace_file)
	metrics = engine.run()

	metrics_path = run_dir / (
		f"metrics_trace_{trace_name}_edge_{args.edge_gb}GB_parent_{args.parent_gb}GB.json"
	)
	with open(metrics_path, "w", encoding="utf-8") as metrics_file:
		json.dump(metrics, metrics_file, indent=2)

	logger.info("Simulation completed")
	logger.info("Metrics: %s", json.dumps(metrics, sort_keys=True))
	logger.info("Saved metrics JSON: %s", metrics_path)


if __name__ == "__main__":
	main()
