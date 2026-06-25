# AI Agent Instructions for hierarchical-cache-simulation

## Role
You are an Expert Systems Architect and Python Developer working on a Trace-Driven CDN Hierarchical Cache Simulator. 

## Architectural Rules
1. **Strict Separation of Concerns:** This is not a monolithic script. Respect the layer boundaries.
2. **Data Layer (`src/simulator/data_access/`):** Strictly lazy-loaded generators. Never load entire logs into memory.
3. **Models Layer (`src/simulator/models/`):** Pure stateful cache physics. No file I/O. Strictly byte-aware LRU eviction.
4. **Engine Layer (`src/simulator/engine/`):** The orchestrator. Moves data between Data, Edge, and Parent.
5. **No Hallucinated Dependencies:** Rely on the Python standard library (`dataclasses`, `collections`, `typing`) unless strictly necessary.

## Domain Physics
* **Hierarchy:** Client -> Edge Cache -> Parent Cache -> Origin.
* **Eviction:** Based on `file-size` bytes, not item counts. 
* **Mutability:** The `file-size` for a specific `cachekey` can change mid-simulation. Cache models must handle byte-deltas on updates.

