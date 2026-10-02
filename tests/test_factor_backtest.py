import unittest

from automation.kiwoom_factor_backtest import validate_complete_universe


class FactorBacktestValidationTests(unittest.TestCase):
    def test_complete_universe_passes_when_every_symbol_has_required_bars(self):
        daily_bars = {"AAA": [1, 2], "BBB": [3, 4]}

        self.assertIsNone(validate_complete_universe(daily_bars, ["AAA", "BBB"], 2))

    def test_missing_and_short_symbols_are_reported_together(self):
        daily_bars = {"AAA": [1], "BBB": []}

        with self.assertRaisesRegex(
            RuntimeError,
            r"FACTOR_BACKTEST_BLOCKED.*AAA: received 1/2.*BBB: received 0/2",
        ):
            validate_complete_universe(daily_bars, ["AAA", "BBB", "CCC"], 2)

    def test_validation_does_not_accept_extra_bars_as_a_substitute_for_missing_symbol(self):
        daily_bars = {"AAA": [1, 2, 3], "BBB": [4, 5]}

        with self.assertRaisesRegex(RuntimeError, r"CCC: received 0/2"):
            validate_complete_universe(daily_bars, ["AAA", "BBB", "CCC"], 2)


if __name__ == "__main__":
    unittest.main()
