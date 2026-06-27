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
	--trace-file data/request_seq_small \
	--edge-gb 1000 \
	--parent-gb 5000 \
	--experiment-name single_run
```

## Run: Trace Analysis

```bash
python -m scripts.analyze_trace \
	--trace-file data/request_seq_small \
	--experiment-name trace_analysis
```

## Run: Fixed-Parent Edge Sweep

```bash
python -m scripts.edge_sweep_experiment \
	--trace-file data/request_seq_small \
	--parent-gb 120 \
	--edge-sizes-gb 6,12,24,48,96,120 \
	--experiment-name edge_sweep
```
