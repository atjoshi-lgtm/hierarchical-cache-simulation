# hierarchical-cache-simulation

## Project State

For current capabilities, canonical commands, metric definitions, and known gaps, read `PROJECT_STATE.md` first.

## Setup

From the repository root:

```bash
source venv/bin/activate
python -m pip install -e .
```

## Smoke Tests

Always use the tiny files `data/trace_A_smoke` and `data/trace_B_smoke` for smoke tests, especially for multi-edge, two-edge, and parent-sweep CLI checks. Use the larger `data/three_edges/trace_A` and `data/three_edges/trace_B` traces only for real experiment runs.

## Documentation Notes

Do not update files under `docs/analysis_latex/` during general documentation edits. Only update those LaTeX analysis files when explicitly asked to update the LaTeX or analysis-paper content.

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

### Notes for Trace Analysis

- Saves summary JSON, rank-frequency popularity CSV, and log-log popularity plot.
- Also saves size-weighted popularity artifacts for byte-budget analysis:
  - `trace_analysis_<trace_name>_weighted_by_size.csv`
  - `trace_analysis_<trace_name>_weighted_by_size.png`
- The size-weighted curve orders objects by request frequency, then reports cumulative request coverage as cumulative unique object bytes increase.
- In the weighted CSV, `cumulative_request_fraction` answers: "what fraction of total requests are made by the top-k bytes" where k is `cumulative_byte_fraction * working_set_bytes`.

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
- Parent miss-stream metrics are reported as `parent_hit_rate` (aggregate) and `edge_i_parent_hit_rate` (per edge), along with matching hit/miss counters.

## Run: Two-Edge Parent Hit-Rate Sweep

```bash
python -m scripts.two_edge_parent_hitrate_experiment \
	--trace-files data/three_edges/request_seq_edge_1 data/three_edges/request_seq_edge_2 \
	--edge-1-sizes-gb 6,12,24,48,96,120 \
	--edge-2-gb 24 \
	--parent-gb 120 \
	--experiment-name two_edge_parent_hitrate
```

### Notes for the Two-Edge Sweep

- This experiment fixes edge_2 and the parent cache, then sweeps only edge_1 size.
- It writes one composite 2x2 plot with four metric families:
	- Parent hit rates: `parent_hit_rate`, `edge_1_parent_hit_rate`, `edge_2_parent_hit_rate`
	- Per-edge edge hit rates: `edge_1_hit_rate`, `edge_2_hit_rate`
	- Global hit rates: aggregate `global_hit_rate`, plus `edge_1_global_hit_rate`, `edge_2_global_hit_rate`
	- Duplication byte rates: aggregate `duplication_byte_rate`, plus `edge_1_duplication_byte_rate`, `edge_2_duplication_byte_rate`
- Raw CSV, raw JSON, and the composite PNG are written under the experiment directory.

## Run: Two-Edge Parent Size Sweep

```bash
python -m scripts.two_edge_parent_sweep_experiment \
	--trace-files data/three_edges/request_seq_edge_1 data/three_edges/request_seq_edge_2 \
	--edge-1-gb 24 \
	--edge-2-gb 12 \
	--parent-sizes-gb 12,24,48,96,120 \
	--experiment-name two_edge_parent_sweep
```

### Notes for the Two-Edge Parent Size Sweep

- This experiment fixes edge_1 and edge_2, then sweeps only parent cache size.
- It writes the same four-family composite 2x2 plot as the edge_1 sweep, with parent disk size on the x-axis.
- Raw CSV, raw JSON, and the composite PNG are written under the experiment directory.

### Two-Edge Metric Definitions

- `parent_hit_rate = parent_hits / edge_misses`
- `edge_i_parent_hit_rate = edge_i_parent_hits / (edge_i_parent_hits + edge_i_parent_misses)`
- `edge_i_hit_rate = edge_i_hits / edge_i_total_requests`
- `global_hit_rate = (edge_hits + parent_hits) / total_requests`
- `edge_i_global_hit_rate = (edge_i_hits + edge_i_parent_hits) / edge_i_total_requests`
- `duplication_overlap_union_bytes` = bytes currently in parent that also exist in at least one edge cache (union over edges)
- `duplication_byte_rate = duplication_overlap_union_bytes / parent_current_bytes`
- `edge_i_duplication_byte_rate = edge_i_parent_overlap_bytes / parent_current_bytes`

## Run: Two-Trace Weighted Overlap Analysis

```bash
python -m scripts.analyze_two_trace_weighted_overlap \
	--trace-files data/three_edges/request_seq_edge_1 data/three_edges/request_seq_edge_2 \
	--num-buckets 24 \
	--experiment-name two_trace_weighted_overlap
```

### Notes for Weighted Overlap Analysis

- Uses pairwise common window for the two input traces only.
- Time buckets are equal-width by timestamp; final bucket may be shorter.
- The requested bucket count is a target; actual bucket count can be lower while preserving equal-width semantics.
- Reports request-weighted and byte-weighted overlap with directional fractions (A->B, B->A) and weighted Jaccard per bucket.
- For each pair of edges (A, B), let (U_A) and (U_B) be sets of unique files requested.
	- Common-from-(A): $\frac{|U_A \cap U_B|}{|U_A|}$
	- Common-from-(B): $\frac{|U_A \cap U_B|}{|U_B|}$
	- Jaccard: $\frac{|U_A \cap U_B|}{|U_A \cup U_B|}$
- `A->B` means "how much of trace A overlaps with trace B" (shared weighted mass divided by A's total weighted mass for that bucket).
- `B->A` means "how much of trace B overlaps with trace A" (shared weighted mass divided by B's total weighted mass for that bucket).
- Because the denominators differ, `A->B` and `B->A` are often different even for the same bucket.
- Saves raw CSV, raw JSON, summary JSON, and three plots (request overlap, byte overlap, and per-bucket volumes).
