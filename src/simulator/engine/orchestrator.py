from src.simulator.models.lru_cache import ByteAwareLRUCache
from src.simulator.data_access.parser import parse_trace_file


class SimulationEngine:
	def __init__(
		self,
		edge_cache: ByteAwareLRUCache,
		parent_cache: ByteAwareLRUCache,
		trace_file_path: str,
	) -> None:
		self.edge_cache = edge_cache
		self.parent_cache = parent_cache
		self.trace_file_path = trace_file_path
		self.total_requests = 0

	def run(self) -> dict[str, float]:
		for request in parse_trace_file(self.trace_file_path):
			self.total_requests += 1

			if self.edge_cache.get(request.cachekey):
				continue

			if self.parent_cache.get(request.cachekey):
				self.edge_cache.put(request.cachekey, request.file_size)
				continue

			self.parent_cache.put(request.cachekey, request.file_size)
			self.edge_cache.put(request.cachekey, request.file_size)

		duplication_byte_rate = (
			self.parent_cache.byte_overlap_with(self.edge_cache) / self.parent_cache.current_bytes
			if self.parent_cache.current_bytes > 0 else 0.0
		)

		return {
			"total_requests": self.total_requests,
			"edge_hits": self.edge_cache.hits,
			"edge_misses": self.edge_cache.misses,
			"edge_evictions": self.edge_cache.evictions,
			"parent_hits": self.parent_cache.hits,
			"parent_misses": self.parent_cache.misses,
			"parent_evictions": self.parent_cache.evictions,
			"duplication_byte_rate": duplication_byte_rate,
		}
