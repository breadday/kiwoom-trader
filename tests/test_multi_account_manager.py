import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from api.multi_broker_api import MultiAccountManager


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


if __name__ == "__main__":
    unittest.main()
