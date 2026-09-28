import unittest
from unittest.mock import patch

from api.kiwoom_api import KiwoomAPI
from order import LiveOrderDisabledError, OrderValidationError


class FakeAuth:
    base_url = "https://api.kiwoom.com"

    def headers(self):
        return {"authorization": "Bearer test-token"}


class KiwoomOrderSafetyTests(unittest.TestCase):
    def make_api(self, *, paper=True):
        api = KiwoomAPI(FakeAuth(), paper=paper)
        api._throttle = lambda: None
        return api

    @patch("api.kiwoom_api.requests.post")
    def test_insufficient_paper_cash_is_rejected_without_network(self, post):
        api = self.make_api()
        api.paper_balance["cash"] = 10

        result = api.buy_market("005930", 1, price=50000)

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason"], "insufficient paper cash")
        post.assert_not_called()

    @patch("api.kiwoom_api.requests.post")
    def test_insufficient_paper_position_is_rejected_without_network(self, post):
        api = self.make_api()
        api.paper_balance["positions"] = {"005930": {"qty": 1, "avg": 50000}}

        result = api.sell_market("005930", 2, price=50000)

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason"], "insufficient paper position")
        post.assert_not_called()

    @patch("api.kiwoom_api.requests.post")
    def test_live_order_is_fail_closed_without_network(self, post):
        api = self.make_api(paper=False)

        with self.assertRaises(LiveOrderDisabledError):
            api.buy_market("005930", 1)

        with self.assertRaises(LiveOrderDisabledError):
            api.sell_market("005930", 1)
        post.assert_not_called()

    @patch("api.kiwoom_api.requests.post")
    def test_invalid_order_is_rejected_before_network(self, post):
        api = self.make_api()

        with self.assertRaises(OrderValidationError):
            api.buy_market("NOT-A-CODE", 1)
        with self.assertRaises(OrderValidationError):
            api.sell_market("005930", 0)
        post.assert_not_called()

    def test_valid_paper_buy_and_sell_update_local_balance(self):
        api = self.make_api()
        starting_cash = api.paper_balance["cash"]

        buy = api.buy_market("005930", 2, price=1000)
        sell = api.sell_market("005930", 1, price=1200)

        self.assertEqual(buy["status"], "filled")
        self.assertEqual(sell["status"], "filled")
        self.assertEqual(api.paper_balance["cash"], starting_cash - 800)
        self.assertEqual(api.paper_balance["positions"]["005930"]["qty"], 1)


if __name__ == "__main__":
    unittest.main()
