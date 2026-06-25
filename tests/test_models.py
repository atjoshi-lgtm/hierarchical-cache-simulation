from src.simulator.models.lru_cache import ByteAwareLRUCache


def test_basic_hit_and_miss() -> None:
	cache = ByteAwareLRUCache(max_bytes=100)
	cache.put("known", 40)

	assert cache.get("known") is True
	assert cache.get("unknown") is False
	assert cache.hits == 1
	assert cache.misses == 1


def test_byte_eviction() -> None:
	cache = ByteAwareLRUCache(max_bytes=100)
	cache.put("obj1", 40)
	cache.put("obj2", 40)
	cache.put("obj3", 40)

	assert cache.current_bytes == 80
	assert cache.evictions == 1
	assert cache.get("obj1") is False
	assert cache.get("obj2") is True
	assert cache.get("obj3") is True


def test_object_mutation_size_increase() -> None:
	cache = ByteAwareLRUCache(max_bytes=100)
	cache.put("key", 50)
	cache.put("key", 80)

	assert cache.current_bytes == 80


def test_mutation_triggering_eviction() -> None:
	cache = ByteAwareLRUCache(max_bytes=100)
	cache.put("KeyA", 40)
	cache.put("KeyB", 40)
	cache.put("KeyA", 80)

	assert cache.get("KeyB") is False
	assert cache.get("KeyA") is True
	assert cache.current_bytes == 80
	assert cache.evictions == 1


def test_large_object_bypass() -> None:
	cache = ByteAwareLRUCache(max_bytes=100)
	cache.put("too_large", 150)

	assert cache.current_bytes == 0
	assert cache.hits == 0
	assert cache.misses == 0
	assert cache.byte_misses == 0
	assert cache.evictions == 0
