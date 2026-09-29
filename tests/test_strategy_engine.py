import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from api.strategy_engine import (
    AmbiguousPositionError,
    MarketDataRequiredError,
    PerStockStrategyEngine,
    StrategyNotConfiguredError,
)


class FakeManager:
    def __init__(self, positions):
        self.positions = positions
        self.sell_calls = []

    def get_all_balances(self):
        return {"all_positions": list(self.positions)}

    def sell_stock(self, account_id, code, qty):
        self.sell_calls.append((account_id, code, qty))
        return {"status": "filled", "simulated": True}


def position(code, pl_pct, account_id="paper-1", qty=2):
    return {
        "code": code,
        "account_id": account_id,
        "account_name": f"Paper account {account_id}",
        "broker": "kiwoom",
        "pl_pct": pl_pct,
        "qty": qty,
        "cur": 10_000,
    }


class StrategyEngineSelectionTests(unittest.TestCase):
    def test_run_single_evaluates_only_requested_position(self):
        manager = FakeManager([position("005930", -45), position("000660", -45)])
        engine = PerStockStrategyEngine(manager)
        engine.set_strategy("005930", "RESCUE")

        result = engine.run_single("005930", lambda _code: {})

        self.assertEqual(result["code"], "005930")
        self.assertTrue(result["should_sell"])
        self.assertEqual(manager.sell_calls, [("paper-1", "005930", 2)])

    def test_run_single_returns_error_for_unknown_position(self):
        engine = PerStockStrategyEngine(FakeManager([position("005930", 0)]))

        self.assertEqual(
            engine.run_single("000660", lambda _code: {}),
            {"error": "000660 보유종목 없음"},
        )

    def test_run_selected_preserves_requested_order(self):
        manager = FakeManager([position("005930", 0), position("000660", 0)])
        engine = PerStockStrategyEngine(manager)
        engine.set_strategy("005930", "FACTOR")
        engine.set_strategy("000660", "FACTOR")

        results = engine.run_selected(
            ["000660", "999999", "005930"],
            lambda _code: {"factor_total": 60},
        )

        self.assertEqual([result["code"] if "code" in result else result["error"] for result in results], [
            "000660",
            "999999 보유종목 없음",
            "005930",
        ])
        self.assertEqual(manager.sell_calls, [])

    def test_missing_market_data_provider_fails_before_sell(self):
        manager = FakeManager([position("005930", -45)])
        engine = PerStockStrategyEngine(manager)
        engine.set_strategy("005930", "RESCUE")

        with self.assertRaises(MarketDataRequiredError):
            engine.run_single("005930")

        self.assertEqual(manager.sell_calls, [])

    def test_missing_strategy_fails_before_provider_or_sell(self):
        manager = FakeManager([position("005930", -45)])
        engine = PerStockStrategyEngine(manager)
        provider_calls = []

        with self.assertRaises(StrategyNotConfiguredError):
            engine.run_single(
                "005930",
                lambda code: provider_calls.append(code) or {},
            )

        self.assertEqual(provider_calls, [])
        self.assertEqual(manager.sell_calls, [])

    def test_malformed_market_data_fails_before_sell(self):
        manager = FakeManager([position("005930", -45)])
        engine = PerStockStrategyEngine(manager)
        engine.set_strategy("005930", "RESCUE")

        with self.assertRaisesRegex(ValueError, "market data"):
            engine.run_single("005930", lambda _code: None)

        self.assertEqual(manager.sell_calls, [])

    def test_run_preflights_every_position_before_any_sell(self):
        manager = FakeManager([position("005930", -45), position("000660", -45)])
        engine = PerStockStrategyEngine(manager)
        engine.set_strategy("005930", "RESCUE")

        with self.assertRaises(StrategyNotConfiguredError):
            engine.run(lambda _code: {})

        self.assertEqual(manager.sell_calls, [])

    def test_run_selected_preflights_market_data_before_any_sell(self):
        manager = FakeManager([position("005930", -45), position("000660", -45)])
        engine = PerStockStrategyEngine(manager)
        engine.set_strategy("005930", "RESCUE")
        engine.set_strategy("000660", "RESCUE")

        def provider(code):
            return {} if code == "005930" else None

        with self.assertRaisesRegex(ValueError, "market data"):
            engine.run_selected(["005930", "000660"], provider)

        self.assertEqual(manager.sell_calls, [])

    def test_run_evaluates_all_positions_before_executing_actions(self):
        events = []
        manager = FakeManager([position("005930", -45), position("000660", -45)])

        def sell_stock(account_id, code, qty):
            events.append(f"sell:{code}")
            return FakeManager.sell_stock(manager, account_id, code, qty)

        manager.sell_stock = sell_stock
        engine = PerStockStrategyEngine(manager)
        engine.set_strategy("005930", "RESCUE")
        engine.set_strategy("000660", "RESCUE")

        actions = engine.run(
            lambda code: events.append(f"data:{code}") or {}
        )

        self.assertEqual(
            events,
            ["data:005930", "data:000660", "sell:005930", "sell:000660"],
        )
        self.assertTrue(all(action["should_sell"] for action in actions))

    def test_duplicate_selected_code_is_rejected_before_evaluation(self):
        manager = FakeManager([position("005930", -45)])
        engine = PerStockStrategyEngine(manager)
        engine.set_strategy("005930", "RESCUE")
        provider_calls = []

        with self.assertRaisesRegex(ValueError, "unique"):
            engine.run_selected(
                ["005930", "005930"],
                lambda code: provider_calls.append(code) or {},
            )

        self.assertEqual(provider_calls, [])
        self.assertEqual(manager.sell_calls, [])

    def test_run_single_rejects_same_code_held_in_multiple_accounts(self):
        manager = FakeManager(
            [
                position("005930", -45, "paper-1"),
                position("005930", -45, "paper-2"),
            ]
        )
        engine = PerStockStrategyEngine(manager)
        engine.set_strategy("005930", "RESCUE")
        provider_calls = []

        with self.assertRaises(AmbiguousPositionError):
            engine.run_single(
                "005930",
                lambda code: provider_calls.append(code) or {},
            )

        self.assertEqual(provider_calls, [])
        self.assertEqual(manager.sell_calls, [])

    def test_run_account_position_targets_only_the_explicit_account(self):
        manager = FakeManager(
            [
                position("005930", -45, "paper-1"),
                position("005930", -45, "paper-2"),
            ]
        )
        engine = PerStockStrategyEngine(manager)
        engine.set_strategy("005930", "RESCUE")

        result = engine.run_account_position(
            "paper-2",
            "005930",
            lambda _code: {},
        )

        self.assertEqual(result["account_id"], "paper-2")
        self.assertEqual(manager.sell_calls, [("paper-2", "005930", 2)])

    def test_run_selected_rejects_ambiguous_holding_before_evaluation(self):
        manager = FakeManager(
            [
                position("005930", -45, "paper-1"),
                position("005930", -45, "paper-2"),
            ]
        )
        engine = PerStockStrategyEngine(manager)
        engine.set_strategy("005930", "RESCUE")
        provider_calls = []

        with self.assertRaises(AmbiguousPositionError):
            engine.run_selected(
                ["005930"],
                lambda code: provider_calls.append(code) or {},
            )

        self.assertEqual(provider_calls, [])
        self.assertEqual(manager.sell_calls, [])

    def test_rescue_partial_exit_sells_half_once_with_odd_quantity_rounded_up(self):
        manager = FakeManager([position("005930", -25, qty=5)])
        engine = PerStockStrategyEngine(manager)
        engine.set_strategy("005930", "RESCUE")

        first = engine.run_single("005930", lambda _code: {})
        second = engine.run_single("005930", lambda _code: {})

        self.assertEqual(first["sell_fraction"], 0.5)
        self.assertEqual(first["sell_qty"], 3)
        self.assertTrue(first["should_sell"])
        self.assertFalse(second["should_sell"])
        self.assertEqual(second["sell_qty"], 0)
        self.assertEqual(manager.sell_calls, [("paper-1", "005930", 3)])

    def test_factor_partial_exit_sells_half_quantity(self):
        manager = FakeManager([position("005930", 0, qty=4)])
        engine = PerStockStrategyEngine(manager)
        engine.set_strategy("005930", "FACTOR")

        result = engine.run_single(
            "005930",
            lambda _code: {"factor_total": 45, "is_bounce": True},
        )

        self.assertEqual(result["sell_fraction"], 0.5)
        self.assertEqual(result["sell_qty"], 2)
        self.assertEqual(manager.sell_calls, [("paper-1", "005930", 2)])

    def test_immediate_exit_can_sell_remainder_after_partial_exit(self):
        pos = position("005930", -25, qty=5)
        manager = FakeManager([pos])
        engine = PerStockStrategyEngine(manager)
        engine.set_strategy("005930", "RESCUE")

        engine.run_single("005930", lambda _code: {})
        pos["qty"] = 2
        pos["pl_pct"] = -45
        result = engine.run_single("005930", lambda _code: {})

        self.assertEqual(result["sell_fraction"], 1.0)
        self.assertEqual(result["sell_qty"], 2)
        self.assertEqual(
            manager.sell_calls,
            [("paper-1", "005930", 3), ("paper-1", "005930", 2)],
        )

    def test_failed_partial_exit_is_not_latched(self):
        manager = FakeManager([position("005930", -25, qty=4)])

        def fail_sell(account_id, code, qty):
            manager.sell_calls.append((account_id, code, qty))
            return {"error": "paper failure"}

        manager.sell_stock = fail_sell
        engine = PerStockStrategyEngine(manager)
        engine.set_strategy("005930", "RESCUE")

        first = engine.run_single("005930", lambda _code: {})
        second = engine.run_single("005930", lambda _code: {})

        self.assertEqual(first["executed"], {"error": "paper failure"})
        self.assertTrue(second["should_sell"])
        self.assertEqual(
            manager.sell_calls,
            [("paper-1", "005930", 2), ("paper-1", "005930", 2)],
        )

    def test_partial_exit_state_suppresses_duplicate_after_restart(self):
        with TemporaryDirectory() as directory:
            state_file = str(Path(directory) / "partial-exits.json")
            first_manager = FakeManager([position("005930", -25, qty=4)])
            first_engine = PerStockStrategyEngine(
                first_manager,
                partial_exit_state_file=state_file,
            )
            first_engine.set_strategy("005930", "RESCUE")
            first_engine.run_single("005930", lambda _code: {})

            second_manager = FakeManager([position("005930", -25, qty=4)])
            second_engine = PerStockStrategyEngine(
                second_manager,
                partial_exit_state_file=state_file,
            )
            second_engine.set_strategy("005930", "RESCUE")
            result = second_engine.run_single("005930", lambda _code: {})

            self.assertFalse(result["should_sell"])
            self.assertEqual(second_manager.sell_calls, [])

    def test_partial_exit_reservation_is_persisted_before_sell(self):
        with TemporaryDirectory() as directory:
            state_file = Path(directory) / "partial-exits.json"
            manager = FakeManager([position("005930", -25, qty=4)])

            def verify_pending_then_sell(account_id, code, qty):
                payload = json.loads(state_file.read_text(encoding="utf-8"))
                self.assertEqual(payload["entries"][0]["status"], "pending")
                return FakeManager.sell_stock(manager, account_id, code, qty)

            manager.sell_stock = verify_pending_then_sell
            engine = PerStockStrategyEngine(
                manager,
                partial_exit_state_file=str(state_file),
            )
            engine.set_strategy("005930", "RESCUE")

            engine.run_single("005930", lambda _code: {})

            payload = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(payload["entries"][0]["status"], "filled")

    def test_failed_partial_exit_is_released_from_durable_state(self):
        with TemporaryDirectory() as directory:
            state_file = str(Path(directory) / "partial-exits.json")
            first_manager = FakeManager([position("005930", -25, qty=4)])
            first_manager.sell_stock = lambda *_args: {"error": "paper failure"}
            first_engine = PerStockStrategyEngine(
                first_manager,
                partial_exit_state_file=state_file,
            )
            first_engine.set_strategy("005930", "RESCUE")
            first_engine.run_single("005930", lambda _code: {})

            second_manager = FakeManager([position("005930", -25, qty=4)])
            second_engine = PerStockStrategyEngine(
                second_manager,
                partial_exit_state_file=state_file,
            )
            second_engine.set_strategy("005930", "RESCUE")
            result = second_engine.run_single("005930", lambda _code: {})

            self.assertTrue(result["should_sell"])
            self.assertEqual(second_manager.sell_calls, [("paper-1", "005930", 2)])

    def test_partial_exit_exception_remains_pending_after_restart(self):
        with TemporaryDirectory() as directory:
            state_file = str(Path(directory) / "partial-exits.json")
            first_manager = FakeManager([position("005930", -25, qty=4)])

            def uncertain_sell(*_args):
                raise RuntimeError("broker result unknown")

            first_manager.sell_stock = uncertain_sell
            first_engine = PerStockStrategyEngine(
                first_manager,
                partial_exit_state_file=state_file,
            )
            first_engine.set_strategy("005930", "RESCUE")

            with self.assertRaisesRegex(RuntimeError, "result unknown"):
                first_engine.run_single("005930", lambda _code: {})

            second_manager = FakeManager([position("005930", -25, qty=4)])
            second_engine = PerStockStrategyEngine(
                second_manager,
                partial_exit_state_file=state_file,
            )
            second_engine.set_strategy("005930", "RESCUE")
            result = second_engine.run_single("005930", lambda _code: {})

            self.assertFalse(result["should_sell"])
            self.assertEqual(second_manager.sell_calls, [])

    def test_corrupt_partial_exit_state_fails_before_evaluation(self):
        with TemporaryDirectory() as directory:
            state_file = Path(directory) / "partial-exits.json"
            state_file.write_text("not-json", encoding="utf-8")
            manager = FakeManager([position("005930", -25, qty=4)])

            with self.assertRaisesRegex(ValueError, "partial-exit state file"):
                PerStockStrategyEngine(
                    manager,
                    partial_exit_state_file=str(state_file),
                )

            self.assertEqual(manager.sell_calls, [])

    def test_unwritable_partial_exit_state_fails_before_sell(self):
        with TemporaryDirectory() as directory:
            blocked_parent = Path(directory) / "not-a-directory"
            blocked_parent.write_text("blocked", encoding="utf-8")
            manager = FakeManager([position("005930", -25, qty=4)])
            engine = PerStockStrategyEngine(
                manager,
                partial_exit_state_file=str(blocked_parent / "state.json"),
            )
            engine.set_strategy("005930", "RESCUE")

            with self.assertRaisesRegex(RuntimeError, "partial-exit state"):
                engine.run_single("005930", lambda _code: {})

            self.assertEqual(manager.sell_calls, [])

    def test_explicit_reset_allows_a_new_partial_exit_campaign(self):
        with TemporaryDirectory() as directory:
            state_file = str(Path(directory) / "partial-exits.json")
            manager = FakeManager([position("005930", -25, qty=4)])
            engine = PerStockStrategyEngine(
                manager,
                partial_exit_state_file=state_file,
            )
            engine.set_strategy("005930", "RESCUE")
            engine.run_single("005930", lambda _code: {})

            self.assertTrue(engine.reset_partial_exit("paper-1", "005930"))
            engine.run_single("005930", lambda _code: {})

            self.assertEqual(
                manager.sell_calls,
                [("paper-1", "005930", 2), ("paper-1", "005930", 2)],
            )


if __name__ == "__main__":
    unittest.main()
