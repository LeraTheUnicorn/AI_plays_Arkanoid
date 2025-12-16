from typing import Dict, Any, List


class MemoryEfficientCache:
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Any] = {}
        self.access_order: List[str] = []
        self.max_size = max_size

    def get(self, key: str) -> Any:
        if key in self.cache:
            # Переместить в конец списка (MRU)
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None

    def put(self, key: str, value: Any):
        if key in self.cache:
            self.access_order.remove(key)
        elif len(self.cache) >= self.max_size:
            # Удалить LRU элемент
            lru_key = self.access_order.pop(0)
            del self.cache[lru_key]

        self.cache[key] = value
        self.access_order.append(key)
