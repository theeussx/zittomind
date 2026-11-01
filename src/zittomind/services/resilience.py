"""Circuit breaker with one half-open probe and a sliding-window limiter."""

import time
from collections import defaultdict, deque
from collections.abc import Callable


class CircuitBreaker:
    def __init__(
        self,
        threshold: int = 3,
        cooldown: float = 30,
        *,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.threshold, self.cooldown, self.clock = threshold, cooldown, clock
        self.failures: dict[str, int] = defaultdict(int)
        self.opened: dict[str, float] = {}
        self.probes: set[str] = set()

    def allow(self, key: str) -> bool:
        if key not in self.opened:
            return True
        if self.clock() - self.opened[key] < self.cooldown or key in self.probes:
            return False
        self.probes.add(key)
        return True

    def failure(self, key: str) -> None:
        self.probes.discard(key)
        self.failures[key] += 1
        if self.failures[key] >= self.threshold:
            self.opened[key] = self.clock()

    def abandon(self, key: str) -> None:
        """Release a half-open probe when execution never reached the provider."""
        self.probes.discard(key)

    def success(self, key: str) -> None:
        self.failures.pop(key, None)
        self.opened.pop(key, None)
        self.probes.discard(key)


class RateLimiter:
    def __init__(self, limit: int):
        self.limit = limit
        self.windows: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        window = self.windows[key]
        while window and window[0] <= now - 60:
            window.popleft()
        if len(window) >= self.limit:
            raise ValueError("rate limit exceeded")
        window.append(now)
