"""Bounded, process-local cache for normalized daily chart results."""

from collections import OrderedDict
from copy import deepcopy
import time


class DailyChartCache:
    """Five-minute TTL and LRU eviction; callers always receive independent bars."""

    def __init__(self, ttl=300, max_entries=128):
        self.ttl = ttl
        self.max_entries = max_entries
        self._entries = OrderedDict()

    def get(self, key):
        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, bars = entry
        if time.monotonic() >= expires_at:
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        return deepcopy(bars)

    def put(self, key, bars):
        # Empty results may be transient; retry them on the next request.
        if not bars:
            return
        self._entries[key] = (time.monotonic() + self.ttl, deepcopy(bars))
        self._entries.move_to_end(key)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)

    def discard(self, key):
        self._entries.pop(key, None)

    def clear(self):
        self._entries.clear()
