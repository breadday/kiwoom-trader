import statistics
import unittest
from datetime import date, timedelta

from api.strategy_optimizer import StrategyOptimizer


UNIVERSE = (
    "005935", "061220", "067310", "086520",
    "253590", "272210", "441680", "416770",
)


def make_bars(code_index=0, days=312, start_date=date(2025, 1, 1)):
    result = []
    cursor = start_date
    index = 0
    while len(result) < days:
        if cursor.weekday() < 5:
            close = 100.0 + code_index * 4.0 + index * (0.03 + code_index * 0.002)
            result.append({
                "date": cursor.strftime("%Y%m%d"),
                "open": close,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": 1000 + code_index * 100 + index % 7,
            })
            index += 1
        cursor += timedelta(days=1)
    return result


def set_bar(bars, index, close):
    bars[index].update({
        "open": close,
        "high": close + 1,
        "low": close - 1,
        "close": close,
    })


class FactorBacktestTests(unittest.TestCase):
    def test_factor_measurements_match_factor_swing_252_and_60_row_windows(self):
        bars = make_bars(days=312)
        factors = StrategyOptimizer._factor_measurements(bars, 252)
        expected_momentum = bars[232]["close"] / bars[1]["close"] - 1.0
        expected_value = -(bars[252]["close"] / bars[193]["close"] - 1.0)
        expected_returns = [bars[index]["close"] / bars[index - 1]["close"] - 1.0 for index in range(193, 253)]
        expected_lowvol = 1.0 / statistics.stdev(expected_returns)
        self.assertAlmostEqual(factors["mom"], expected_momentum)
        self.assertAlmostEqual(factors["value"], expected_value)
        self.assertAlmostEqual(factors["lowvol"], expected_lowvol)
        self.assertAlmostEqual(factors["quality"], statistics.mean(bar["volume"] for bar in bars[193:253]))

    def test_factor_measurements_reject_nonfinite_derived_returns(self):
        bars = make_bars(days=312)
        bars[231]["close"] = 1e-308
        bars[232]["close"] = 1e308
        with self.assertRaisesRegex(ValueError, "factor measurements must be finite"):
            StrategyOptimizer._factor_measurements(bars, 252)

    def test_low_quality_ties_exclude_exact_bottom_fraction_stably(self):
        qualities = {code: 100.0 for code in UNIVERSE}
        self.assertEqual(
            StrategyOptimizer._exclude_low_quality(qualities),
            set(sorted(UNIVERSE)[:2]),
        )

    def test_low_quality_filter_rejects_nonfinite_measurements(self):
        with self.assertRaisesRegex(ValueError, "factor quality values must be finite"):
            StrategyOptimizer._exclude_low_quality({"005935": float("nan")})

    def test_cross_sectional_percentile_uses_average_ranks_and_excluded_zero(self):
        optimizer = StrategyOptimizer()
        result = optimizer._factor_percentiles(
            {"a": 1.0, "b": 2.0, "c": 2.0, "d": 4.0}, excluded_codes={"d"}
        )
        self.assertEqual(result, {"a": 0.0, "b": 50.0, "c": 50.0, "d": 0.0})

    def test_single_eligible_score_maps_to_neutral_percentile(self):
        result = StrategyOptimizer()._factor_percentiles({"a": 4.0}, excluded_codes=set())
        self.assertEqual(result, {"a": 50.0})

    def test_factor_exit_is_evaluated_on_mondays_and_immediate_has_priority(self):
        bars = make_bars(days=312)
        set_bar(bars, 252, 100.0)
        monday_offsets = [i for i in range(1, 60) if date.fromisoformat(
            bars[252 + i]["date"][:4] + "-" + bars[252 + i]["date"][4:6] + "-" + bars[252 + i]["date"][6:]
        ).weekday() == 0]
        self.assertGreaterEqual(len(monday_offsets), 2)
        monday_offset = monday_offsets[1]
        self.assertEqual(date.fromisoformat(
            bars[252 + monday_offset]["date"][:4] + "-" + bars[252 + monday_offset]["date"][4:6] + "-" + bars[252 + monday_offset]["date"][6:]
        ).weekday(), 0)
        set_bar(bars, 252 + monday_offset - 1, 30.0)
        set_bar(bars, 252 + monday_offset, 35.0)
        set_bar(bars, 252 + monday_offset + 1, 35.0)
        # Below 40 exits all even though a close rebound could qualify the partial rule.
        scores = [50.0] * 60
        scores[monday_offset] = 35.0
        result = StrategyOptimizer()._simulate_factor_trade("005935", bars, scores, days=60)
        self.assertEqual(result.total_trades, 1)
        self.assertAlmostEqual(result.total_return, -65.0, places=6)

    def test_immediate_exit_close_to_close_marks_realized_drawdown(self):
        bars = make_bars(days=312)
        set_bar(bars, 252, 100.0)
        first_monday = next(i for i in range(1, 60) if date.fromisoformat(
            bars[252 + i]["date"][:4] + "-" + bars[252 + i]["date"][4:6] + "-" + bars[252 + i]["date"][6:]
        ).weekday() == 0)
        self.assertEqual(date.fromisoformat(
            bars[252 + first_monday]["date"][:4] + "-" + bars[252 + first_monday]["date"][4:6] + "-" + bars[252 + first_monday]["date"][6:]
        ).weekday(), 0)
        set_bar(bars, 252 + first_monday, 35.0)
        set_bar(bars, 252 + first_monday + 1, 35.0)
        scores = [60.0] * 60
        scores[first_monday] = 35.0
        result = StrategyOptimizer()._simulate_factor_trade("005935", bars, scores, days=60)
        self.assertAlmostEqual(result.total_return, -65.0, places=6)
        self.assertAlmostEqual(result.max_drawdown, 65.0, places=6)

    def test_entry_day_score_is_not_used_as_a_same_close_exit_signal(self):
        bars = make_bars(days=312, start_date=date(2025, 1, 2))
        entry_date = date.fromisoformat(
            bars[252]["date"][:4] + "-" + bars[252]["date"][4:6] + "-" + bars[252]["date"][6:]
        )
        self.assertEqual(entry_date.weekday(), 0)
        scores = [0.0] + [60.0] * 59
        result = StrategyOptimizer()._simulate_factor_trade("005935", bars, scores, days=60)
        self.assertGreater(result.total_return, 0.0)

    def test_monday_close_signal_fills_next_session_open_without_lookahead(self):
        bars = make_bars(days=312)
        set_bar(bars, 252, 100.0)
        monday_offset = next(
            offset for offset in range(1, 59)
            if date.fromisoformat(
                bars[252 + offset]["date"][:4] + "-" + bars[252 + offset]["date"][4:6] + "-" + bars[252 + offset]["date"][6:]
            ).weekday() == 0
        )
        monday_index = 252 + monday_offset
        execution_index = monday_index + 1
        self.assertEqual(date.fromisoformat(
            bars[monday_index]["date"][:4] + "-" + bars[monday_index]["date"][4:6] + "-" + bars[monday_index]["date"][6:]
        ).weekday(), 0)
        set_bar(bars, monday_index - 1, 100.0)
        set_bar(bars, monday_index, 110.0)
        bars[execution_index].update({"open": 80.0, "high": 86.0, "low": 79.0, "close": 85.0})
        scores = [60.0] * 60
        scores[monday_offset] = 35.0

        result = StrategyOptimizer()._simulate_factor_trade("005935", bars, scores, days=60)

        self.assertAlmostEqual(result.total_return, -20.0, places=6)

    def test_final_horizon_monday_signal_does_not_schedule_unfillable_partial(self):
        bars = None
        for day_offset in range(7):
            candidate = make_bars(days=312, start_date=date(2025, 1, 1) + timedelta(days=day_offset))
            final_date = date.fromisoformat(
                candidate[-1]["date"][:4] + "-" + candidate[-1]["date"][4:6] + "-" + candidate[-1]["date"][6:]
            )
            if final_date.weekday() == 0:
                bars = candidate
                break
        self.assertIsNotNone(bars)
        set_bar(bars, 252, 100.0)
        set_bar(bars, len(bars) - 2, 90.0)
        set_bar(bars, len(bars) - 1, 100.0)
        scores = [60.0] * 60
        scores[-1] = 45.0

        result = StrategyOptimizer()._simulate_factor_trade("005935", bars, scores, days=60)

        self.assertAlmostEqual(result.total_return, 0.0, places=6)

    def test_partial_exit_latches_after_rebound_and_recross(self):
        bars = make_bars(days=312)
        set_bar(bars, 252, 100.0)
        mondays = [i for i in range(1, 60) if date.fromisoformat(
            bars[252 + i]["date"][:4] + "-" + bars[252 + i]["date"][4:6] + "-" + bars[252 + i]["date"][6:]
        ).weekday() == 0]
        self.assertGreaterEqual(len(mondays), 3)
        mondays = mondays[1:3]
        self.assertTrue(all(date.fromisoformat(
            bars[252 + offset]["date"][:4] + "-" + bars[252 + offset]["date"][4:6] + "-" + bars[252 + offset]["date"][6:]
        ).weekday() == 0 for offset in mondays))
        scores = [60.0] * 60
        for offset in mondays:
            set_bar(bars, 252 + offset - 1, 70.0)
            set_bar(bars, 252 + offset, 80.0)
            execution_bar = bars[252 + offset + 1]
            execution_bar.update({
                "open": 80.0,
                "low": 79.0,
                "high": max(execution_bar["high"], execution_bar["close"], 81.0),
            })
            scores[offset] = 45.0
        set_bar(bars, len(bars) - 1, 100.0)
        result = StrategyOptimizer()._simulate_factor_trade("005935", bars, scores, days=60)
        # Only the first 50% is sold at 80; remaining 50% is valued at final 100.
        self.assertAlmostEqual(result.total_return, -10.0, places=6)

    def test_factor_universe_fetches_312_bars_once_per_symbol(self):
        calls = []
        data = {code: make_bars(index) for index, code in enumerate(UNIVERSE)}

        def provider(code, *, limit):
            calls.append((code, limit))
            return data[code]

        results = StrategyOptimizer(daily_chart_provider=provider).simulate_factor_universe()
        self.assertEqual(calls, [(code, 312) for code in UNIVERSE])
        self.assertEqual(set(results), set(UNIVERSE))
        self.assertTrue(all(result.strategy_id == "FACTOR" for result in results.values()))

    def test_optimize_factor_returns_one_result_for_requested_in_universe_code(self):
        data = {code: make_bars(index) for index, code in enumerate(UNIVERSE)}
        result = StrategyOptimizer(
            daily_chart_provider=lambda code, *, limit: data[code]
        ).optimize_factor(UNIVERSE[0])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].strategy_id, "FACTOR")

    def test_factor_universe_rejects_impossible_calendar_dates(self):
        data = {code: make_bars(index) for index, code in enumerate(UNIVERSE)}
        for code in UNIVERSE:
            data[code][-1]["date"] = "20251340"
        optimizer = StrategyOptimizer(daily_chart_provider=lambda code, *, limit: data[code])
        with self.assertRaisesRegex(ValueError, "invalid daily chart row"):
            optimizer.simulate_factor_universe()

    def test_factor_universe_rejects_misaligned_dates(self):
        data = {code: make_bars(index) for index, code in enumerate(UNIVERSE)}
        data[UNIVERSE[-1]][-1]["date"] = "20261231"
        optimizer = StrategyOptimizer(daily_chart_provider=lambda code, *, limit: data[code])
        with self.assertRaisesRegex(ValueError, "same dates"):
            optimizer.simulate_factor_universe()

    def test_optimize_factor_requires_a_code_in_approved_universe(self):
        with self.assertRaisesRegex(ValueError, "approved FACTOR universe"):
            StrategyOptimizer().optimize_factor("000001")


if __name__ == "__main__":
    unittest.main()
