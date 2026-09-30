import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from api.scan_scheduling import FileRunLock
from api.scanner import ScanItem
from api.telegram_notifications import (
    TelegramConfig,
    TelegramDeliveryError,
    TelegramScanResultSink,
    TelegramStateBusyError,
)


class FakeResponse:
    def __init__(self, *, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = {"ok": True} if payload is None else payload

    def json(self):
        return self._payload


class TelegramScanResultSinkTests(unittest.TestCase):
    def test_lock_io_failure_stops_before_delivery_or_state_write(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            calls = []
            sink = TelegramScanResultSink(
                TelegramConfig(bot_token="123456:TEST_token", chat_id="123",
                               alert_state_file=str(path)),
                transport=lambda *args, **kwargs: calls.append(kwargs),
            )
            with patch.object(FileRunLock, "acquire", side_effect=RuntimeError("I/O failure")):
                with self.assertRaisesRegex(RuntimeError, "lock could not be acquired"):
                    sink([ScanItem("005930", "MATCH", True, "signal")])
            self.assertEqual(calls, [])
            self.assertFalse(path.exists())

    def test_invalid_state_fields_fail_before_delivery_or_persistence(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            calls = []
            sink = TelegramScanResultSink(
                TelegramConfig(bot_token="123456:TEST_token", chat_id="123",
                               alert_state_file=str(path)),
                transport=lambda *args, **kwargs: calls.append(kwargs),
            )
            for item in (
                ScanItem("bad", "MATCH", True, "signal"),
                ScanItem("005930", "MATCH", True, "signal", "20260230"),
                ScanItem("005930", "MATCH", True, "signal", latest_close=float("nan")),
                ScanItem("005930", "NO_MATCH", False, "clear", latest_volume=-1),
            ):
                with self.subTest(item=item):
                    with self.assertRaises(ValueError):
                        sink([item])
                    self.assertFalse(path.exists())
            self.assertEqual(calls, [])

    def test_zero_volume_and_missing_market_fields_survive_restart(self):
        with TemporaryDirectory() as directory:
            config = TelegramConfig(
                bot_token="123456:TEST_token", chat_id="123",
                alert_state_file=str(Path(directory) / "state.json"),
            )
            calls = []

            def transport(_url, **kwargs):
                calls.append(kwargs)
                return FakeResponse()

            batch = [
                ScanItem("005930", "MATCH", True, "signal", "20260228", 100, 0),
                ScanItem("000660", "ERROR", False, "unavailable"),
            ]
            self.assertTrue(TelegramScanResultSink(config, transport=transport)(batch))
            self.assertFalse(TelegramScanResultSink(config, transport=transport)(batch))
            self.assertEqual(len(calls), 1)

    def test_invalid_persisted_fingerprint_is_rejected(self):
        fingerprints = [
            [[], "signal", None, None, None],
            ["MATCH", "signal", "20260230", 100, 10],
            ["MATCH", "signal", None, float("nan"), 10],
            ["MATCH", "signal", None, float("inf"), 10],
            ["MATCH", "signal", None, True, 10],
            ["MATCH", "signal", None, 0, 10],
            ["MATCH", "signal", None, 100, -1],
            ["MATCH", "signal", None, 100, "10"],
        ]
        with TemporaryDirectory() as directory:
            state_file = Path(directory) / "state.json"
            for fingerprint in fingerprints:
                with self.subTest(fingerprint=fingerprint):
                    state_file.write_text(json.dumps({
                        "version": 1, "states": {"005930": fingerprint},
                    }), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "alert state file"):
                        TelegramScanResultSink(TelegramConfig(
                            bot_token="123456:TEST_token", chat_id="123",
                            alert_state_file=str(state_file),
                        ))

    def test_timeout_rejects_non_finite_and_invalid_values(self):
        for timeout in (float("nan"), float("inf"), float("-inf"), 0, -1, True, "10", None):
            with self.subTest(timeout=timeout):
                with self.assertRaises(ValueError):
                    TelegramConfig(
                        bot_token="123456:TEST_token", chat_id="123",
                        timeout_seconds=timeout,
                    )

    def test_positive_finite_timeout_reaches_transport(self):
        for timeout in (1, 0.25):
            with self.subTest(timeout=timeout):
                calls = []

                def transport(_url, **kwargs):
                    calls.append(kwargs["timeout"])
                    return FakeResponse()

                sink = TelegramScanResultSink(
                    TelegramConfig(
                        bot_token="123456:TEST_token", chat_id="123",
                        timeout_seconds=timeout,
                    ),
                    transport=transport,
                )
                self.assertTrue(sink([ScanItem("005930", "MATCH", True, "signal")]))
                self.assertEqual(calls, [float(timeout)])

    def test_sends_only_matches_and_errors_with_bounded_plain_text(self):
        calls = []

        def transport(url, **kwargs):
            calls.append((url, kwargs))
            return FakeResponse()

        sink = TelegramScanResultSink(
            TelegramConfig(bot_token="123456:TEST_token", chat_id="-100123"),
            transport=transport,
        )
        result = sink(
            [
                ScanItem("005930", "MATCH", True, "breakout", "20260929", 72000, 1000),
                ScanItem("000660", "NO_MATCH", False, "no signal", "20260929", 210000, 500),
                ScanItem("035420", "ERROR", False, "provider unavailable"),
            ]
        )

        self.assertTrue(result)
        self.assertEqual(len(calls), 1)
        url, kwargs = calls[0]
        self.assertEqual(url, "https://api.telegram.org/bot123456:TEST_token/sendMessage")
        self.assertEqual(kwargs["timeout"], 10.0)
        self.assertEqual(kwargs["json"]["chat_id"], "-100123")
        text = kwargs["json"]["text"]
        self.assertIn("MATCH 1 / ERROR 1", text)
        self.assertIn("005930", text)
        self.assertIn("035420", text)
        self.assertNotIn("000660", text)
        self.assertNotIn("parse_mode", kwargs["json"])
        self.assertLessEqual(len(text), 4000)

    def test_no_actionable_results_do_not_call_network(self):
        calls = []
        sink = TelegramScanResultSink(
            TelegramConfig(bot_token="123456:TEST_token", chat_id="123"),
            transport=lambda *args, **kwargs: calls.append((args, kwargs)),
        )

        result = sink([ScanItem("005930", "NO_MATCH", False, "no signal")])

        self.assertFalse(result)
        self.assertEqual(calls, [])

    def test_environment_factory_fails_closed_without_credentials(self):
        for environ in ({}, {"TELEGRAM_BOT_TOKEN": "123456:TEST_token"}):
            with self.subTest(environ=environ):
                with self.assertRaises(ValueError):
                    TelegramConfig.from_env(environ)

    def test_environment_factory_reads_optional_alert_state_file(self):
        config = TelegramConfig.from_env(
            {
                "TELEGRAM_BOT_TOKEN": "123456:TEST_token",
                "TELEGRAM_CHAT_ID": "123",
                "KIWOOM_ALERT_STATE_FILE": "runtime/telegram-alert-state.json",
            }
        )

        self.assertEqual(
            config.alert_state_file,
            "runtime/telegram-alert-state.json",
        )

    def test_delivery_failures_never_expose_token_or_response_body(self):
        token = "123456:SUPER_SECRET_token"
        sink = TelegramScanResultSink(
            TelegramConfig(bot_token=token, chat_id="123"),
            transport=lambda *_args, **_kwargs: FakeResponse(
                status_code=401,
                payload={"ok": False, "description": f"leaked {token}"},
            ),
        )

        with self.assertRaises(TelegramDeliveryError) as context:
            sink([ScanItem("005930", "MATCH", True, "signal")])

        message = str(context.exception)
        self.assertNotIn(token, message)
        self.assertNotIn("leaked", message)

    def test_invalid_batch_is_rejected_before_network(self):
        calls = []
        sink = TelegramScanResultSink(
            TelegramConfig(bot_token="123456:TEST_token", chat_id="123"),
            transport=lambda *args, **kwargs: calls.append((args, kwargs)),
        )

        for batch in (None, "not-a-batch", [object()]):
            with self.subTest(batch=batch):
                with self.assertRaises((TypeError, ValueError)):
                    sink(batch)

        self.assertEqual(calls, [])

    def test_large_actionable_batch_is_truncated_with_omission_count(self):
        messages = []

        def transport(_url, **kwargs):
            messages.append(kwargs["json"]["text"])
            return FakeResponse()

        sink = TelegramScanResultSink(
            TelegramConfig(bot_token="123456:TEST_token", chat_id="123"),
            transport=transport,
        )
        batch = [
            ScanItem(
                f"{index:06d}",
                "MATCH",
                True,
                f"signal-{index} " + ("x" * 1000),
                "20260929",
                1000 + index,
                100,
            )
            for index in range(50)
        ]

        self.assertTrue(sink(batch))
        self.assertEqual(len(messages), 1)
        self.assertLessEqual(len(messages[0]), 4000)
        self.assertIn("more omitted", messages[0])

    def test_identical_actionable_result_is_sent_only_once(self):
        messages = []

        def transport(_url, **kwargs):
            messages.append(kwargs["json"]["text"])
            return FakeResponse()

        sink = TelegramScanResultSink(
            TelegramConfig(bot_token="123456:TEST_token", chat_id="123"),
            transport=transport,
        )
        batch = [
            ScanItem("005930", "MATCH", True, "breakout", "20260929", 72000, 1000)
        ]

        self.assertTrue(sink(batch))
        self.assertFalse(sink(batch))
        self.assertEqual(len(messages), 1)

    def test_no_match_reset_allows_a_later_match_alert(self):
        messages = []

        def transport(_url, **kwargs):
            messages.append(kwargs["json"]["text"])
            return FakeResponse()

        sink = TelegramScanResultSink(
            TelegramConfig(bot_token="123456:TEST_token", chat_id="123"),
            transport=transport,
        )
        match = ScanItem(
            "005930", "MATCH", True, "breakout", "20260929", 72000, 1000
        )

        self.assertTrue(sink([match]))
        self.assertFalse(
            sink(
                [
                    ScanItem(
                        "005930",
                        "NO_MATCH",
                        False,
                        "signal cleared",
                        "20260930",
                        71000,
                        900,
                    )
                ]
            )
        )
        self.assertTrue(sink([match]))
        self.assertEqual(len(messages), 2)

    def test_failed_delivery_is_retried_on_the_next_call(self):
        attempts = []

        def transport(_url, **kwargs):
            attempts.append(kwargs["json"]["text"])
            if len(attempts) == 1:
                return FakeResponse(status_code=503, payload={"ok": False})
            return FakeResponse()

        sink = TelegramScanResultSink(
            TelegramConfig(bot_token="123456:TEST_token", chat_id="123"),
            transport=transport,
        )
        batch = [ScanItem("005930", "ERROR", False, "provider unavailable")]

        with self.assertRaises(TelegramDeliveryError):
            sink(batch)
        self.assertTrue(sink(batch))
        self.assertEqual(len(attempts), 2)

    def test_state_file_suppresses_duplicate_after_process_restart(self):
        with TemporaryDirectory() as directory:
            state_file = str(Path(directory) / "alert-state.json")
            config = TelegramConfig(
                bot_token="123456:TEST_token",
                chat_id="123",
                alert_state_file=state_file,
            )
            calls = []

            def transport(_url, **kwargs):
                calls.append(kwargs["json"]["text"])
                return FakeResponse()

            batch = [
                ScanItem(
                    "005930", "MATCH", True, "breakout", "20260929", 72000, 1000
                )
            ]

            self.assertTrue(TelegramScanResultSink(config, transport=transport)(batch))
            self.assertFalse(TelegramScanResultSink(config, transport=transport)(batch))
            self.assertEqual(len(calls), 1)

    def test_stale_sink_reloads_state_before_sending_duplicate(self):
        with TemporaryDirectory() as directory:
            state_file = str(Path(directory) / "alert-state.json")
            config = TelegramConfig(
                bot_token="123456:TEST_token",
                chat_id="123",
                alert_state_file=state_file,
            )
            calls = []

            def transport(_url, **kwargs):
                calls.append(kwargs["json"]["text"])
                return FakeResponse()

            first = TelegramScanResultSink(config, transport=transport)
            stale = TelegramScanResultSink(config, transport=transport)
            batch = [
                ScanItem(
                    "005930", "MATCH", True, "breakout", "20260929", 72000, 1000
                )
            ]

            self.assertTrue(first(batch))
            self.assertFalse(stale(batch))
            self.assertEqual(len(calls), 1)

    def test_state_lock_contention_fails_before_network(self):
        with TemporaryDirectory() as directory:
            state_file = str(Path(directory) / "alert-state.json")
            calls = []
            sink = TelegramScanResultSink(
                TelegramConfig(
                    bot_token="123456:TEST_token",
                    chat_id="123",
                    alert_state_file=state_file,
                ),
                transport=lambda *args, **kwargs: calls.append((args, kwargs)),
            )

            with FileRunLock(f"{state_file}.lock"):
                with self.assertRaises(TelegramStateBusyError):
                    sink([ScanItem("005930", "MATCH", True, "breakout")])

            self.assertEqual(calls, [])

    def test_persisted_no_match_allows_later_match_after_restart(self):
        with TemporaryDirectory() as directory:
            state_file = str(Path(directory) / "alert-state.json")
            config = TelegramConfig(
                bot_token="123456:TEST_token",
                chat_id="123",
                alert_state_file=state_file,
            )
            calls = []

            def transport(_url, **kwargs):
                calls.append(kwargs["json"]["text"])
                return FakeResponse()

            match = ScanItem(
                "005930", "MATCH", True, "breakout", "20260929", 72000, 1000
            )
            no_match = ScanItem(
                "005930",
                "NO_MATCH",
                False,
                "signal cleared",
                "20260930",
                71000,
                900,
            )

            self.assertTrue(TelegramScanResultSink(config, transport=transport)([match]))
            self.assertFalse(
                TelegramScanResultSink(config, transport=transport)([no_match])
            )
            self.assertTrue(TelegramScanResultSink(config, transport=transport)([match]))
            self.assertEqual(len(calls), 2)

    def test_corrupt_state_file_fails_before_network(self):
        with TemporaryDirectory() as directory:
            state_file = Path(directory) / "alert-state.json"
            state_file.write_text("not-json", encoding="utf-8")
            calls = []

            with self.assertRaisesRegex(ValueError, "alert state file"):
                TelegramScanResultSink(
                    TelegramConfig(
                        bot_token="123456:TEST_token",
                        chat_id="123",
                        alert_state_file=str(state_file),
                    ),
                    transport=lambda *args, **kwargs: calls.append((args, kwargs)),
                )

            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
