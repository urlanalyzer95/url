import time
from collections import OrderedDict

class LRUCache:
    def __init__(self, max_size=1000):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl = 3600  # 1 час по умолчанию
    
    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                self.cache.move_to_end(key)
                return value
            else:
                del self.cache[key]
        return None
    
    def put(self, key, value, ttl=None):
        if ttl is None:
            ttl = self.ttl
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)
        self.cache[key] = (value, time.time())
    
    def size(self):
        # Очищаем просроченные
        now = time.time()
        expired = [k for k, (_, ts) in self.cache.items() if now - ts >= self.ttl]
        for k in expired:
            del self.cache[k]
        return len(self.cache)
