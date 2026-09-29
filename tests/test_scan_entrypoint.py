import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from api.scanner import ScanItem
from api.scan_entrypoint import ScanRuntimeConfig, build_scan_runner, run_scan_once
from api.scan_scheduling import FileRunLock, ScanAlreadyRunningError
from api.telegram_notifications import TelegramDeliveryError


class FakeAPI:
    instances = []

    def __init__(self, *, paper):
        self.paper = paper
        self.calls = []
        self.__class__.instances.append(self)

    @property
    def is_paper(self):
        return self.paper

    def get_daily_chart(self, code, **kwargs):
        self.calls.append((code, kwargs))
        return [
            {
                "date": "20260929",
                "open": 100,
                "high": 110,
                "low": 95,
                "close": 105,
                "volume": 1000,
            }
        ]


class FakeSink:
    instances = []

    def __init__(self, config):
        self.config = config
        self.batches = []
        self.__class__.instances.append(self)

    def __call__(self, batch):
        self.batches.append(batch)
        return True


class ScanRuntimeConfigTests(unittest.TestCase):
    def test_reads_explicit_codes_limit_and_interval_from_environment(self):
        config = ScanRuntimeConfig.from_env(
            {
                "KIWOOM_SCAN_CODES": "005930, 000660",
                "KIWOOM_SCAN_LIMIT": "120",
                "KIWOOM_SCAN_INTERVAL_SECONDS": "600",
            }
        )

        self.assertEqual(config.codes, ("005930", "000660"))
        self.assertEqual(config.limit, 120)
        self.assertEqual(config.interval_seconds, 600.0)

    def test_reads_retry_and_lock_settings_from_environment(self):
        config = ScanRuntimeConfig.from_env(
            {
                "KIWOOM_SCAN_CODES": "005930",
                "KIWOOM_ALERT_MAX_ATTEMPTS": "4",
                "KIWOOM_ALERT_RETRY_SECONDS": "1.5",
                "KIWOOM_SCAN_LOCK_FILE": "automation/runs/scan.lock",
            }
        )

        self.assertEqual(config.alert_max_attempts, 4)
        self.assertEqual(config.alert_retry_seconds, 1.5)
        self.assertEqual(config.lock_file, "automation/runs/scan.lock")

    def test_missing_or_malformed_environment_fails_closed(self):
        invalid_environments = (
            {},
            {"KIWOOM_SCAN_CODES": ""},
            {"KIWOOM_SCAN_CODES": "005930,005930"},
            {"KIWOOM_SCAN_CODES": "005930", "KIWOOM_SCAN_LIMIT": "0"},
            {"KIWOOM_SCAN_CODES": "005930", "KIWOOM_SCAN_INTERVAL_SECONDS": "nan"},
            {"KIWOOM_SCAN_CODES": "005930", "KIWOOM_ALERT_MAX_ATTEMPTS": "0"},
            {"KIWOOM_SCAN_CODES": "005930", "KIWOOM_ALERT_RETRY_SECONDS": "-1"},
            {"KIWOOM_SCAN_CODES": "005930", "KIWOOM_SCAN_LOCK_FILE": ""},
        )

        for environ in invalid_environments:
            with self.subTest(environ=environ), self.assertRaises(ValueError):
                ScanRuntimeConfig.from_env(environ)


class ScanEntrypointTests(unittest.TestCase):
    def setUp(self):
        FakeAPI.instances.clear()
        FakeSink.instances.clear()

    def test_builds_paper_readonly_pipeline_from_environment(self):
        evaluated = []

        def evaluator(code, bars):
            evaluated.append((code, bars))
            return True, "configured signal"

        runner = build_scan_runner(
            evaluator=evaluator,
            environ={
                "KIWOOM_SCAN_CODES": "005930",
                "KIWOOM_SCAN_LIMIT": "1",
                "KIWOOM_SCAN_INTERVAL_SECONDS": "30",
                "TELEGRAM_BOT_TOKEN": "123456:TEST_token",
                "TELEGRAM_CHAT_ID": "123",
            },
            api_factory=FakeAPI,
            sink_factory=FakeSink,
        )

        self.assertTrue(FakeAPI.instances[0].is_paper)
        self.assertEqual(runner.interval_seconds, 30.0)
        batch = runner.scanner.scan_once(base_dt="20260929")
        self.assertEqual(batch, [ScanItem("005930", "MATCH", True, "configured signal", "20260929", 105, 1000)])
        self.assertEqual(FakeAPI.instances[0].calls[0][1]["limit"], 1)
        self.assertEqual(len(evaluated), 1)

    def test_run_scan_once_publishes_exactly_one_cycle(self):
        cycles = run_scan_once(
            evaluator=lambda _code, _bars: (False, "no signal"),
            environ={
                "KIWOOM_SCAN_CODES": "005930",
                "TELEGRAM_BOT_TOKEN": "123456:TEST_token",
                "TELEGRAM_CHAT_ID": "123",
            },
            api_factory=FakeAPI,
            sink_factory=FakeSink,
        )

        self.assertEqual(cycles, 1)
        self.assertEqual(len(FakeSink.instances[0].batches), 1)

    def test_entrypoint_retries_only_telegram_delivery_failure(self):
        class FlakySink(FakeSink):
            def __call__(self, batch):
                self.batches.append(batch)
                if len(self.batches) == 1:
                    raise TelegramDeliveryError("temporary")
                return True

        cycles = run_scan_once(
            evaluator=lambda _code, _bars: (False, "no signal"),
            environ={
                "KIWOOM_SCAN_CODES": "005930",
                "KIWOOM_ALERT_MAX_ATTEMPTS": "2",
                "KIWOOM_ALERT_RETRY_SECONDS": "0",
                "TELEGRAM_BOT_TOKEN": "123456:TEST_token",
                "TELEGRAM_CHAT_ID": "123",
            },
            api_factory=FakeAPI,
            sink_factory=FlakySink,
        )

        self.assertEqual(cycles, 1)
        self.assertEqual(len(FlakySink.instances[-1].batches), 2)

    def test_lock_conflict_blocks_before_api_construction(self):
        with TemporaryDirectory() as directory:
            lock_file = str(Path(directory) / "scan.lock")
            environ = {
                "KIWOOM_SCAN_CODES": "005930",
                "KIWOOM_SCAN_LOCK_FILE": lock_file,
                "TELEGRAM_BOT_TOKEN": "123456:TEST_token",
                "TELEGRAM_CHAT_ID": "123",
            }

            with FileRunLock(lock_file), self.assertRaises(ScanAlreadyRunningError):
                run_scan_once(
                    evaluator=lambda _code, _bars: (False, "no signal"),
                    environ=environ,
                    api_factory=FakeAPI,
                    sink_factory=FakeSink,
                )

            self.assertEqual(FakeAPI.instances, [])

    def test_rejects_non_paper_api_before_market_data_request(self):
        class UnsafeAPI(FakeAPI):
            def __init__(self, *, paper):
                super().__init__(paper=False)

        with self.assertRaisesRegex(RuntimeError, "paper mode"):
            build_scan_runner(
                evaluator=lambda _code, _bars: (False, "no signal"),
                environ={
                    "KIWOOM_SCAN_CODES": "005930",
                    "TELEGRAM_BOT_TOKEN": "123456:TEST_token",
                    "TELEGRAM_CHAT_ID": "123",
                },
                api_factory=UnsafeAPI,
                sink_factory=FakeSink,
            )

        self.assertEqual(UnsafeAPI.instances[-1].calls, [])


if __name__ == "__main__":
    unittest.main()
