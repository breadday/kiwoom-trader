import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from api.multi_broker_api import MultiAccountManager


class FakeAdapter:
    def __init__(self, broker, name, balance):
        self.broker = broker
        self.name = name
        self._balance = balance

    def get_balance(self):
        return self._balance


def manager_with_adapters(adapters):
    manager = MultiAccountManager.__new__(MultiAccountManager)
    manager.adapters = adapters
    return manager


class MultiAccountManagerConfigTests(unittest.TestCase):
    def test_missing_config_does_not_create_implicit_mock_accounts(self):
        with TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.yaml"

            with self.assertRaisesRegex(FileNotFoundError, "accounts config"):
                MultiAccountManager(missing)

    def test_unknown_broker_fails_instead_of_silently_dropping_account(self):
        with TemporaryDirectory() as directory:
            config = Path(directory) / "accounts.yaml"
            config.write_text(
                "accounts:\n  - id: unknown\n    broker: unsupported\n    paper: true\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unsupported broker"):
                MultiAccountManager(config)

    def test_duplicate_account_ids_fail_closed(self):
        with TemporaryDirectory() as directory:
            config = Path(directory) / "accounts.yaml"
            config.write_text(
                "accounts:\n"
                "  - id: duplicate\n    broker: nh\n    paper: true\n"
                "  - id: duplicate\n    broker: kb\n    paper: true\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "duplicate account id"):
                MultiAccountManager(config)

    def test_malformed_accounts_document_fails_closed(self):
        with TemporaryDirectory() as directory:
            config = Path(directory) / "accounts.yaml"
            config.write_text("accounts: not-a-list\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "accounts must be a list"):
                MultiAccountManager(config)

    def test_explicit_paper_accounts_load_in_configured_order(self):
        with TemporaryDirectory() as directory:
            config = Path(directory) / "accounts.yaml"
            config.write_text(
                "accounts:\n"
                "  - id: nh-paper\n    name: NH paper\n    broker: nh\n    paper: true\n"
                "  - id: kb-paper\n    name: KB paper\n    broker: kb\n    paper: true\n",
                encoding="utf-8",
            )

            manager = MultiAccountManager(config)

            self.assertEqual(list(manager.adapters), ["nh-paper", "kb-paper"])
            self.assertTrue(all(adapter.paper for adapter in manager.adapters.values()))


class MultiAccountManagerBalanceTests(unittest.TestCase):
    def test_valid_balances_are_aggregated_without_merging_same_code(self):
        manager = manager_with_adapters(
            {
                "first": FakeAdapter(
                    "nh",
                    "NH paper",
                    {
                        "cash": 1000,
                        "positions": {
                            "005930": {"qty": 2, "avg": 100, "cur": 120}
                        },
                    },
                ),
                "second": FakeAdapter(
                    "kb",
                    "KB paper",
                    {
                        "cash": 500,
                        "positions": {
                            "005930": {"qty": 1, "avg": 200, "cur": 180}
                        },
                    },
                ),
            }
        )

        result = manager.get_all_balances()

        self.assertEqual(result["summary"]["total_cash"], 1500)
        self.assertEqual(result["summary"]["total_eval"], 420)
        self.assertEqual(result["summary"]["total_buy"], 400)
        self.assertEqual(result["summary"]["total_asset"], 1920)
        self.assertEqual(len(result["all_positions"]), 2)
        self.assertEqual(
            [position["account_id"] for position in result["all_positions"]],
            ["first", "second"],
        )

    def test_malformed_or_nonfinite_balance_fails_before_aggregation(self):
        invalid_balances = (
            None,
            {"cash": -1, "positions": {}},
            {"cash": float("nan"), "positions": {}},
            {"cash": 0, "positions": []},
            {"cash": 0, "positions": {"5930": {"qty": 1, "avg": 1, "cur": 1}}},
            {"cash": 0, "positions": {"005930": {"qty": 0, "avg": 1, "cur": 1}}},
            {"cash": 0, "positions": {"005930": {"qty": True, "avg": 1, "cur": 1}}},
            {"cash": 0, "positions": {"005930": {"qty": 1, "avg": 0, "cur": 1}}},
            {
                "cash": 0,
                "positions": {
                    "005930": {"qty": 1, "avg": 1, "cur": float("inf")}
                },
            },
        )

        for balance in invalid_balances:
            with self.subTest(balance=balance):
                manager = manager_with_adapters(
                    {"invalid": FakeAdapter("nh", "invalid", balance)}
                )
                with self.assertRaisesRegex(ValueError, "balance"):
                    manager.get_all_balances()


if __name__ == "__main__":
    unittest.main()
