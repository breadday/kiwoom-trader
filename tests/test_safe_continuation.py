import unittest
from pathlib import Path

from automation.continue_safe import build_command_specs, render_report


class SafeContinuationTests(unittest.TestCase):
    def test_command_specs_are_offline_and_do_not_publish(self):
        specs = build_command_specs("python")
        commands = [command for _, command in specs]

        self.assertTrue(any("pytest" in command for command in commands))
        self.assertTrue(any("compileall" in command for command in commands))
        self.assertTrue(any("kiwoom_rescue_demo.py" in command for command in commands))
        self.assertTrue(any("git diff --check" in command for command in commands))
        self.assertFalse(any("push" in command or "curl" in command for command in commands))

    def test_report_preserves_unresolved_external_gates(self):
        report = render_report(
            [
                {"name": "tests", "command": "python -m pytest -q", "ok": True, "output": "2 passed"},
                {"name": "compile", "command": "python -m compileall -q", "ok": False, "output": "syntax error"},
            ],
            Path("docs/UNRESOLVED.md"),
        )

        self.assertIn("tests", report)
        self.assertIn("FAIL", report)
        self.assertIn("docs/UNRESOLVED.md", report)
        self.assertIn("외부 승인", report)
        self.assertIn("push하지 않음", report)


if __name__ == "__main__":
    unittest.main()
