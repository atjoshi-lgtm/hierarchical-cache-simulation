# Experiment Results Summary

This document summarizes the completed cache experiments and the main conclusions from the results under `experiments/`.

## Single-Edge Sweep

The single-edge experiments use one edge cache and one parent cache. The edge disk size is swept while the parent size is fixed.

The trace used for the main single-edge sweep has about 7.17 million requests, 974k unique objects, and a byte working set of about 584 GB. This working set is larger than all tested edge and parent cache sizes, so no tested cache can hold the whole trace.

The edge hit rate increases steadily as edge size grows. For the `request_seq_small` trace, the edge hit rate rises from about 61.7% at 6 GB to about 81.8% at 120 GB. This shows that increasing edge capacity is directly useful for this trace.

The parent cache is most useful when the edge cache is small. With a 48 GB parent and a 6 GB edge, the global hit rate reaches about 75.9%. As the edge grows, the parent contributes fewer hits because many useful parent objects are already present at the edge.

Duplication between parent and edge becomes very high as edge size grows. In several runs, the duplication byte rate reaches 100%, meaning all parent bytes are also present in the edge. At that point, the parent adds little or no extra hit-rate benefit.

**Conclusion:** In the single-edge case, edge capacity dominates the result. The parent helps when the edge is small, but with larger edge caches the parent mostly duplicates edge contents and becomes less useful.

## Two-Edge Experiments

The two-edge experiments use two edge traces from `data/three_edges` and one shared parent cache. The implemented sweep scripts support two complementary views: sweeping one edge size while holding the other edge and parent fixed, and sweeping parent size while holding both edges fixed.

The three traces are well aligned in time, so nearly all requests are usable in common-window simulations. Edge 1 is the largest trace, with about 16.87 million requests and a 3.57 TB working set. Edges 2 and 3 are smaller, each with about 6.8-7.0 million requests and working sets around 2.2-2.4 TB.

The pairwise overlap analysis shows that Edge 2 and Edge 3 are the most balanced pair. Their request overlap is about 33-34% in both directions. Edge 1 is much larger, so the overlap is asymmetric: only about 20-22% of Edge 1 overlaps with Edge 2 or Edge 3, but about 51-53% of Edge 2 or Edge 3 overlaps with Edge 1.

With a 120 GB parent and one edge fixed at 24 GB, global hit rates are mostly around 47-50%. Increasing the swept edge size improves that edge's local hit rate, but it also reduces parent hits. As a result, the total global hit rate changes only modestly.

With a 240 GB parent, the shared parent becomes more valuable. For Edge 1 + Edge 2, global hit rate increases to about 56-57%, compared with about 48-49% for the 120 GB parent. However, the same substitution effect remains: as the swept edge grows, the parent hit rate falls and duplication rises.

The parent-size sweep script writes the same 2x2 composite metric plot as the edge-size sweep, but with parent disk size on the x-axis. This makes it easier to separate two effects: local edge growth, which filters the parent miss stream, and parent growth, which increases the shared cache's ability to retain cross-edge objects.

**Conclusion:** The shared parent is useful in the two-edge setting because it can reuse content requested by multiple edges. Its value is strongest when the edge traces overlap. However, the current insertion policy still causes significant duplication, so larger edge caches can reduce the parent's marginal benefit.

## Cross-Edge Effect

Changing the disk size of one edge can affect the parent hit rate for the other edge's miss stream.

When one edge becomes larger, it serves more requests locally and sends fewer misses to the parent. This means fewer objects from that edge are inserted into or refreshed in the parent. If the other edge later misses on overlapping content, the parent may be less likely to have that object.

In the 120 GB parent runs, increasing one edge from 6 GB to 120 GB generally reduces the other edge's parent hit rate. For example, when Edge 1 is swept and Edge 2 is fixed at 24 GB, Edge 2's parent hit rate falls from about 21.0% to about 15.5%. With a larger 240 GB parent, the effect is smaller because the parent can retain more shared objects.

**Conclusion:** Edge caches and parent caches are not independent. A larger edge cache helps its own users, but it can reduce the shared parent population available to other edges. This is a miss-stream filtering effect.

## Overall Takeaways

* Edge capacity reliably improves local edge hit rate.
* Parent caches are most useful when they aggregate misses from multiple edges with overlapping demand.
* Larger parent caches improve global hit rate, especially in the two-edge experiments.
* High parent-edge duplication limits the benefit of the parent cache.
* The current policy behaves like an inclusive hierarchy: objects fetched through the parent are also stored at the edge.
* Future experiments should compare this policy with less duplicative policies, such as selective parent admission, leave-copy-down, or parent admission only after reuse across multiple edges.

## Most Relevant Literature

The closest literature is on hierarchical and cooperative Web caching. Che, Tung, and Wang's "Hierarchical Web Caching Systems: Modeling, Design and Experimental Results" studies how lower-level caches filter the request stream seen by upper-level caches. Laoutaris, Che, and Stavrakakis's "The LCD Interconnection of LRU Caches and Its Analysis" is relevant because it studies a less duplicative alternative to copying content everywhere. For cooperative cache interactions, Laoutaris et al.'s "Distributed Selfish Caching" and related work on distributed caching groups discuss how one cache's decisions can affect other caches in the same system.