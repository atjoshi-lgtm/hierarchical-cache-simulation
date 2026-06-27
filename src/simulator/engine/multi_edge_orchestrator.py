"""Multi-edge orchestration for a shared-parent CDN hierarchy simulation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.simulator.data_access.parser import RequestTrace
from src.simulator.models.lru_cache import ByteAwareLRUCache


@dataclass(slots=True)
class MultiEdgeSimulationEngine:
    edge_caches: dict[int, ByteAwareLRUCache]
    parent_cache: ByteAwareLRUCache
    merged_requests: Iterable[tuple[int, RequestTrace]]

    def run(self) -> dict[str, float]:
        total_requests = 0

        for edge_id, request in self.merged_requests:
            if edge_id not in self.edge_caches:
                raise KeyError(f"Edge cache not configured for edge_id={edge_id}")

            edge_cache = self.edge_caches[edge_id]
            total_requests += 1

            if edge_cache.get(request.cachekey):
                continue

            if self.parent_cache.get(request.cachekey):
                edge_cache.put(request.cachekey, request.file_size)
                continue

            self.parent_cache.put(request.cachekey, request.file_size)
            edge_cache.put(request.cachekey, request.file_size)

        parent_current_bytes = self.parent_cache.current_bytes
        overlap_union_bytes = self._parent_overlap_with_edge_union()
        duplication_byte_rate = (
            overlap_union_bytes / parent_current_bytes if parent_current_bytes > 0 else 0.0
        )

        metrics: dict[str, float] = {
            "total_requests": total_requests,
            "edge_hits": sum(cache.hits for cache in self.edge_caches.values()),
            "edge_misses": sum(cache.misses for cache in self.edge_caches.values()),
            "edge_evictions": sum(cache.evictions for cache in self.edge_caches.values()),
            "parent_hits": self.parent_cache.hits,
            "parent_misses": self.parent_cache.misses,
            "parent_evictions": self.parent_cache.evictions,
            "duplication_byte_rate": duplication_byte_rate,
            "duplication_overlap_union_bytes": overlap_union_bytes,
        }

        for edge_id, edge_cache in sorted(self.edge_caches.items()):
            overlap_bytes = self.parent_cache.byte_overlap_with(edge_cache)
            metrics[f"edge_{edge_id}_hits"] = edge_cache.hits
            metrics[f"edge_{edge_id}_misses"] = edge_cache.misses
            metrics[f"edge_{edge_id}_evictions"] = edge_cache.evictions
            metrics[f"edge_{edge_id}_parent_overlap_bytes"] = overlap_bytes
            metrics[f"edge_{edge_id}_duplication_byte_rate"] = (
                overlap_bytes / parent_current_bytes if parent_current_bytes > 0 else 0.0
            )

        return metrics

    def _parent_overlap_with_edge_union(self) -> int:
        """Return parent bytes that also exist in at least one edge cache."""
        edge_union_keys: set[str] = set()
        for edge_cache in self.edge_caches.values():
            edge_union_keys.update(edge_cache._entries.keys())

        return sum(
            size for key, size in self.parent_cache._entries.items() if key in edge_union_keys
        )
