"""Local scheduling safeguards for read-only scan runs."""

from collections.abc import Callable
import math
import os
from pathlib import Path
import time


class ScanAlreadyRunningError(RuntimeError):
    """Raised when another process holds the configured scan lock."""


class RetryingResultSink:
    """Retry only explicitly approved transient sink failures."""

    def __init__(
        self,
        sink: Callable,
        *,
        max_attempts: int = 3,
        retry_seconds: float = 2.0,
        retry_exceptions: tuple[type[Exception], ...],
        sleeper: Callable[[float], object] = time.sleep,
    ):
        if not callable(sink):
            raise TypeError("sink must be callable")
        if (
            isinstance(max_attempts, bool)
            or not isinstance(max_attempts, int)
            or max_attempts <= 0
        ):
            raise ValueError("max_attempts must be a positive integer")
        if (
            isinstance(retry_seconds, bool)
            or not isinstance(retry_seconds, (int, float))
            or not math.isfinite(retry_seconds)
            or retry_seconds < 0
        ):
            raise ValueError("retry_seconds must be a non-negative finite number")
        if (
            not isinstance(retry_exceptions, tuple)
            or not retry_exceptions
            or any(
                not isinstance(exception_type, type)
                or not issubclass(exception_type, Exception)
                for exception_type in retry_exceptions
            )
        ):
            raise TypeError("retry_exceptions must contain exception classes")
        if not callable(sleeper):
            raise TypeError("sleeper must be callable")
        self._sink = sink
        self.max_attempts = max_attempts
        self.retry_seconds = float(retry_seconds)
        self.retry_exceptions = retry_exceptions
        self._sleeper = sleeper

    def __call__(self, batch):
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self._sink(batch)
            except self.retry_exceptions:
                if attempt >= self.max_attempts:
                    raise
                self._sleeper(self.retry_seconds)
        raise AssertionError("unreachable retry state")


class FileRunLock:
    """Non-blocking OS file lock released automatically when the process exits."""

    def __init__(self, path):
        try:
            raw_path = os.fspath(path)
        except TypeError:
            raise TypeError("lock path must be path-like") from None
        if not isinstance(raw_path, str) or not raw_path.strip() or "\x00" in raw_path:
            raise ValueError("lock path has an invalid format")
        self.path = Path(raw_path)
        self._handle = None

    def acquire(self):
        if self._handle is not None:
            raise RuntimeError("scan lock is already held by this instance")
        handle = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            handle = self.path.open("a+b")
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
        except OSError:
            if handle is not None:
                try:
                    handle.close()
                except OSError:
                    pass
            raise RuntimeError("scan lock file could not be opened") from None
        try:
            self._lock(handle)
        except OSError:
            handle.close()
            raise ScanAlreadyRunningError("another scan process is already running") from None
        self._handle = handle
        return self

    def release(self):
        if self._handle is None:
            return
        handle = self._handle
        self._handle = None
        try:
            self._unlock(handle)
        finally:
            handle.close()

    @staticmethod
    def _lock(handle):
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    @staticmethod
    def _unlock(handle):
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
        return False
