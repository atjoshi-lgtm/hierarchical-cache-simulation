# hierarchical-cache-simulation

## Project State

For current capabilities, canonical commands, metric definitions, and known gaps, read `PROJECT_STATE.md` first.

## Setup

From the repository root:

```bash
source venv/bin/activate
python -m pip install -e .
```

## Run: Single Simulation

```bash
python -m scripts.run_simulation_demo \
	--trace-file data/single_edge/request_seq_small \
	--edge-gb 1000 \
	--parent-gb 5000 \
	--experiment-name single_run
```

## Run: Trace Analysis

```bash
python -m scripts.analyze_trace \
	--trace-file data/single_edge/request_seq_small \
	--experiment-name trace_analysis
```

## Run: Fixed-Parent Edge Sweep

```bash
python -m scripts.edge_sweep_experiment \
	--trace-file data/single_edge/request_seq_small \
	--parent-gb 120 \
	--edge-sizes-gb 6,12,24,48,96,120 \
	--experiment-name edge_sweep
```

## Run: Multi-Edge (N Edges -> 1 Parent)

```bash
python -m scripts.run_multi_edge_simulation \
	--trace-files data/three_edges/request_seq_edge_1 data/three_edges/request_seq_edge_2 data/three_edges/request_seq_edge_3 \
	--edge-gb 24 \
	--parent-gb 120 \
	--experiment-name multi_edge_run
```

### Notes for Multi-Edge Runs

- The run accepts one or more edge traces via `--trace-files`.
- The run computes a strict shared overlap window across all provided traces and keeps timestamps in the inclusive range [start, end].
- Equal timestamps are processed deterministically by edge index order (edge1, edge2, edge3, ...).
- Default merge mode supports unsorted input traces by sorting in-window records in memory.
- If traces are already timestamp-sorted, add `--assume-sorted` for streaming merge behavior.
- Progress logging is enabled by default every 1,000,000 requests; tune with `--log-every` or disable periodic logs using `--log-every 0`.
- Run outputs include edge count in names, for example `3_edges_edge_24GB_parent_120GB`.
