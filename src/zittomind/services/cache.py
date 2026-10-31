"""Bounded process-local TTL caches; callers hash the complete context."""

import time
from collections import OrderedDict
from collections.abc import Callable
from copy import deepcopy
from typing import Any


class Cache:
    def __init__(
        self,
        capacity: int = 256,
        ttl: float = 300,
        *,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.capacity, self.ttl, self.clock = capacity, ttl, clock
        self.data: OrderedDict[tuple[str, str], tuple[float, Any]] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, project: str, key: str) -> Any:
        item = self.data.get((project, key))
        if item is None or item[0] <= self.clock():
            self.data.pop((project, key), None)
            self.misses += 1
            return None
        self.hits += 1
        self.data.move_to_end((project, key))
        return deepcopy(item[1])

    def put(self, project: str, key: str, value: Any) -> None:
        self.data[(project, key)] = (self.clock() + self.ttl, deepcopy(value))
        self.data.move_to_end((project, key))
        while len(self.data) > self.capacity:
            self.data.popitem(last=False)

    def clear(self, project: str | None = None) -> int:
        keys = [key for key in self.data if project is None or key[0] == project]
        for key in keys:
            del self.data[key]
        return len(keys)
