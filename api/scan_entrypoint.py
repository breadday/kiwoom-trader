"""Composition entrypoint for one read-only market scan cycle.

Signal rules are deliberately supplied by the caller. This module only binds
validated environment configuration, Kiwoom daily bars, the scanner, and the
Telegram result sink; it never imports or invokes an order adapter.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import math
import os
from typing import Any

from api.kiwoom_api import KiwoomAPI
from api.scanner import ReadOnlyMarketScanner, ScanConfig, ScanRunner
from api.telegram_notifications import TelegramConfig, TelegramScanResultSink


@dataclass(frozen=True)
class ScanRuntimeConfig:
    codes: tuple[str, ...]
    limit: int = 60
    interval_seconds: float = 300.0

    def __post_init__(self):
        scan_config = ScanConfig(codes=self.codes, limit=self.limit)
        object.__setattr__(self, "codes", scan_config.codes)
        if (
            isinstance(self.interval_seconds, bool)
            or not isinstance(self.interval_seconds, (int, float))
            or not math.isfinite(self.interval_seconds)
            or self.interval_seconds <= 0
        ):
            raise ValueError("scan interval must be a positive finite number")

    @classmethod
    def from_env(cls, environ=None):
        source = os.environ if environ is None else environ
        if not isinstance(source, Mapping):
            raise TypeError("environ must be a mapping")

        raw_codes = source.get("KIWOOM_SCAN_CODES")
        if not isinstance(raw_codes, str) or not raw_codes.strip():
            raise ValueError("KIWOOM_SCAN_CODES is not configured")
        codes = tuple(part.strip() for part in raw_codes.split(","))

        limit = cls._positive_int(source.get("KIWOOM_SCAN_LIMIT", "60"), "scan limit")
        interval = cls._positive_float(
            source.get("KIWOOM_SCAN_INTERVAL_SECONDS", "300"),
            "scan interval",
        )
        return cls(codes=codes, limit=limit, interval_seconds=interval)

    @staticmethod
    def _positive_int(value, label):
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} must be a positive integer") from exc
        if isinstance(value, bool) or parsed <= 0 or str(value).strip() != str(parsed):
            raise ValueError(f"{label} must be a positive integer")
        return parsed

    @staticmethod
    def _positive_float(value, label):
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} must be a positive finite number") from exc
        if isinstance(value, bool) or not math.isfinite(parsed) or parsed <= 0:
            raise ValueError(f"{label} must be a positive finite number")
        return parsed


def build_scan_runner(
    *,
    evaluator: Callable[[str, Sequence[Mapping[str, Any]]], tuple[bool, str]],
    environ=None,
    api_factory=KiwoomAPI,
    sink_factory=TelegramScanResultSink,
):
    """Build a paper-mode, read-only scan pipeline from validated settings."""
    if not callable(evaluator):
        raise TypeError("evaluator must be callable")
    if not callable(api_factory):
        raise TypeError("api_factory must be callable")
    if not callable(sink_factory):
        raise TypeError("sink_factory must be callable")

    runtime = ScanRuntimeConfig.from_env(environ)
    telegram = TelegramConfig.from_env(environ)
    api = api_factory(paper=True)
    if getattr(api, "is_paper", None) is not True:
        raise RuntimeError("scan entrypoint requires paper mode")

    scanner = ReadOnlyMarketScanner(
        ScanConfig(codes=runtime.codes, limit=runtime.limit),
        daily_chart_provider=api.get_daily_chart,
        evaluator=evaluator,
    )
    return ScanRunner(
        scanner,
        result_sink=sink_factory(telegram),
        interval_seconds=runtime.interval_seconds,
    )


def run_scan_once(*, evaluator, environ=None, api_factory=KiwoomAPI, sink_factory=TelegramScanResultSink):
    """Run exactly one configured scan cycle and publish its result batch."""
    runner = build_scan_runner(
        evaluator=evaluator,
        environ=environ,
        api_factory=api_factory,
        sink_factory=sink_factory,
    )
    return runner.run(max_cycles=1)
