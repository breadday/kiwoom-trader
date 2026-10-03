"""Run ORB/BULL_FLAG backtests on Kiwoom read-only minute bars.

The script never places orders and never synthesizes missing market data.
Execution costs are required explicitly so results cannot hide assumptions.
"""
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.kiwoom_api import KiwoomAPI
from automation.kiwoom_readonly_smoke import load_credentials


@dataclass(frozen=True)
class CostModel:
    commission_rate: float
    sell_tax_rate: float
    slippage_rate: float

    def validate(self) -> None:
        if min(self.commission_rate, self.sell_tax_rate, self.slippage_rate) < 0:
            raise ValueError("cost rates must be non-negative")


def _day(value: str) -> str:
    return str(value)[:8]


def _price(value: float, rate: float, buying: bool) -> float:
    return value * (1 + rate) if buying else value * (1 - rate)


def _trade_return(entry: float, exit_price: float, costs: CostModel) -> float:
    buy = _price(entry, costs.slippage_rate, True) * (1 + costs.commission_rate)
    sell = _price(exit_price, costs.slippage_rate, False) * (1 - costs.commission_rate - costs.sell_tax_rate)
    return sell / buy - 1.0


def _signal(day_bars: list[dict], index: int, opening_high: float, volume_decay: float):
    bar = day_bars[index]
    orb = bar["close"] > opening_high * 1.003 and bar["volume"] > sum(x["volume"] for x in day_bars) / len(day_bars) * 1.2
    flag = False
    if index >= 15:
        pole_base = day_bars[index - 10]["close"]
        pole_gain = (day_bars[index - 1]["close"] - pole_base) / pole_base
        flag_bars = day_bars[index - 5:index]
        before = day_bars[index - 15:index - 10]
        flag_volume = sum(x["volume"] for x in flag_bars) / len(flag_bars)
        before_volume = sum(x["volume"] for x in before) / len(before)
        flag = (
            pole_gain >= 0.02
            and flag_volume <= before_volume * volume_decay
            and bar["close"] > max(x["high"] for x in flag_bars) * 1.001
        )
    return "ORB" if orb else "BULL_FLAG" if flag else None


def backtest_day(day_bars: list[dict], volume_decay: float, costs: CostModel) -> list[dict]:
    if len(day_bars) <= 15:
        return []
    opening_high = max(x["high"] for x in day_bars[:15])
    trades = []
    position = None
    for index in range(15, len(day_bars) - 1):
        bar = day_bars[index]
        if position is None:
            strategy = _signal(day_bars, index, opening_high, volume_decay)
            if strategy:
                position = {"strategy": strategy, "entry_index": index + 1, "entry": day_bars[index + 1]["open"]}
            continue
        entry = position["entry"]
        pnl = (bar["close"] - entry) / entry
        held = index - position["entry_index"]
        if pnl <= -0.03 if position["strategy"] == "ORB" else pnl <= -0.02:
            exit_price = day_bars[index + 1]["open"]
        elif pnl >= 0.08 if position["strategy"] == "ORB" else pnl >= 0.05 or held >= 30:
            exit_price = day_bars[index + 1]["open"]
        else:
            continue
        trades.append({"strategy": position["strategy"], "entry": entry, "exit": exit_price, "return": _trade_return(entry, exit_price, costs)})
        position = None
    if position is not None:
        exit_price = day_bars[-1]["close"]
        trades.append({"strategy": position["strategy"], "entry": position["entry"], "exit": exit_price, "return": _trade_return(position["entry"], exit_price, costs)})
    return trades


def run(bars: Iterable[dict], volume_decay: float, costs: CostModel) -> dict:
    costs.validate()
    grouped: dict[str, list[dict]] = {}
    for bar in bars:
        grouped.setdefault(_day(bar["datetime"]), []).append(bar)
    trades = [trade for day in grouped.values() for trade in backtest_day(day, volume_decay, costs)]
    returns = [trade["return"] for trade in trades]
    total = 1.0
    peak = 1.0
    mdd = 0.0
    for value in returns:
        total *= 1 + value
        peak = max(peak, total)
        mdd = max(mdd, (peak - total) / peak)
    return {"days": len(grouped), "trades": len(trades), "return": total - 1, "mdd": mdd, "trades_detail": trades}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--credentials-file", required=True, type=Path)
    parser.add_argument("--code", required=True)
    parser.add_argument("--tick", type=int, default=1)
    parser.add_argument("--volume-decay", type=float, action="append", required=True)
    parser.add_argument("--commission-rate", type=float, required=True)
    parser.add_argument("--sell-tax-rate", type=float, required=True)
    parser.add_argument("--slippage-rate", type=float, required=True)
    args = parser.parse_args()
    load_credentials(args.credentials_file)
    os.environ["KIWOOM_BASE_URL"] = "https://mockapi.kiwoom.com"
    api = KiwoomAPI(paper=True)
    bars = api.get_minute_chart(args.code, tick=args.tick)
    if not bars:
        raise RuntimeError("no minute bars returned; refusing synthetic fallback")
    costs = CostModel(args.commission_rate, args.sell_tax_rate, args.slippage_rate)
    for decay in args.volume_decay:
        result = run(bars, decay, costs)
        print("ORB_BULL_FLAG_BACKTEST_OK", f"code={args.code}", f"decay={decay}", f"days={result['days']}", f"trades={result['trades']}", f"return={result['return']:.6f}", f"mdd={result['mdd']:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
