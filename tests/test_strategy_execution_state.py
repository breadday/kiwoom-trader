from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from api.scan_scheduling import FileRunLock
from api.strategy_engine import PerStockStrategyEngine
from api.strategy_execution_state import (
    PartialExitStateBusyError,
    PartialExitStateStore,
)
from tests.test_strategy_engine import FakeManager, position


class PartialExitStateConcurrencyTests(unittest.TestCase):
    def test_stale_store_reloads_before_reserving_same_position(self):
        with TemporaryDirectory() as directory:
            state_file = str(Path(directory) / "partial-exits.json")
            first = PartialExitStateStore(state_file)
            stale = PartialExitStateStore(state_file)

            self.assertTrue(first.reserve("paper-1", "005930", "RESCUE"))
            self.assertFalse(stale.reserve("paper-1", "005930", "RESCUE"))

    def test_lock_contention_fails_before_provider_or_sell(self):
        with TemporaryDirectory() as directory:
            state_file = str(Path(directory) / "partial-exits.json")
            manager = FakeManager([position("005930", -25, qty=4)])
            engine = PerStockStrategyEngine(
                manager,
                partial_exit_state_file=state_file,
            )
            engine.set_strategy("005930", "RESCUE")
            provider_calls = []

            with FileRunLock(f"{state_file}.lock"):
                with self.assertRaises(PartialExitStateBusyError):
                    engine.run_single(
                        "005930",
                        lambda code: provider_calls.append(code) or {},
                    )

            self.assertEqual(provider_calls, [])
            self.assertEqual(manager.sell_calls, [])


if __name__ == "__main__":
    unittest.main()
