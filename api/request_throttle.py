"""Thread-safe minimum-interval throttle for outbound broker requests."""

from collections.abc import Callable
import math
from threading import Lock
import time


class RequestThrottle:
    """Serialize callers and enforce a minimum monotonic interval."""

    def __init__(
        self,
        min_interval_seconds: float = 0.21,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], object] = time.sleep,
    ):
        if (
            isinstance(min_interval_seconds, bool)
            or not isinstance(min_interval_seconds, (int, float))
            or not math.isfinite(min_interval_seconds)
            or min_interval_seconds <= 0
        ):
            raise ValueError("min_interval_seconds must be a positive finite number")
        if not callable(clock):
            raise TypeError("clock must be callable")
        if not callable(sleeper):
            raise TypeError("sleeper must be callable")
        self.min_interval_seconds = float(min_interval_seconds)
        self._clock = clock
        self._sleeper = sleeper
        self._lock = Lock()
        self._last_request_at = None

    def wait(self):
        with self._lock:
            now = self._clock()
            if self._last_request_at is not None:
                remaining = self.min_interval_seconds - (
                    now - self._last_request_at
                )
                if remaining > 0:
                    self._sleeper(remaining)
                    now = self._clock()
            self._last_request_at = now
