"""Run the approved FACTOR universe backtest with Kiwoom demo daily bars."""

from argparse import ArgumentParser
from pathlib import Path
import sys
import time

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.kiwoom_api import KiwoomAPI
from api.strategy_optimizer import StrategyOptimizer
from automation.kiwoom_readonly_smoke import load_credentials


UNIVERSE = StrategyOptimizer.FACTOR_UNIVERSE


def fetch_daily_bars(api, code, base_date, required_bars, *, max_attempts=4):
    """Fetch one symbol, retrying only HTTP 429 with bounded backoff."""
    for attempt in range(max_attempts):
        try:
            return api.get_daily_chart(
                code,
                base_dt=base_date,
                limit=required_bars,
            )
        except requests.HTTPError as exc:
            if getattr(exc.response, "status_code", None) != 429 or attempt + 1 >= max_attempts:
                raise
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable retry state")


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--credentials-file", required=True, type=Path)
    parser.add_argument("--base-date", required=True, help="YYYYMMDD")
    parser.add_argument("--days", type=int, default=60)
    args = parser.parse_args()
    if args.days <= 1:
        raise ValueError("days must be greater than 1")

    load_credentials(args.credentials_file)
    api = KiwoomAPI(paper=True, base_url="https://mockapi.kiwoom.com")
    required_bars = StrategyOptimizer.FACTOR_LOOKBACK_BARS + args.days
    daily_bars = {}
    for index, code in enumerate(UNIVERSE):
        daily_bars[code] = fetch_daily_bars(
            api, code, args.base_date, required_bars
        )
        if len(daily_bars[code]) != required_bars:
            raise RuntimeError(
                f"FACTOR_BACKTEST_BLOCKED missing {required_bars} bars for {code}; "
                f"received {len(daily_bars[code])}"
            )
        if index + 1 < len(UNIVERSE):
            time.sleep(1.5)
    results = StrategyOptimizer().simulate_factor_universe(
        days=args.days,
        daily_bars_by_code=daily_bars,
    )
    print("FACTOR_BACKTEST_OK", f"universe={len(results)}", f"bars_per_code={required_bars}")
    for code in UNIVERSE:
        result = results[code]
        print(
            code,
            f"return={result.total_return:.4f}%",
            f"mdd={result.max_drawdown:.4f}%",
            f"sharpe={result.sharpe:.4f}",
            f"score={result.score:.4f}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
