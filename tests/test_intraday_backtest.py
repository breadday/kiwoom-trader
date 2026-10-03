import unittest

from automation.kiwoom_intraday_backtest import CostModel, run


def bars(count=40):
    return [
        {
            "datetime": f"20261002{90000 + index:06d}",
            "open": 100 + index * 0.1,
            "high": 101 + index * 0.1,
            "low": 99 + index * 0.1,
            "close": 100 + index * 0.1,
            "volume": 1000,
        }
        for index in range(count)
    ]


class IntradayBacktestTests(unittest.TestCase):
    def test_run_groups_bars_and_applies_explicit_cost_model(self):
        result = run(bars(), 0.7, CostModel(0.001, 0.002, 0.001))
        self.assertEqual(result["days"], 1)
        self.assertIn("trades", result)
        self.assertIn("mdd", result)

    def test_negative_cost_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-negative"):
            run(bars(), 0.7, CostModel(-0.001, 0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
