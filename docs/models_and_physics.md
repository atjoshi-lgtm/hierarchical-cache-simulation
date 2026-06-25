# Models and Physics

This document defines the core mechanics and domain rules of the 2-tier CDN caching system.

## Network Topology and Flow

* **Request Path:** Client -> Edge Cache -> Parent Cache -> Origin.
* **The Edge:** Serves as the first line of defense, absorbing the most popular content.
* **The Parent:** Receives a heavily filtered miss stream from the Edge. Because the Parent serves misses back to the Edge, both caches end up storing the object. This is known as the "chopped head" problem, causing a high degree of disk overlap/duplication.

## Byte-Aware LRU Mechanics

* **Eviction Policy:** Strict Least Recently Used (LRU).
* **Capacity Limit:** Constrained exclusively by total bytes (`max_bytes`), not by object count. 
* **Eviction Trigger:** If inserting a new object pushes the cache's total bytes over `max_bytes`, the oldest (least recently used) objects are deleted one by one until the cache is back under the limit.

## Object Mutability Rules

* **Dynamic Sizes:** The `file_size` associated with a specific `cachekey` can change mid-simulation due to Origin updates.
* **Update Protocol:** When an existing `cachekey` is requested with a new `file_size`, the cache must update the object, subtract the old size from its running byte total, and add the new size. If this size increase exceeds `max_bytes`, the cache must immediately trigger an eviction cycle.