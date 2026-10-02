import ast
import unittest
from api.demo_portfolio import split_quantity_evenly
from api.sample_portfolio import SAMPLE_POSITIONS
from tests.offline_demo_runner import run_demo_offline
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEMO_SCRIPT = ROOT / "automation" / "kiwoom_rescue_demo.py"


class DemoPortfolioPrivacyTests(unittest.TestCase):
    def test_rescue_demo_script_uses_only_explicit_sample_portfolio_data(self):
        source = DEMO_SCRIPT.read_text(encoding="utf-8")

        self.assertNotIn("REAL_POSITIONS", source)
        self.assertNotIn("실제 계좌 상태", source)
        self.assertIn("from api.sample_portfolio import SAMPLE_CASH, SAMPLE_POSITIONS", source)
        self.assertNotIn("from api.kiwoom_auth", source)
        self.assertNotIn("from api.kiwoom_api", source)
        self.assertNotIn("sell_market", source)
        self.assertNotIn("paper=False", source)

    def test_sample_portfolio_fixture_is_clearly_synthetic_and_well_formed(self):
        fixture_path = ROOT / "api" / "sample_portfolio.py"
        self.assertTrue(fixture_path.is_file(), "synthetic portfolio fixture must exist")
        tree = ast.parse(fixture_path.read_text(encoding="utf-8"))
        values = {
            target.id: ast.literal_eval(value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
            for value in [node.value]
        }

        cash = values["SAMPLE_CASH"]
        positions = values["SAMPLE_POSITIONS"]
        self.assertGreater(cash, 0)
        self.assertTrue(positions)
        for code, position in positions.items():
            self.assertTrue(code.startswith("DEMO-"))
            self.assertTrue(position["name"].startswith("가상 샘플"))
            self.assertGreater(position["qty"], 0)
            self.assertGreater(position["avg"], 0)
            self.assertGreater(position["current"], 0)

        total_pnl = sum(
            (position["current"] - position["avg"]) * position["qty"]
            for position in positions.values()
        )
        self.assertLess(total_pnl, 0, "demo rescue portfolio should be loss-making")


    def test_three_week_sale_plan_preserves_all_shares_with_balanced_remainders(self):
        self.assertEqual([4, 3, 3], split_quantity_evenly(10, 3))
        self.assertEqual([2, 2, 1], split_quantity_evenly(5, 3))
        self.assertEqual([0, 0, 0], split_quantity_evenly(0, 3))

    def test_exact_30_percent_loss_is_eligible_for_virtual_sale(self):
        from unittest.mock import patch

        position = dict(SAMPLE_POSITIONS["DEMO-003"], current=28_000)
        with patch.dict(SAMPLE_POSITIONS, {"DEMO-003": position}):
            _, output = run_demo_offline(DEMO_SCRIPT)

        sale_lines = [line for line in output.splitlines() if "가상 매도" in line]
        self.assertEqual(3, len(sale_lines))
        self.assertIn("(DEMO-003) 2주 가상 매도", sale_lines[0])
        self.assertIn("(DEMO-003) 2주 가상 매도", sale_lines[1])
        self.assertIn("(DEMO-003) 1주 가상 매도", sale_lines[2])

    def test_trusted_demo_passes_selected_python_network_guards_without_broker_imports(self):
        strategy_tree = ast.parse((ROOT / "strategies" / "factor_swing.py").read_text(encoding="utf-8"))
        strategy_imports = {
            alias.name.split(".")[0]
            for node in ast.walk(strategy_tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        strategy_imports.update(
            node.module.split(".")[0]
            for node in ast.walk(strategy_tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        self.assertLessEqual(strategy_imports, {"numpy", "pandas"})

        demo_globals, output = run_demo_offline(DEMO_SCRIPT)
        for code, position in SAMPLE_POSITIONS.items():
            close = demo_globals["history"][code]["close"]
            self.assertEqual(position["avg"], close.iloc[0])
            self.assertEqual(position["current"], close.iloc[-1])

        self.assertEqual(["DEMO-001", "DEMO-003"], demo_globals["picks"]["code"].tolist())
        self.assertEqual([0.6707, -0.4907], [round(float(score), 4) for score in demo_globals["picks"]["score"]])
        self.assertEqual(2, output.count("가상 샘플 C (DEMO-003) 2주 가상 매도"))
        self.assertEqual(1, output.count("가상 샘플 C (DEMO-003) 1주 가상 매도"))

    def test_runner_blocks_subprocess_run_via_python_entrypoint_patch(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            probe = Path(directory) / "child_process_probe.py"
            probe.write_text(
                "import subprocess, sys\n"
                "subprocess.run([sys.executable, '-c', 'pass'], check=True)\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(AssertionError, "selected Python process API"):
                run_demo_offline(probe)

    def test_direct_demo_entrypoint_runs_from_repository_root(self):
        import os
        import subprocess
        import sys

        env = os.environ.copy()
        completed = subprocess.run(
            [sys.executable, str(DEMO_SCRIPT)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("가상 샘플 현금:", completed.stdout)
        self.assertIn("가상 매도", completed.stdout)

    def test_offline_demo_output_is_deterministic_across_processes(self):
        import os
        import subprocess
        import sys

        env = os.environ.copy()
        env["PYTHONHASHSEED"] = "random"
        outputs = [
            subprocess.check_output(
                [sys.executable, "-m", "tests.offline_demo_runner", str(DEMO_SCRIPT)],
                cwd=ROOT,
                env=env,
                text=True,
            )
            for _ in range(2)
        ]
        self.assertEqual(outputs[0], outputs[1])


if __name__ == "__main__":
    unittest.main()
