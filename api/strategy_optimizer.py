
"""
전략 최적화 엔진 - 평가 기준을 못 잡겠을 때 자동으로 최적 파라미터 찾기
"""
import itertools
import math
import statistics
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass

@dataclass
class BacktestResult:
    strategy_id: str
    params: dict
    total_return: float
    win_rate: float
    max_drawdown: float
    sharpe: float
    avg_hold_days: float
    total_trades: int
    score: float  # 종합 점수

class StrategyOptimizer:
    """
    네 보유종목 -945만원 손실을 줄이기 위한 최적화
    평가 기준 4가지를 종합 점수로 계산
    """

    def __init__(self, daily_chart_provider: Optional[Callable] = None):
        self.daily_chart_provider = daily_chart_provider

    def _load_daily_bars(self, code: str, days: int, bars=None) -> List[dict]:
        if isinstance(days, bool) or not isinstance(days, int) or days <= 1:
            raise ValueError("days must be an integer greater than 1")
        if bars is None:
            if self.daily_chart_provider is None:
                raise RuntimeError("daily chart provider is required for backtests")
            bars = self.daily_chart_provider(code, limit=days)
        if not isinstance(bars, list) or len(bars) != days:
            actual = len(bars) if isinstance(bars, list) else "non-list"
            raise ValueError(f"expected exactly {days} daily bars, received {actual}")

        normalized = []
        previous_date = None
        for row in bars:
            if not isinstance(row, dict):
                raise ValueError("daily bars must contain mapping rows")
            try:
                bar_date = row["date"]
                if not isinstance(bar_date, str) or len(bar_date) != 8 or not bar_date.isdigit():
                    raise ValueError("invalid date")
                if previous_date is not None and bar_date <= previous_date:
                    raise ValueError("daily bars must be unique and ascending by date")
                prices = {name: float(row[name]) for name in ("open", "high", "low", "close")}
                volume = int(row["volume"])
                if any(not math.isfinite(value) or value <= 0 for value in prices.values()):
                    raise ValueError("OHLC prices must be finite and positive")
                if volume < 0 or prices["low"] > min(prices["open"], prices["close"]) or prices["high"] < max(prices["open"], prices["close"]):
                    raise ValueError("daily OHLCV row is inconsistent")
            except (KeyError, TypeError, ValueError, OverflowError) as exc:
                raise ValueError(f"invalid daily chart row: {row!r}") from exc
            normalized.append({**prices, "date": bar_date, "volume": volume})
            previous_date = bar_date
        return normalized

    def simulate_trades(self, code: str, strategy_id: str, params: dict, days=60, daily_bars=None) -> BacktestResult:
        """Backtest one RESCUE position using injected daily bars only.

        Enter at the first close, check sell thresholds at subsequent daily
        closes, sell half once at the partial threshold, and value any remainder
        at the final close. Fees and slippage are not modeled.
        """
        if strategy_id != "RESCUE":
            raise NotImplementedError("daily OHLCV backtest currently supports RESCUE only")
        bars = self._load_daily_bars(code, days, daily_bars)
        immediate_th = float(params.get("immediate_th", -40))
        partial_th = float(params.get("partial_th", -20))
        if not math.isfinite(immediate_th) or not math.isfinite(partial_th):
            raise ValueError("RESCUE thresholds must be finite numbers")
        if immediate_th >= 0 or partial_th >= 0 or partial_th <= immediate_th:
            raise ValueError("thresholds must satisfy immediate_th < partial_th < 0")

        entry_price = bars[0]["close"]
        initial_quantity = 1.0 / entry_price
        remaining_quantity = initial_quantity
        cash = 0.0
        partial_sold = False
        partial_day = None
        exit_day = days - 1
        equity_curve = [1.0]

        for day_index, bar in enumerate(bars[1:], start=1):
            close = bar["close"]
            pnl_pct = (close / entry_price - 1.0) * 100.0
            immediate_price = entry_price * (1.0 + immediate_th / 100.0)
            partial_price = entry_price * (1.0 + partial_th / 100.0)
            if close <= immediate_price:
                cash += remaining_quantity * close
                remaining_quantity = 0.0
                exit_day = day_index
            elif not partial_sold and close <= partial_price:
                quantity_to_sell = initial_quantity * 0.5
                cash += quantity_to_sell * close
                remaining_quantity -= quantity_to_sell
                partial_sold = True
                partial_day = day_index

            equity_curve.append(cash + remaining_quantity * close)
            if remaining_quantity == 0.0:
                equity_curve.extend([cash] * (days - len(equity_curve)))
                break

        if remaining_quantity > 0.0:
            cash += remaining_quantity * bars[-1]["close"]
        final_equity = cash
        daily_returns = [current / previous - 1.0 for previous, current in zip(equity_curve, equity_curve[1:]) if previous > 0]
        sharpe = 0.0
        if len(daily_returns) > 1:
            deviation = statistics.stdev(daily_returns)
            if deviation > 0:
                sharpe = statistics.mean(daily_returns) / deviation * math.sqrt(252)

        peak = 1.0
        max_drawdown = 0.0
        for equity in equity_curve:
            peak = max(peak, equity)
            if peak > 0:
                max_drawdown = max(max_drawdown, (peak - equity) / peak * 100.0)

        total_return = (final_equity - 1.0) * 100.0
        win_rate = 1.0 if total_return > 0 else 0.0
        avg_hold_days = (partial_day * 0.5 + exit_day * 0.5) if partial_sold else float(exit_day)
        score = (total_return + 50.0) * 0.8 + (30.0 - max_drawdown) + win_rate * 30.0 + max(0.0, sharpe) * 10.0
        return BacktestResult(
            strategy_id=strategy_id,
            params=dict(params),
            total_return=total_return,
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            sharpe=sharpe,
            avg_hold_days=avg_hold_days,
            total_trades=1,
            score=score,
        )

    def optimize_rescue(self, code: str) -> List[BacktestResult]:
        """RESCUE 전략 최적화 - 네 -945만원 회복용"""
        results = []
        bars = self._load_daily_bars(code, 60)
        # Reuse one verified snapshot for every parameter set; do not issue one
        # market-data request per grid point.
        for immediate_th in [-25, -30, -35, -40, -45, -50]:
            for partial_th in [-10, -15, -20, -25]:
                if partial_th <= immediate_th:  # 분할매도(-20)가 즉시정리(-40)보다 높아야 함 ( -20 > -40 )
                    continue
                params = {"immediate_th": immediate_th, "partial_th": partial_th}
                res = self.simulate_trades(code, "RESCUE", params, days=60, daily_bars=bars)
                results.append(res)
        return sorted(results, key=lambda x: x.score, reverse=True)

    def optimize_factor(self, code: str) -> List[BacktestResult]:
        raise NotImplementedError("FACTOR backtest requires a defined daily factor-score contract")

    def optimize_all_strategies(self, code: str) -> Dict[str, List[BacktestResult]]:
        raise NotImplementedError("all-strategy optimization is unavailable until FACTOR rules are data-driven")

    def recommend_for_portfolio(self, codes: List[str]) -> Dict[str, dict]:
        raise NotImplementedError("data-driven portfolio recommendations require explicit per-strategy rules")

if __name__ == "__main__":
    print("Configure StrategyOptimizer(daily_chart_provider=kiwoom_api.get_daily_chart) before running a backtest.")
