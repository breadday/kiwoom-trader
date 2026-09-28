import unittest

from api.scanner import ScanItem
from api.telegram_notifications import (
    TelegramConfig,
    TelegramDeliveryError,
    TelegramScanResultSink,
)


class FakeResponse:
    def __init__(self, *, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = {"ok": True} if payload is None else payload

    def json(self):
        return self._payload


class TelegramScanResultSinkTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
