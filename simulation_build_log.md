# Simulation Build Log

## Project Mission
Build a highly modular, strictly separated Python repository for a trace-driven 2-tier CDN Hierarchical Cache Simulator (Edge -> Parent). 

## Core Physics
* **Eviction Policy:** Strict LRU based on byte-size limits, not item counts.
* **Flow:** Client -> Edge -> Parent -> Origin.
* **Phenomenon Under Test:** Measuring how Edge disk size variations impact the Parent's hit rate, observing the "chopped head" duplication effect.

## Phase 0: Architecture Defined
* **Status:** Complete.
* **Decisions:** * Adopted layered architecture: `data_access` (lazy parsing), `models` (stateful caches), `engine` (orchestration), and `scripts` (execution).
  * Added `tests` directory to validate strict LRU eviction physics before running full simulations.

## Phase 1: Data Layer Built
* **Status:** Complete.
* **Component:** `src/simulator/data_access/parser.py`
* **Decisions:** * Implemented `parse_trace_file` as a generator to ensure $O(1)$ memory complexity regardless of the log file size (preventing out-of-memory errors on local 8GB RAM).
  * Used `@dataclass(slots=True)` for the `RequestTrace` object to optimize the memory footprint of instantiated records before garbage collection.
  * Extracted only `timestamp`, `cachekey`, and `file_size`, discarding the rest of the 14 fields to save processing cycles.

## Phase 1.5: AI Context & Environment Configuration
* **Status:** Complete.
* **Decisions:** * Configured virtual environment with `pytest`.
  * Created `AGENT.md` to enforce strict architectural boundaries for future AI integrations.
  * **Physics Rule Established:** A `cachekey` is mutable. If its `file-size` changes mid-simulation, the cache model must dynamically adjust its current byte count and evaluate evictions.

## Phase 2: Core Documentation Populated
* **Status:** Complete.
* **Decisions:** * Fully populated `docs/architecture.md` and `docs/models_and_physics.md` to act as a contextual anchor for Copilot. 
  * Explicitly documented the object mutability rule and the "chopped head" filter effect.

## Phase 3: Models Layer Built
* **Status:** Complete.
* **Component:** `src/simulator/models/lru_cache.py`
* **Decisions:** * Implemented `ByteAwareLRUCache` using `collections.OrderedDict` to guarantee $O(1)$ time complexity for hits and evictions.
  * Added bypass logic for objects larger than the cache's maximum capacity to prevent catastrophic cache wiping.
  * Successfully handled the object mutability rule by calculating byte-deltas dynamically during `put()` operations.

## Phase 4: Core Physics Validation
* **Status:** Complete.
* **Component:** `tests/test_models.py`
* **Decisions:** * Implemented rigorous `pytest` unit tests for the `ByteAwareLRUCache`.
  * Verified edge cases: size-based evictions, mid-simulation object mutation (size updates), and the large-object bypass mechanic.

## Phase 5: Engine Layer Built
* **Status:** Complete.
* **Component:** `src/simulator/engine/orchestrator.py`
* **Decisions:** * Implemented `SimulationEngine` to orchestrate the Edge -> Parent -> Origin flow.
  * Enforced minimalist design: the simulation loop relies entirely on the internal state management of the `ByteAwareLRUCache` models, avoiding bloated validation checks.
  * Added environment execution rules to `AGENT.md`.

## Phase 6: Executable Entry Point Built
* **Status:** Complete.
* **Component:** `scripts/run_simulation.py`
* **Decisions:** * Created a minimalist execution script to wire the Data, Models, and Engine layers together.
  * Hardcoded initial testing variables (10MB Edge, 50MB Parent) to rapidly validate the "chopped head" physics on the `data/request_seq_small` log file.
  * Used standard JSON output for clean metric reporting.

## Phase 6.5: Trace Data Analysis & Visualization
* **Status:** Complete.
* **Component:** `scripts/analyze_trace.py`
* **Decisions:** * Created an analysis script to establish baseline trace metrics (Working Set Size, time span, unique objects, size distribution).
  * Leveraged `matplotlib` and `numpy` to generate a log-log plot of the complete Rank vs. Frequency popularity distribution (`popularity_distribution.png`), allowing us to visually verify the Zipfian skew of the CDN traffic.
  * Maintained $O(1)$ memory complexity during the log parsing phase by reusing the Data Layer generator.

## Phase 6.6: Experiment Management Architecture
* **Status:** Complete.
* **Decisions:** * Updated `AGENT.md` to enforce strict MLOps output rules: all outputs go to `experiments/<experiment_name>/` and must use parameterized file/folder naming.

## Phase 6.7: Raw Data Preservation Rule
* **Status:** Complete.
* **Decisions:** * Updated `AGENT.md` to strictly mandate saving raw data (`.csv`/`.json`) alongside any generated plots.

## Phase 7: Fixed-Parent Edge Sweep Experiment
* **Status:** Complete.
* **Components:** `src/simulator/models/lru_cache.py`, `src/simulator/engine/orchestrator.py`, `scripts/edge_sweep_experiment.py`
* **Decisions:** * Added cache-overlap instrumentation via `byte_overlap_with()` in the LRU model to quantify duplication between tiers.
  * Extended engine metrics with final-state `duplication_byte_rate` (fraction of parent bytes duplicated in edge).
  * Built an experiment runner that fixes Parent at 240 GB and sweeps Edge sizes `[6, 12, 24, 48, 96, 120]` GB.
  * Generated `experiments/experiment_results_parent_120GB.png` and `experiments/experiment_results_edge_sweep_240GB.png` with four core curves: Edge Hit Rate, Parent Conditional Hit Rate, Global Hit Rate, and Duplication Byte Rate.
  * Observed key behavior: global hit rate remained nearly flat (~0.844-0.847), while duplication rose sharply with larger edge allocations (up to ~0.460 at 120 GB).