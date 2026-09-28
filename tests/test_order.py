import unittest

from order import (
    LiveOrderDisabledError,
    OrderExecutor,
    OrderRequest,
    OrderSide,
    OrderType,
    OrderValidationError,
    validate_order,
)


class OrderRequestTests(unittest.TestCase):
    def test_market_order_accepts_string_side(self):
        request = OrderRequest("005930", "buy", 2)

        self.assertEqual(request.side, OrderSide.BUY)
        self.assertEqual(request.order_type, OrderType.MARKET)

    def test_limit_order_requires_positive_price(self):
        with self.assertRaises(OrderValidationError):
            OrderRequest("005930", OrderSide.BUY, 1, OrderType.LIMIT)

        request = OrderRequest("005930", OrderSide.BUY, 1, OrderType.LIMIT, limit_price=70_000)
        self.assertEqual(request.limit_price, 70_000)

    def test_invalid_code_and_quantity_are_rejected(self):
        for code in ("5930", "005930 ", "A005930"):
            with self.subTest(code=code), self.assertRaises(OrderValidationError):
                OrderRequest(code, OrderSide.BUY, 1)

        for quantity in (0, -1, True, 1.5):
            with self.subTest(quantity=quantity), self.assertRaises(OrderValidationError):
                OrderRequest("005930", OrderSide.BUY, quantity)


class OrderExecutorTests(unittest.TestCase):
    def test_dry_run_never_calls_transport(self):
        class ForbiddenTransport:
            def __getattr__(self, name):
                raise AssertionError(f"transport must not be called: {name}")

        result = OrderExecutor(transport=ForbiddenTransport()).buy_market("005930", 1)

        self.assertTrue(result.simulated)
        self.assertEqual(result.status.value, "accepted")
        self.assertIn("no broker", result.message)

    def test_client_order_id_is_preserved(self):
        result = OrderExecutor().sell_market("000660", 3, client_order_id="exit-001")

        self.assertEqual(result.order_id, "exit-001")
        self.assertEqual(result.request.side, OrderSide.SELL)

    def test_live_mode_is_fail_closed(self):
        with self.assertRaises(LiveOrderDisabledError):
            OrderExecutor(dry_run=False).buy_market("005930", 1)


class ValidationMappingTests(unittest.TestCase):
    def test_validate_order_builds_request(self):
        request = validate_order({"code": "035720", "side": "SELL", "quantity": 4})

        self.assertEqual(request.code, "035720")
        self.assertEqual(request.side, OrderSide.SELL)

    def test_validate_order_reports_missing_fields(self):
        with self.assertRaisesRegex(OrderValidationError, "code"):
            validate_order({"side": "BUY", "quantity": 1})


if __name__ == "__main__":
    unittest.main()
