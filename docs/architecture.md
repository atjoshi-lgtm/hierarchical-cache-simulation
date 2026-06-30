# System Architecture

This document defines the strict, modular layer boundaries for the hierarchical-cache-simulation repository.

## Layer Definitions

* **Data Layer (`src/simulator/data_access/`):** Responsible for file I/O. Uses lazy-loading generators to parse massive text logs line-by-line and converts raw strings into lightweight `RequestTrace` dataclasses. For multi-edge alignment, the default unsorted merge mode may buffer overlap-window records in memory to guarantee deterministic global ordering; sorted mode remains streaming.
* **Models Layer (`src/simulator/models/`):** Contains the stateful cache data structures. Completely decoupled from file I/O and routing. Handles pure cache physics, specifically byte-aware LRU eviction and object mutation.
* **Engine Layer (`src/simulator/engine/`):** The orchestrator. Fetches data from the Data Layer and routes it through the Edge and Parent models. Tracks all simulation metrics including hits, misses, and byte-level traffic.
* **Scripts (`scripts/`):** The executable entry points. Responsible for parsing configuration variables (like cache sizes and file paths), instantiating the Engine, and triggering the simulation run.

## Multi-Edge Extensions

* **Trace Alignment Module (`src/simulator/data_access/trace_aligner.py`):**
	* Computes per-trace bounds and strict shared overlap window for multi-edge runs.
	* Filters each trace to inclusive overlap bounds [start, end].
	* Produces deterministic merged request ordering with edge tie-break rule edge1 -> edge2 -> edge3 -> ...
* **Merge Modes:**
	* Default mode (`assume_sorted=False`) sorts in-window records to support traces that are not strictly timestamp-sorted.
	* Streaming mode (`assume_sorted=True`) uses iterator-based heap merge for pre-sorted traces.
* **Multi-Edge Engine (`src/simulator/engine/multi_edge_orchestrator.py`):**
	* Maintains one cache per edge plus one shared parent cache.
	* Processes merged events with the same Edge -> Parent -> Origin logic as single-edge simulation.
	* Emits aggregate and per-edge metrics, plus union-based duplication overlap counters.
* **Operational Logging (`scripts/run_multi_edge_simulation.py`):**
	* Logs run phases (window scan, merge setup, simulation progress, completion).
	* Supports periodic progress logging with configurable request interval.
* **Two-Edge Sweep Scripts:**
	* `scripts/two_edge_parent_hitrate_experiment.py` sweeps edge_1 size while edge_2 and parent capacity remain fixed.
	* `scripts/two_edge_parent_sweep_experiment.py` sweeps parent size while edge_1 and edge_2 capacity remain fixed.
	* Both scripts save `run.log`, `config_used.json`, raw CSV, raw JSON, and one 2x2 composite PNG under `experiments/<experiment_name>/...`.
	* The composite plots show parent hit rates, per-edge edge hit rates, aggregate/per-edge global hit rates, and aggregate/per-edge duplication byte rates.