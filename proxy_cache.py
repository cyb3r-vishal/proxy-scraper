"""
Proxy Cache Module - High-performance cache for validated proxies
"""

import json
import os
import time
from datetime import datetime, timedelta
import threading

class ProxyCache:
    def __init__(self, cache_file="proxy_cache.json", max_age_hours=12):  # Reduced default cache age
        self.cache_file = cache_file
        self.max_age = timedelta(hours=max_age_hours)
        self.cache = self._load_cache()
        self.memory_only_cache = {}  # Ultra-fast in-memory cache
        self.lock = threading.RLock()  # Thread-safe operations
        self.last_save = time.time()
        self.save_interval = 60  # Save to disk every 60 seconds

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}    
    def _save_cache(self):
        """Save cache to disk with optimized writes"""
        try:
            # Write to temporary file first to prevent corruption
            temp_file = f"{self.cache_file}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(self.cache, f)
            
            # Atomic replace
            if os.path.exists(temp_file):
                if os.path.exists(self.cache_file):
                    os.replace(temp_file, self.cache_file)
                else:
                    os.rename(temp_file, self.cache_file)
        except Exception:
            # Silently fail to avoid blocking the application
            pass

    def get(self, proxy_string):
        """Get cached proxy info with ultra-fast memory lookups"""
        # First check memory-only cache (fastest)
        if proxy_string in self.memory_only_cache:
            return self.memory_only_cache[proxy_string]
            
        # Then check persistent cache
        with self.lock:
            if proxy_string in self.cache:
                timestamp = datetime.fromisoformat(self.cache[proxy_string]['timestamp'])
                if datetime.now() - timestamp < self.max_age:
                    # Copy to memory cache for future ultra-fast lookups
                    self.memory_only_cache[proxy_string] = self.cache[proxy_string]['data']
                    return self.cache[proxy_string]['data']
        return None

    def set(self, proxy_string, data):
        """Cache proxy validation data with optimized disk writes"""
        # Update memory cache immediately for ultra-fast future lookups
        self.memory_only_cache[proxy_string] = data
        
        # Update persistent cache
        with self.lock:
            self.cache[proxy_string] = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            # Only save to disk periodically to improve performance
            current_time = time.time()
            if current_time - self.last_save > self.save_interval:
                self._save_cache()
                self.last_save = current_time
        
        self._save_cache()

    def clean(self):
        """Remove expired entries"""
        now = datetime.now()
        self.cache = {
            k: v for k, v in self.cache.items()
            if now - datetime.fromisoformat(v['timestamp']) < self.max_age
        }
        self._save_cache()
