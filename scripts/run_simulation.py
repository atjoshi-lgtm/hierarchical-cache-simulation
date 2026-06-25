import json

from src.simulator.engine.orchestrator import SimulationEngine
from src.simulator.models.lru_cache import ByteAwareLRUCache


if __name__ == "__main__":
	GB = 1_000_000_000
	TB = 1_000_000_000_000
	TRACE_FILE = "data/request_seq_small"
	EDGE_MAX_BYTES = 1 * TB
	PARENT_MAX_BYTES = 5 * TB

	edge_cache = ByteAwareLRUCache(EDGE_MAX_BYTES)
	parent_cache = ByteAwareLRUCache(PARENT_MAX_BYTES)
	engine = SimulationEngine(edge_cache, parent_cache, TRACE_FILE)
	metrics = engine.run()

	print(json.dumps(metrics, indent=4))
