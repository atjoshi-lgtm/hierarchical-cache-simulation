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