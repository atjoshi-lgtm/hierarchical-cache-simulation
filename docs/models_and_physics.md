# Models and Physics

This document defines the core mechanics and domain rules of the 2-tier CDN caching system.

## Network Topology and Flow

* **Request Path:** Client -> Edge Cache -> Parent Cache -> Origin.
* **The Edge:** Serves as the first line of defense, absorbing the most popular content.
* **The Parent:** Receives a heavily filtered miss stream from the Edge. Because the Parent serves misses back to the Edge, both caches end up storing the object. This is known as the "chopped head" problem, causing a high degree of disk overlap/duplication.

### Single-Edge Mode

* One edge cache and one parent cache are simulated.

### Multi-Edge Mode

* One or more independent edge caches share one parent cache.
* Input traces are first aligned to a strict common time window across all provided edges.
* Inclusive overlap rule: keep requests with timestamps in [start, end].
* Deterministic ordering rule: when timestamps are equal across edges, process in edge order edge1 -> edge2 -> edge3 -> ...

## Byte-Aware LRU Mechanics

* **Eviction Policy:** Strict Least Recently Used (LRU).
* **Capacity Limit:** Constrained exclusively by total bytes (`max_bytes`), not by object count. 
* **Eviction Trigger:** If inserting a new object pushes the cache's total bytes over `max_bytes`, the oldest (least recently used) objects are deleted one by one until the cache is back under the limit.

## Duplication Metrics in Multi-Edge Mode

* **Union Overlap Bytes:** Number of parent bytes whose objects are present in at least one edge cache.
* **Duplication Byte Rate:** `union_overlap_bytes / parent_current_bytes` (0.0 if parent is empty).
* **Per-Edge Overlap Metrics:** Also report each edge's overlap with parent and per-edge duplication rate for attribution.
* **Per-Edge Duplication Byte Rate (`edge_i_duplication_byte_rate`):** `edge_i_parent_overlap_bytes / parent_current_bytes` (0.0 if parent is empty).

## Parent Miss-Stream Metrics in Multi-Edge Mode

* **Aggregate Parent Hit Rate (`parent_hit_rate`):** `parent_hits / edge_misses`.
* **Per-Edge Parent Hit Rate (`edge_i_parent_hit_rate`):** `edge_i_parent_hits / (edge_i_parent_hits + edge_i_parent_misses)`.
* **Per-Edge Parent Counters:** `edge_i_parent_hits` and `edge_i_parent_misses` track parent behavior for each edge's miss stream.

## Per-Edge Request and Global Hit Metrics in Multi-Edge Mode

* **Per-Edge Request Count (`edge_i_total_requests`):** Number of merged-window requests routed to edge `i`.
* **Per-Edge Edge Hit Rate (`edge_i_hit_rate` in sweep outputs):** `edge_i_hits / edge_i_total_requests`.
* **Aggregate Global Hit Rate (`global_hit_rate` in sweep outputs):** `(edge_hits + parent_hits) / total_requests`.
* **Per-Edge Global Hit Rate (`edge_i_global_hit_rate` in sweep outputs):** `(edge_i_hits + edge_i_parent_hits) / edge_i_total_requests`.

## Object Mutability Rules

* **Dynamic Sizes:** The `file_size` associated with a specific `cachekey` can change mid-simulation due to Origin updates.
* **Update Protocol:** When an existing `cachekey` is requested with a new `file_size`, the cache must update the object, subtract the old size from its running byte total, and add the new size. If this size increase exceeds `max_bytes`, the cache must immediately trigger an eviction cycle.