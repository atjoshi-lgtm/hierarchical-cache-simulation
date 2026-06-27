# Project State

## Objective
This repository implements a trace-driven, 2-tier CDN cache simulator (Client -> Edge -> Parent -> Origin) for both single-edge and multi-edge configurations, to study byte-aware LRU behavior and the chopped-head duplication effect when cache capacity is split across hierarchy levels.

## Current Capabilities
- Parse large trace files lazily with generator-based streaming in the data layer.
- Simulate a single Edge/Parent configuration and save reproducible run artifacts.
- Simulate one or more edge caches feeding one shared parent cache with strict common-window alignment.
- Merge multi-edge requests deterministically by edge index order for equal timestamps.
- Emit structured progress logs during long multi-edge runs.
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

Multi-edge simulation run:

```bash
python -m scripts.run_multi_edge_simulation \
  --trace-files data/three_edges/request_seq_edge_1 data/three_edges/request_seq_edge_2 data/three_edges/request_seq_edge_3 \
  --edge-gb 24 \
  --parent-gb 120 \
  --experiment-name multi_edge_run
```

# Data Format
The input is a massive plain text log file containing pre-processed request traces. 
* Lines starting with `#` are metadata/comments and must be ignored.
* Data lines are colon-separated (`:`) and contain 14 fields.
* The format is: `map:serial:timestamp:cachekey:file-size:bytes-served:cpcode:objstatus1:arlid:network:mapname:region:vcd-id:product`
* For our simulation, the critical fields are `timestamp` (index 2), `cachekey` (index 3, the unique object ID), and `file-size` (index 4, the bytes required to store it).
* Multi-edge traces are not required to be strictly timestamp-sorted when using the default merge mode.

## Metrics and Definitions
Core simulation counters (from engine output):
- total_requests
- edge_hits, edge_misses, edge_evictions
- parent_hits, parent_misses, parent_evictions
- duplication_byte_rate

Additional multi-edge counters:
- edge_1_hits/edge_1_misses/edge_1_evictions
- edge_2_hits/edge_2_misses/edge_2_evictions
- edge_3_hits/edge_3_misses/edge_3_evictions
- duplication_overlap_union_bytes
- edge_i_parent_overlap_bytes and edge_i_duplication_byte_rate

Definitions used by the sweep script:
- edge_hit_rate = edge_hits / total_requests
- parent_conditional_hit_rate = parent_hits / edge_misses
- global_hit_rate = (edge_hits + parent_hits) / total_requests
- duplication_byte_rate = overlapping_parent_bytes_with_edge / parent_current_bytes

## Current Experiment Scope
- Trace input: configurable, default is data/request_seq_small.
- Single-run script supports one Edge size + one Parent size.
- Multi-edge run supports one or more traces plus a shared parent.
- Multi-edge run computes strict shared overlap window across all provided traces and filters each trace to inclusive bounds [start, end].
- Multi-edge tie-break policy at equal timestamp is deterministic edge order (1 -> 2 -> 3 -> ...).
- Multi-edge CLI supports progress control using `--log-every` and merge strategy with `--assume-sorted`.
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

Multi-edge directory pattern:
- experiments/<experiment_name>/<num_edges>_edges_edge_<edge>GB_parent_<parent>GB/

Typical artifacts per run:
- run.log
- config_used.json
- raw data (.csv and/or .json)
- plot (.png), where applicable

## Source-of-Truth Code Map
- src/simulator/data_access/parser.py: generator trace parser and RequestTrace model.
- src/simulator/data_access/trace_aligner.py: overlap-window computation, window filtering, and deterministic multi-trace merge.
- src/simulator/models/lru_cache.py: byte-aware LRU cache physics and overlap metric helper.
- src/simulator/engine/orchestrator.py: request flow orchestration and top-level counters.
- src/simulator/engine/multi_edge_orchestrator.py: multi-edge shared-parent orchestration and multi-edge metrics.
- scripts/run_simulation_demo.py: reproducible single-configuration simulation entry point.
- scripts/run_multi_edge_simulation.py: reproducible multi-edge simulation entry point with progress logging.
- scripts/analyze_trace.py: trace summary + popularity distribution artifacts.
- scripts/edge_sweep_experiment.py: fixed-parent edge sweep experiment and 4-metric plot.

## Known Gaps / Cleanup Items
- Multi-edge default merge path sorts in-window records in memory to handle unsorted traces; this can increase memory use for very large overlap windows.
- Parent-size sweep wrapper for multi-edge path is still pending.
- experiments/ currently contains top-level PNG files from earlier runs; newer scripts now use nested experiment directories.

## Immediate Next Priorities
1. Add a parent-size sweep wrapper for the multi-edge path.
2. Add optional external-sort/pre-sort utilities for large multi-edge windows.
3. Add comparison plotting for per-edge and aggregate multi-edge metrics.

## Quick Handoff Notes for Human or AI
- Read this file first, then run one canonical command above to validate environment.
- Treat AGENT.md as policy constraints (output structure, raw-data persistence, reproducibility).
- Keep this file as current-state only; do not append chronological build history.
