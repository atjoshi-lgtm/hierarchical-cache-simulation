# Project State

## Objective
This repository implements a trace-driven, 2-tier CDN cache simulator (Client -> Edge -> Parent -> Origin) to study byte-aware LRU behavior and the chopped-head duplication effect when cache capacity is split across hierarchy levels.

## Current Capabilities
- Parse large trace files lazily with generator-based streaming in the data layer.
- Simulate a single Edge/Parent configuration and save reproducible run artifacts.
- Analyze one trace and produce:
  - summary metrics JSON
  - rank-frequency popularity CSV
  - log-log popularity plot
- Run a fixed-parent, edge-size sweep experiment and produce:
  - raw CSV + JSON of per-run metrics
  - 2x2 comparison plot for edge hit rate, parent conditional hit rate, global hit rate, and duplication byte rate.

## Canonical Commands
Run from repository root after activating virtual environment.

```bash
source venv/bin/activate
python -m pip install -e .
```

Single simulation run:

```bash
python -m scripts.run_simulation_demo \
  --trace-file data/request_seq_small \
  --edge-gb 1000 \
  --parent-gb 5000 \
  --experiment-name single_run
```

Trace analysis run:

```bash
python -m scripts.analyze_trace \
  --trace-file data/request_seq_small \
  --experiment-name trace_analysis
```

Fixed-parent edge sweep run:

```bash
python -m scripts.edge_sweep_experiment \
  --trace-file data/request_seq_small \
  --parent-gb 120 \
  --edge-sizes-gb 6,12,24,48,96,120 \
  --experiment-name edge_sweep
```

## Metrics and Definitions
Core simulation counters (from engine output):
- total_requests
- edge_hits, edge_misses, edge_evictions
- parent_hits, parent_misses, parent_evictions
- duplication_byte_rate

Definitions used by the sweep script:
- edge_hit_rate = edge_hits / total_requests
- parent_conditional_hit_rate = parent_hits / edge_misses
- global_hit_rate = (edge_hits + parent_hits) / total_requests
- duplication_byte_rate = overlapping_parent_bytes_with_edge / parent_current_bytes

## Current Experiment Scope
- Trace input: configurable, default is data/request_seq_small.
- Single-run script supports one Edge size + one Parent size.
- Sweep script currently varies Edge size over a provided list while holding Parent fixed.
- Duplication metric currently reported as final-state overlap ratio at run end.

## Artifact Conventions (Implemented)
All scripts write outputs under experiments/<experiment_name>/... and create directories automatically.

Single run directory pattern:
- experiments/<experiment_name>/trace_<trace_name>_edge_<edge>GB_parent_<parent>GB/

Trace analysis directory pattern:
- experiments/<experiment_name>/trace_<trace_name>/

Edge sweep directory pattern:
- experiments/<experiment_name>/trace_<trace_name>_parent_<parent>GB_edges_<min>-<max>GB/

Typical artifacts per run:
- run.log
- config_used.json
- raw data (.csv and/or .json)
- plot (.png), where applicable

## Source-of-Truth Code Map
- src/simulator/data_access/parser.py: generator trace parser and RequestTrace model.
- src/simulator/models/lru_cache.py: byte-aware LRU cache physics and overlap metric helper.
- src/simulator/engine/orchestrator.py: request flow orchestration and top-level counters.
- scripts/run_simulation_demo.py: reproducible single-configuration simulation entry point.
- scripts/analyze_trace.py: trace summary + popularity distribution artifacts.
- scripts/edge_sweep_experiment.py: fixed-parent edge sweep experiment and 4-metric plot.

## Known Gaps / Cleanup Items
- README currently references scripts/run_simulation.py, but active script is scripts/run_simulation_demo.py.
- tests/test_engine.py is empty.
- tests/test_data_access.py is empty.
- experiments/ currently contains top-level PNG files from earlier runs; newer scripts now use nested experiment directories.

## Immediate Next Priorities
1. Update README run command to match current executable scripts.
2. Add engine and parser tests (integration checks + malformed trace handling).
3. Add a small wrapper script for multi-parent sweeps (repeat edge sweep for several fixed parent sizes).

## Quick Handoff Notes for Human or AI
- Read this file first, then run one canonical command above to validate environment.
- Treat AGENT.md as policy constraints (output structure, raw-data persistence, reproducibility).
- Keep this file as current-state only; do not append chronological build history.
