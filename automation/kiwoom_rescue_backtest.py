"""Run RESCUE threshold optimization with Kiwoom demo daily bars."""

from argparse import ArgumentParser
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.kiwoom_api import KiwoomAPI
from api.strategy_optimizer import StrategyOptimizer
from automation.kiwoom_readonly_smoke import load_credentials


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--credentials-file", required=True, type=Path)
    parser.add_argument("--codes", required=True, help="comma-separated six-digit codes")
    parser.add_argument("--base-date", required=True, help="YYYYMMDD")
    args = parser.parse_args()
    codes = tuple(code.strip() for code in args.codes.split(",") if code.strip())
    if not codes or any(len(code) != 6 or not code.isdigit() for code in codes):
        raise ValueError("codes must be comma-separated six-digit strings")

    load_credentials(args.credentials_file)
    api = KiwoomAPI(paper=True, base_url="https://mockapi.kiwoom.com")
    for index, code in enumerate(codes):
        bars = api.get_daily_chart(code, base_dt=args.base_date, limit=60)
        if len(bars) != 60:
            raise RuntimeError(f"RESCUE_BACKTEST_BLOCKED missing 60 bars for {code}; received {len(bars)}")
        provider = lambda _code, *, limit, snapshot=bars: snapshot
        ranked = StrategyOptimizer(daily_chart_provider=provider).optimize_rescue(code)
        best = ranked[0]
        print(
            code,
            f"best_immediate={best.params['immediate_th']}",
            f"best_partial={best.params['partial_th']}",
            f"return={best.total_return:.4f}%",
            f"mdd={best.max_drawdown:.4f}%",
            f"score={best.score:.4f}",
        )
        if index + 1 < len(codes):
            time.sleep(1.5)
    print("RESCUE_BACKTEST_OK", f"codes={len(codes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
