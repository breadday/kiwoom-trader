"""Run the repository's safe, offline continuation checks.

This runner deliberately does not access broker/Telegram/Vercel services, read
credentials, commit, push, or mutate external state. It executes reproducible
local checks and records their outcome beside the unresolved-work ledger.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _quote_python(python: str) -> str:
    return f'"{python}"' if " " in python else python


def build_command_specs(python: str) -> list[tuple[str, str]]:
    """Return the bounded local commands used by the continuation runner."""

    py = _quote_python(python)
    return [
        ("tests", f"{py} -m pytest -q"),
        ("compile", f"{py} -m compileall -q api strategies tests automation"),
        ("offline demo", f"{py} automation/kiwoom_rescue_demo.py"),
        ("whitespace", "git diff --check"),
    ]


def render_report(results: list[dict], unresolved_path: Path) -> str:
    lines = [
        "# 자동화된 안전 연속 진행 결과",
        "",
        "> 이 보고서는 외부 서비스에 접근하지 않는 로컬 검증 결과다.",
        "> credential을 읽지 않고, commit/push하지 않으며(push하지 않음), 실주문을 시도하지 않는다.",
        "",
        "## 실행 결과",
        "",
        "| 단계 | 결과 | 명령 |",
        "|---|---|---|",
    ]
    for result in results:
        status = "PASS" if result["ok"] else "FAIL"
        lines.append(f"| {result['name']} | **{status}** | `{result['command']}` |")

    unresolved_display = "docs/UNRESOLVED.md" if unresolved_path.is_absolute() else unresolved_path.as_posix()
    lines.extend(
        [
            "",
            "## 남은 처리 항목",
            "",
            f"- 외부 승인·인증·원격 ref 작업은 자동화 범위 밖이며 실행하지 않았다. 상세 내용: `{unresolved_display}`",
            "- Gate 0 rewritten-ref publication, 운영 endpoint/account 검증, 승인되지 않은 실데이터 백테스트는 외부 승인 전까지 보류한다.",
            "- 실패 단계가 있으면 해당 오류를 먼저 수정하고 이 runner를 다시 실행한다.",
            "- 성공 단계만으로 외부 배포·Telegram 수신·원격 push가 완료되었다고 판단하지 않는다.",
            "",
            "## 출력 요약",
            "",
        ]
    )
    for result in results:
        output = result.get("output", "").strip().replace("\r\n", "\n")
        if len(output) > 1200:
            output = output[:1200] + "\n... (truncated)"
        lines.extend([f"### {result['name']}", "", "```text", output or "(no output)", "```", ""])
    return "\n".join(lines)


def run(root: Path, report_path: Path, python: str) -> int:
    results: list[dict] = []
    for name, command in build_command_specs(python):
        completed = subprocess.run(
            command,
            cwd=root,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        display_command = command.replace(str(Path(python)), "<project-python>")
        results.append(
            {
                "name": name,
                "command": display_command,
                "ok": completed.returncode == 0,
                "output": output,
            }
        )
        if completed.returncode != 0:
            break

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_report(results, root / "docs" / "UNRESOLVED.md"), encoding="utf-8"
    )
    return 0 if results and all(result["ok"] for result in results) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("docs/AUTOMATED-CONTINUATION-RESULTS.md"),
    )
    args = parser.parse_args()
    root = args.repo_root.resolve()
    report = args.report if args.report.is_absolute() else root / args.report
    return run(root, report, sys.executable)


if __name__ == "__main__":
    raise SystemExit(main())
