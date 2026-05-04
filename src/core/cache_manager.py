import os
import json
import time
from typing import Any, Optional

class CacheManager:
    def __init__(self, cache_file: str, expiry_seconds: int = 60):
        self.cache_file = cache_file
        self.expiry_seconds = expiry_seconds
        self.data = {}
        self.load_cache()

    def load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}

    def save_cache(self):
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.data, f)
        except Exception:
            pass

    def get(self, key: str) -> Optional[Any]:
        if key in self.data:
            entry = self.data[key]
            if time.time() - entry["timestamp"] < self.expiry_seconds:
                return entry["value"]
            else:
                del self.data[key]
                self.save_cache()
        return None

    def set(self, key: str, value: Any):
        self.data[key] = {
            "value": value,
            "timestamp": time.time()
        }
        self.save_cache()

    def clear(self):
        self.data = {}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
