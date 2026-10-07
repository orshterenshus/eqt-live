"""Thread-safe TTL cache. Failed computations are not cached."""
from threading import Lock
from typing import Callable, Hashable, TypeVar

from cachetools import TTLCache

from app.config import CACHE_TTL_SECONDS

T = TypeVar("T")


class ResultCache:
    def __init__(self, ttl: int = CACHE_TTL_SECONDS, maxsize: int = 256):
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = Lock()

    def get_or_compute(self, key: Hashable, compute: Callable[[], T]) -> T:
        with self._lock:
            if key in self._cache:
                return self._cache[key]
        value = compute()
        with self._lock:
            self._cache[key] = value
        return value
