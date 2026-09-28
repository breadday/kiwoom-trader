import unittest
from threading import Event

from api.scanner import ReadOnlyMarketScanner, ScanConfig, ScanRunner


def _bars(code):
    offset = int(code[-1])
    return [
        {
            "date": "20260924",
            "open": 100 + offset,
            "high": 105 + offset,
            "low": 99 + offset,
            "close": 103 + offset,
            "volume": 1000 + offset,
        },
        {
            "date": "20260925",
            "open": 103 + offset,
            "high": 110 + offset,
            "low": 102 + offset,
            "close": 108 + offset,
            "volume": 1200 + offset,
        },
    ]


class ReadOnlyMarketScannerTests(unittest.TestCase):
    def test_scans_each_code_once_in_configured_order(self):
        calls = []

        def provider(code, *, base_dt, limit, refresh):
            calls.append((code, base_dt, limit, refresh))
            return _bars(code)

        def evaluator(code, bars):
            return bars[-1]["close"] >= 108, f"latest close for {code}"

        scanner = ReadOnlyMarketScanner(
            ScanConfig(codes=("005930", "000660"), limit=2),
            daily_chart_provider=provider,
            evaluator=evaluator,
        )

        results = scanner.scan_once(base_dt="20260925", refresh=True)

        self.assertEqual(
            calls,
            [
                ("005930", "20260925", 2, True),
                ("000660", "20260925", 2, True),
            ],
        )
        self.assertEqual([item.code for item in results], ["005930", "000660"])
        self.assertEqual([item.status for item in results], ["MATCH", "MATCH"])
        self.assertEqual(results[0].latest_date, "20260925")
        self.assertEqual(results[0].latest_close, 108)
        self.assertEqual(results[0].latest_volume, 1200)

    def test_provider_failure_isolated_as_fail_closed_error(self):
        evaluated = []

        def provider(code, **_kwargs):
            if code == "005930":
                raise RuntimeError("provider unavailable")
            return _bars(code)

        def evaluator(code, _bars):
            evaluated.append(code)
            return False, "no signal"

        scanner = ReadOnlyMarketScanner(
            ScanConfig(codes=("005930", "000660"), limit=2),
            daily_chart_provider=provider,
            evaluator=evaluator,
        )

        results = scanner.scan_once(base_dt="20260925")

        self.assertEqual(results[0].status, "ERROR")
        self.assertIn("provider unavailable", results[0].reason)
        self.assertFalse(results[0].matched)
        self.assertEqual(results[1].status, "NO_MATCH")
        self.assertEqual(evaluated, ["000660"])

    def test_invalid_or_duplicate_codes_fail_before_provider_call(self):
        provider_calls = []

        def provider(*args, **kwargs):
            provider_calls.append((args, kwargs))

        for codes in ((), ("5930",), ("005930", "005930")):
            with self.subTest(codes=codes):
                with self.assertRaises(ValueError):
                    ReadOnlyMarketScanner(
                        ScanConfig(codes=codes),
                        daily_chart_provider=provider,
                        evaluator=lambda _code, _bars: (False, "no signal"),
                    )

        self.assertEqual(provider_calls, [])

    def test_empty_or_malformed_bars_never_reach_evaluator(self):
        evaluated = []

        def evaluator(code, bars):
            evaluated.append((code, bars))
            return True, "unsafe"

        for payload in ([], [{"date": "20260925", "close": 100}]):
            with self.subTest(payload=payload):
                scanner = ReadOnlyMarketScanner(
                    ScanConfig(codes=("005930",)),
                    daily_chart_provider=lambda *_args, **_kwargs: payload,
                    evaluator=evaluator,
                )
                result = scanner.scan_once()[0]
                self.assertEqual(result.status, "ERROR")
                self.assertFalse(result.matched)

        self.assertEqual(evaluated, [])


class ScanRunnerTests(unittest.TestCase):
    def test_runner_publishes_bounded_cycles_without_order_execution(self):
        class FakeScanner:
            def __init__(self):
                self.calls = 0

            def scan_once(self):
                self.calls += 1
                return [f"cycle-{self.calls}"]

        scanner = FakeScanner()
        published = []
        waits = []
        stop_event = Event()
        stop_event.wait = lambda seconds: waits.append(seconds) or False
        runner = ScanRunner(
            scanner,
            result_sink=published.append,
            interval_seconds=30,
        )

        cycles = runner.run(max_cycles=2, stop_event=stop_event)

        self.assertEqual(cycles, 2)
        self.assertEqual(scanner.calls, 2)
        self.assertEqual(published, [["cycle-1"], ["cycle-2"]])
        self.assertEqual(waits, [30])


if __name__ == "__main__":
    unittest.main()
