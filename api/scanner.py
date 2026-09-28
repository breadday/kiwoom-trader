"""Read-only market scanning and periodic orchestration.

This module deliberately has no broker or order dependency. An evaluator can
classify validated daily bars, while a result sink can later deliver summaries
to a dashboard or notification adapter.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from threading import Event
from typing import Any


@dataclass(frozen=True)
class ScanConfig:
    codes: tuple[str, ...]
    limit: int = 60
    max_symbols: int = 50

    def __post_init__(self):
        if isinstance(self.codes, (str, bytes)) or not isinstance(self.codes, Sequence):
            raise ValueError("scan codes must be a sequence")
        object.__setattr__(self, "codes", tuple(self.codes))
        if (
            isinstance(self.max_symbols, bool)
            or not isinstance(self.max_symbols, int)
            or self.max_symbols <= 0
        ):
            raise ValueError("max_symbols must be a positive integer")
        if not self.codes:
            raise ValueError("scan codes must not be empty")
        if len(self.codes) > self.max_symbols:
            raise ValueError("scan codes exceed max_symbols")
        if len(set(self.codes)) != len(self.codes):
            raise ValueError("scan codes must be unique")
        if any(
            not isinstance(code, str) or len(code) != 6 or not code.isdigit()
            for code in self.codes
        ):
            raise ValueError("each scan code must be a six-digit string")
        if isinstance(self.limit, bool) or not isinstance(self.limit, int) or self.limit <= 0:
            raise ValueError("scan limit must be a positive integer")


@dataclass(frozen=True)
class ScanItem:
    code: str
    status: str
    matched: bool
    reason: str
    latest_date: str | None = None
    latest_close: float | int | None = None
    latest_volume: float | int | None = None


class ReadOnlyMarketScanner:
    """Fetch and evaluate an explicit stock-code allowlist without orders."""

    def __init__(
        self,
        config: ScanConfig,
        *,
        daily_chart_provider: Callable[..., Sequence[Mapping[str, Any]]],
        evaluator: Callable[[str, Sequence[Mapping[str, Any]]], tuple[bool, str]],
    ):
        if not isinstance(config, ScanConfig):
            raise TypeError("config must be a ScanConfig")
        if not callable(daily_chart_provider):
            raise TypeError("daily_chart_provider must be callable")
        if not callable(evaluator):
            raise TypeError("evaluator must be callable")
        self.config = config
        self._daily_chart_provider = daily_chart_provider
        self._evaluator = evaluator

    def scan_once(self, *, base_dt=None, refresh=False):
        if base_dt is not None:
            self._validate_date(base_dt)
        if not isinstance(refresh, bool):
            raise ValueError("refresh must be a boolean")

        results = []
        for code in self.config.codes:
            try:
                bars = self._daily_chart_provider(
                    code,
                    base_dt=base_dt,
                    limit=self.config.limit,
                    refresh=refresh,
                )
                self._validate_bars(bars)
                matched, reason = self._evaluator(code, bars)
                if not isinstance(matched, bool):
                    raise ValueError("evaluator match flag must be boolean")
                if not isinstance(reason, str) or not reason.strip():
                    raise ValueError("evaluator reason must be a non-empty string")
                latest = bars[-1]
                results.append(
                    ScanItem(
                        code=code,
                        status="MATCH" if matched else "NO_MATCH",
                        matched=matched,
                        reason=reason,
                        latest_date=latest["date"],
                        latest_close=latest["close"],
                        latest_volume=latest["volume"],
                    )
                )
            except Exception as exc:
                results.append(
                    ScanItem(
                        code=code,
                        status="ERROR",
                        matched=False,
                        reason=f"{type(exc).__name__}: {exc}",
                    )
                )
        return results

    @staticmethod
    def _validate_date(value):
        if not isinstance(value, str) or len(value) != 8 or not value.isdigit():
            raise ValueError("base_dt must be a valid YYYYMMDD date")
        try:
            datetime.strptime(value, "%Y%m%d")
        except ValueError as exc:
            raise ValueError("base_dt must be a valid YYYYMMDD date") from exc

    @classmethod
    def _validate_bars(cls, bars):
        if not isinstance(bars, Sequence) or isinstance(bars, (str, bytes)) or not bars:
            raise ValueError("provider must return non-empty daily bars")
        previous_date = None
        required = ("date", "open", "high", "low", "close", "volume")
        for bar in bars:
            if not isinstance(bar, Mapping) or any(field not in bar for field in required):
                raise ValueError("provider returned a malformed daily bar")
            cls._validate_date(bar["date"])
            if previous_date is not None and bar["date"] <= previous_date:
                raise ValueError("daily bars must be strictly ascending and unique")
            previous_date = bar["date"]
            prices = [bar[field] for field in ("open", "high", "low", "close")]
            if any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or value <= 0
                for value in prices
            ):
                raise ValueError("daily prices must be positive numbers")
            if bar["high"] < max(prices) or bar["low"] > min(prices):
                raise ValueError("daily OHLC values are inconsistent")
            volume = bar["volume"]
            if (
                isinstance(volume, bool)
                or not isinstance(volume, (int, float))
                or volume < 0
            ):
                raise ValueError("daily volume must be a non-negative number")


class ScanRunner:
    """Run bounded or stoppable scan cycles and publish read-only results."""

    def __init__(self, scanner, *, result_sink, interval_seconds=300):
        if not hasattr(scanner, "scan_once") or not callable(scanner.scan_once):
            raise TypeError("scanner must provide scan_once")
        if not callable(result_sink):
            raise TypeError("result_sink must be callable")
        if (
            isinstance(interval_seconds, bool)
            or not isinstance(interval_seconds, (int, float))
            or interval_seconds <= 0
        ):
            raise ValueError("interval_seconds must be positive")
        self.scanner = scanner
        self.result_sink = result_sink
        self.interval_seconds = interval_seconds

    def run(self, *, max_cycles=None, stop_event=None):
        if max_cycles is not None and (
            isinstance(max_cycles, bool)
            or not isinstance(max_cycles, int)
            or max_cycles <= 0
        ):
            raise ValueError("max_cycles must be a positive integer or None")
        if stop_event is None:
            stop_event = Event()
        if not callable(getattr(stop_event, "is_set", None)) or not callable(
            getattr(stop_event, "wait", None)
        ):
            raise TypeError("stop_event must provide is_set and wait")

        cycles = 0
        while not stop_event.is_set() and (max_cycles is None or cycles < max_cycles):
            self.result_sink(self.scanner.scan_once())
            cycles += 1
            if max_cycles is not None and cycles >= max_cycles:
                break
            if stop_event.wait(self.interval_seconds):
                break
        return cycles
