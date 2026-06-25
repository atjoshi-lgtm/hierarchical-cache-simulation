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