import unittest

from api.multi_broker_api import KBAdapter, NHAdapter, SamsungAdapter
from order import LiveOrderDisabledError


class MultiBrokerOrderSafetyTests(unittest.TestCase):
    def test_non_paper_adapters_reject_buy_and_sell(self):
        adapters = (
            NHAdapter({"id": "nh", "broker": "nh", "paper": False}),
            SamsungAdapter({"id": "samsung", "broker": "samsung", "paper": False}),
            KBAdapter({"id": "kb", "broker": "kb", "paper": False}),
        )

        for adapter in adapters:
            with self.subTest(broker=adapter.broker):
                with self.assertRaises(LiveOrderDisabledError):
                    adapter.buy_market("005930", 1)
                with self.assertRaises(LiveOrderDisabledError):
                    adapter.sell_market("005930", 1)

    def test_paper_adapters_keep_mock_order_behavior(self):
        adapters = (
            NHAdapter({"id": "nh", "broker": "nh", "paper": True}),
            SamsungAdapter({"id": "samsung", "broker": "samsung", "paper": True}),
            KBAdapter({"id": "kb", "broker": "kb", "paper": True}),
        )

        for adapter in adapters:
            with self.subTest(broker=adapter.broker):
                self.assertEqual(adapter.buy_market("005930", 1)["status"], "filled")
                self.assertEqual(adapter.sell_market("005930", 1)["status"], "filled")


if __name__ == "__main__":
    unittest.main()
