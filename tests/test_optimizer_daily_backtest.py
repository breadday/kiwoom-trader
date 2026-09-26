import unittest
from datetime import date, timedelta

from api.strategy_optimizer import StrategyOptimizer


def bars_with_closes(changes):
    closes = [100.0] * 60
    for day_index, close in changes.items():
        closes[day_index] = close
    result = []
    start = date(2026, 1, 1)
    for index, close in enumerate(closes):
        result.append({
            "date": (start + timedelta(days=index)).strftime("%Y%m%d"),
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": 1000,
        })
    return result


class DailyBacktestTests(unittest.TestCase):
    def test_partial_threshold_sells_half_and_marks_remainder_at_last_close(self):
        source_bars = bars_with_closes({1: 80, 59: 90})
        calls = []

        def provider(code, *, limit):
            calls.append((code, limit))
            return source_bars

        result = StrategyOptimizer(daily_chart_provider=provider).simulate_trades(
            "005930", "RESCUE", {"immediate_th": -40, "partial_th": -20}, days=60
        )

        self.assertEqual(calls, [("005930", 60)])
        self.assertAlmostEqual(result.total_return, -15.0)
        self.assertEqual(result.total_trades, 1)
        self.assertEqual(result.win_rate, 0.0)

    def test_partial_threshold_is_latched_after_rebound_and_recross(self):
        bars = bars_with_closes({1: 80, 2: 100, 3: 80, 59: 100})
        result = StrategyOptimizer(
            daily_chart_provider=lambda code, *, limit: bars
        ).simulate_trades(
            "005930", "RESCUE", {"immediate_th": -40, "partial_th": -20}, days=60
        )

        self.assertAlmostEqual(result.total_return, -10.0)
        self.assertEqual(result.total_trades, 1)

    def test_immediate_threshold_exits_full_position_before_partial(self):
        result = StrategyOptimizer(
            daily_chart_provider=lambda code, *, limit: bars_with_closes({1: 80})
        ).simulate_trades(
            "005930", "RESCUE", {"immediate_th": -15, "partial_th": -10}, days=60
        )

        self.assertAlmostEqual(result.total_return, -20.0)
        self.assertEqual(result.total_trades, 1)

    def test_requires_exact_requested_history_and_never_uses_mock_fallback(self):
        optimizer = StrategyOptimizer(daily_chart_provider=lambda code, *, limit: bars_with_closes({})[:59])

        with self.assertRaisesRegex(ValueError, "60"):
            optimizer.simulate_trades("UNKNOWN", "RESCUE", {}, days=60)

    def test_rescue_grid_fetches_daily_history_once_for_all_parameter_sets(self):
        calls = []
        source_bars = bars_with_closes({1: 78})

        def provider(code, *, limit):
            calls.append((code, limit))
            return source_bars

        results = StrategyOptimizer(daily_chart_provider=provider).optimize_rescue("005930")

        self.assertEqual(calls, [("005930", 60)])
        self.assertEqual(len(results), 23)
        self.assertEqual(results, sorted(results, key=lambda item: item.score, reverse=True))

    def test_unsupported_factor_optimization_fails_without_fetching_data(self):
        calls = []

        def provider(code, *, limit):
            calls.append((code, limit))
            return bars_with_closes({})

        optimizer = StrategyOptimizer(daily_chart_provider=provider)
        with self.assertRaisesRegex(NotImplementedError, "FACTOR"):
            optimizer.optimize_factor("005930")
        self.assertEqual(calls, [])

    def test_all_strategy_optimization_fails_closed_until_factor_rules_exist(self):
        calls = []
        optimizer = StrategyOptimizer(daily_chart_provider=lambda code, *, limit: calls.append(code))

        with self.assertRaisesRegex(NotImplementedError, "FACTOR"):
            optimizer.optimize_all_strategies("005930")
        self.assertEqual(calls, [])

    def test_portfolio_recommendation_does_not_use_synthetic_history(self):
        with self.assertRaisesRegex(NotImplementedError, "data-driven portfolio"):
            StrategyOptimizer(daily_chart_provider=lambda code, *, limit: bars_with_closes({})).recommend_for_portfolio(["005930"])

    def test_fails_closed_when_no_daily_chart_provider_is_configured(self):
        with self.assertRaisesRegex(RuntimeError, "daily chart provider"):
            StrategyOptimizer().simulate_trades("005930", "RESCUE", {}, days=60)


if __name__ == "__main__":
    unittest.main()
