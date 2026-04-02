import time
from collections import OrderedDict

class CacheManager:
    def __init__(self, max_size=1000):
        self.cache = OrderedDict()
        self.max_size = max_size
    
    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
    
    def set(self, key, value, ttl):
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)
        self.cache[key] = {
            **value,
            '_expires': time.time() + ttl,
            '_timestamp': time.time()
        }
    
    def size(self):
        now = time.time()
        to_remove = [k for k, v in self.cache.items() if v['_expires'] < now]
        for k in to_remove:
            del self.cache[k]
        return len(self.cache)
