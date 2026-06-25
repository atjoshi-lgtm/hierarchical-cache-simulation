"""Byte-aware LRU cache model used by the CDN simulator."""

from collections import OrderedDict


class ByteAwareLRUCache:
	"""LRU cache constrained by total bytes rather than object count."""

	def __init__(self, max_bytes: int) -> None:
		self.max_bytes = max_bytes
		self.current_bytes = 0

		self.hits = 0
		self.misses = 0
		self.byte_misses = 0
		self.evictions = 0

		self._entries: OrderedDict[str, int] = OrderedDict()

	def get(self, cachekey: str) -> bool:
		"""Return True for cache hit and update recency; otherwise return False."""
		if cachekey in self._entries:
			self._entries.move_to_end(cachekey)
			self.hits += 1
			return True

		self.misses += 1
		return False

	def put(self, cachekey: str, file_size: int) -> None:
		"""Insert or update an object and evict least-recently-used items as needed."""
		if file_size > self.max_bytes:
			return

		if cachekey in self._entries:
			old_size = self._entries[cachekey]
			self.current_bytes += file_size - old_size
			self._entries[cachekey] = file_size
			self._entries.move_to_end(cachekey)
		else:
			self._entries[cachekey] = file_size
			self.current_bytes += file_size
			self.byte_misses += file_size

		self._evict_if_needed()

	def _evict_if_needed(self) -> None:
		"""Evict least-recently-used objects until capacity is respected."""
		while self.current_bytes > self.max_bytes:
			_, evicted_size = self._entries.popitem(last=False)
			self.current_bytes -= evicted_size
			self.evictions += 1

	def byte_overlap_with(self, other: 'ByteAwareLRUCache') -> int:
		"""Return the total bytes of objects in other that are also present in this cache."""
		return sum(size for key, size in other._entries.items() if key in self._entries)
