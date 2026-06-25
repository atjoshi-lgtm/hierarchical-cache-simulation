# System Architecture

This document defines the strict, modular layer boundaries for the hierarchical-cache-simulation repository.

## Layer Definitions

* **Data Layer (`src/simulator/data_access/`):** Responsible for file I/O. Uses lazy-loading generators to parse massive text logs line-by-line. Never buffers entire files into memory. Converts raw strings into lightweight `RequestTrace` dataclasses.
* **Models Layer (`src/simulator/models/`):** Contains the stateful cache data structures. Completely decoupled from file I/O and routing. Handles pure cache physics, specifically byte-aware LRU eviction and object mutation.
* **Engine Layer (`src/simulator/engine/`):** The orchestrator. Fetches data from the Data Layer and routes it through the Edge and Parent models. Tracks all simulation metrics including hits, misses, and byte-level traffic.
* **Scripts (`scripts/`):** The executable entry points. Responsible for parsing configuration variables (like cache sizes and file paths), instantiating the Engine, and triggering the simulation run.