from pathlib import Path
import json
import os
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from api.scan_scheduling import FileRunLock
from api.strategy_engine import PerStockStrategyEngine
from api.strategy_execution_state import (
    PartialExitStateBusyError,
    PartialExitStateStore,
)
from tests.test_strategy_engine import FakeManager, position


class PartialExitStateConcurrencyTests(unittest.TestCase):
    def test_rejected_order_release_failure_blocks_restart_until_explicit_reset(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            manager = FakeManager([position("005930", -25, qty=4)])
            attempts = []

            def reject(*args):
                attempts.append(args)
                return {"error": "paper rejection"}

            manager.sell_stock = reject
            engine = PerStockStrategyEngine(manager, partial_exit_state_file=str(path))
            engine.set_strategy("005930", "RESCUE")
            replace = os.replace
            writes = []

            def fail_release(source, destination):
                writes.append(destination)
                if len(writes) == 2:
                    raise OSError("disk failure")
                return replace(source, destination)

            with patch("api.strategy_execution_state.os.replace", side_effect=fail_release):
                with self.assertRaisesRegex(RuntimeError, "could not be written"):
                    engine.run_single("005930", lambda _code: {})
            self.assertEqual(attempts, [("paper-1", "005930", 2)])
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["entries"][0]["status"], "pending")
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])
            restarted_manager = FakeManager([position("005930", -25, qty=4)])
            restarted = PerStockStrategyEngine(restarted_manager, partial_exit_state_file=str(path))
            restarted.set_strategy("005930", "RESCUE")
            self.assertFalse(restarted.run_single("005930", lambda _code: {})["should_sell"])
            self.assertEqual(restarted_manager.sell_calls, [])
            self.assertTrue(restarted.reset_partial_exit("paper-1", "005930"))
            restarted.run_single("005930", lambda _code: {})
            self.assertEqual(restarted_manager.sell_calls, [("paper-1", "005930", 2)])

    def test_failed_explicit_reset_preserves_filled_state(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            manager = FakeManager([position("005930", -25, qty=4)])
            engine = PerStockStrategyEngine(manager, partial_exit_state_file=str(path))
            engine.set_strategy("005930", "RESCUE")
            engine.run_single("005930", lambda _code: {})
            before = path.read_bytes()
            with patch("api.strategy_execution_state.os.replace", side_effect=OSError("disk failure")):
                with self.assertRaisesRegex(RuntimeError, "could not be written"):
                    engine.reset_partial_exit("paper-1", "005930")
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse(engine.run_single("005930", lambda _code: {})["should_sell"])
            self.assertEqual(manager.sell_calls, [("paper-1", "005930", 2)])
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])
            with FileRunLock(f"{path}.lock"):
                pass

    def test_reservation_replace_failure_prevents_sell_and_allows_retry(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            manager = FakeManager([position("005930", -25, qty=4)])
            engine = PerStockStrategyEngine(manager, partial_exit_state_file=str(path))
            engine.set_strategy("005930", "RESCUE")
            with patch("api.strategy_execution_state.os.replace", side_effect=OSError("disk failure")):
                with self.assertRaisesRegex(RuntimeError, "could not be written"):
                    engine.run_single("005930", lambda _code: {})
            self.assertEqual(manager.sell_calls, [])
            self.assertFalse(path.exists())
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])
            engine.run_single("005930", lambda _code: {})
            self.assertEqual(manager.sell_calls, [("paper-1", "005930", 2)])

    def test_confirmation_replace_failure_keeps_pending_and_blocks_restart_sell(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            manager = FakeManager([position("005930", -25, qty=4)])
            engine = PerStockStrategyEngine(manager, partial_exit_state_file=str(path))
            engine.set_strategy("005930", "RESCUE")
            replace = os.replace
            writes = []

            def fail_confirmation(source, destination):
                writes.append(destination)
                if len(writes) == 2:
                    raise OSError("disk failure")
                return replace(source, destination)

            with patch("api.strategy_execution_state.os.replace", side_effect=fail_confirmation):
                with self.assertRaisesRegex(RuntimeError, "could not be written"):
                    engine.run_single("005930", lambda _code: {})
            self.assertEqual(manager.sell_calls, [("paper-1", "005930", 2)])
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["entries"][0]["status"], "pending")
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])
            with FileRunLock(f"{path}.lock"):
                pass
            restarted_manager = FakeManager([position("005930", -25, qty=4)])
            restarted = PerStockStrategyEngine(restarted_manager, partial_exit_state_file=str(path))
            restarted.set_strategy("005930", "RESCUE")
            self.assertFalse(restarted.run_single("005930", lambda _code: {})["should_sell"])
            self.assertEqual(restarted_manager.sell_calls, [])

    def test_lock_io_failure_stops_before_provider_or_sell(self):
        with TemporaryDirectory() as directory:
            state_file = str(Path(directory) / "partial-exits.json")
            manager = FakeManager([position("005930", -25, qty=4)])
            engine = PerStockStrategyEngine(manager, partial_exit_state_file=state_file)
            engine.set_strategy("005930", "RESCUE")
            provider_calls = []
            with patch.object(FileRunLock, "acquire", side_effect=RuntimeError("I/O failure")):
                with self.assertRaisesRegex(RuntimeError, "lock could not be acquired"):
                    engine.run_single("005930", lambda code: provider_calls.append(code) or {})
            self.assertEqual(provider_calls, [])
            self.assertEqual(manager.sell_calls, [])
            self.assertFalse(Path(state_file).exists())

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
