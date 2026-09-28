import unittest

from api.strategy_engine import PerStockStrategyEngine


class FakeManager:
    def __init__(self, positions):
        self.positions = positions
        self.sell_calls = []

    def get_all_balances(self):
        return {"all_positions": list(self.positions)}

    def sell_stock(self, account_id, code, qty):
        self.sell_calls.append((account_id, code, qty))
        return {"status": "filled", "simulated": True}


def position(code, pl_pct):
    return {
        "code": code,
        "account_id": "paper-1",
        "account_name": "Paper account",
        "broker": "kiwoom",
        "pl_pct": pl_pct,
        "qty": 2,
        "cur": 10_000,
    }


class StrategyEngineSelectionTests(unittest.TestCase):
    def test_run_single_evaluates_only_requested_position(self):
        manager = FakeManager([position("005930", -45), position("000660", -45)])
        engine = PerStockStrategyEngine(manager)
        engine.set_strategy("005930", "RESCUE")

        result = engine.run_single("005930")

        self.assertEqual(result["code"], "005930")
        self.assertTrue(result["should_sell"])
        self.assertEqual(manager.sell_calls, [("paper-1", "005930", 2)])

    def test_run_single_returns_error_for_unknown_position(self):
        engine = PerStockStrategyEngine(FakeManager([position("005930", 0)]))

        self.assertEqual(engine.run_single("000660"), {"error": "000660 보유종목 없음"})

    def test_run_selected_preserves_requested_order(self):
        manager = FakeManager([position("005930", 0), position("000660", 0)])
        engine = PerStockStrategyEngine(manager)

        results = engine.run_selected(["000660", "999999", "005930"])

        self.assertEqual([result["code"] if "code" in result else result["error"] for result in results], [
            "000660",
            "999999 보유종목 없음",
            "005930",
        ])
        self.assertEqual(manager.sell_calls, [])


if __name__ == "__main__":
    unittest.main()
