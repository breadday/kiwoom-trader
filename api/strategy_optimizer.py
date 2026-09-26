
"""
전략 최적화 엔진 - 평가 기준을 못 잡겠을 때 자동으로 최적 파라미터 찾기
"""
import itertools
import math
import statistics
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

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

    FACTOR_UNIVERSE = (
        "005935", "061220", "067310", "086520",
        "253590", "272210", "441680", "416770",
    )
    FACTOR_LOOKBACK_BARS = 252

    def __init__(self, daily_chart_provider: Optional[Callable] = None):
        self.daily_chart_provider = daily_chart_provider

    @staticmethod
    def _factor_percentiles(raw_scores: Dict[str, float], excluded_codes=()) -> Dict[str, float]:
        if not raw_scores:
            return {}
        values = list(raw_scores.values())
        if any(not math.isfinite(value) for value in values):
            raise ValueError("factor scores must be finite")
        ordered = sorted(values)
        result = {}
        count = len(ordered)
        for code, value in raw_scores.items():
            first = next(index for index, candidate in enumerate(ordered) if candidate == value)
            last = count - 1 - next(index for index, candidate in enumerate(reversed(ordered)) if candidate == value)
            average_rank = (first + last) / 2.0
            percentile = 50.0 if count == 1 else average_rank / (count - 1) * 100.0
            result[code] = 0.0 if code in excluded_codes else percentile
        return result

    @staticmethod
    def _factor_measurements(bars: List[dict], end_index: int) -> Dict[str, float]:
        history = bars[:end_index + 1]
        if len(history) <= 252:
            raise ValueError("FACTOR scoring requires more than 252 daily bars")
        closes = [bar["close"] for bar in history]
        volumes = [bar["volume"] for bar in history]
        # Preserve FactorSwingStrategy's 252-row (inclusive of current bar) convention.
        momentum = closes[-21] / closes[-252] - 1.0
        returns = [closes[index] / closes[index - 1] - 1.0 for index in range(len(closes) - 60, len(closes))]
        if any(not math.isfinite(value) for value in returns):
            raise ValueError("factor measurements must be finite")
        try:
            volatility = statistics.stdev(returns)
        except (OverflowError, ValueError) as exc:
            raise ValueError("factor measurements must be finite") from exc
        if not math.isfinite(volatility):
            raise ValueError("factor measurements must be finite")
        lowvol = 1.0 / volatility if volatility > 0 else 0.0
        quality = statistics.mean(volumes[-60:])
        value_proxy = -(closes[-1] / closes[-60] - 1.0)
        result = {"mom": momentum, "lowvol": lowvol, "quality": quality, "value": value_proxy}
        if any(not math.isfinite(value) for value in result.values()):
            raise ValueError("factor measurements must be finite")
        return result

    @staticmethod
    def _exclude_low_quality(qualities: Dict[str, float]) -> set:
        if any(not math.isfinite(value) for value in qualities.values()):
            raise ValueError("factor quality values must be finite")
        excluded_count = math.floor(len(qualities) * 0.3)
        return {
            code for code, _ in sorted(qualities.items(), key=lambda item: (item[1], item[0]))[:excluded_count]
        }

    @staticmethod
    def _daily_factor_percentiles(histories: Dict[str, List[dict]], end_index: int) -> Dict[str, float]:
        factors = {
            code: StrategyOptimizer._factor_measurements(bars, end_index)
            for code, bars in histories.items()
        }

        zscores = {code: {} for code in factors}
        for name in ("mom", "lowvol", "quality", "value"):
            column = [item[name] for item in factors.values()]
            mean = statistics.mean(column)
            deviation = statistics.stdev(column) if len(column) > 1 else float("nan")
            for code, item in factors.items():
                zscores[code][name] = (item[name] - mean) / (deviation + 1e-9) if math.isfinite(deviation) else float("nan")

        excluded = StrategyOptimizer._exclude_low_quality(
            {code: item["quality"] for code, item in factors.items()}
        )
        raw_scores = {}
        for code, item in factors.items():
            z = zscores[code]
            raw_scores[code] = z["mom"] * 0.4 + z["lowvol"] * 0.3 + z["quality"] * 0.2 + z["value"] * 0.1
        return StrategyOptimizer._factor_percentiles(raw_scores, excluded)

    def _simulate_factor_trade(self, code: str, bars: List[dict], factor_scores: List[float], days=60) -> BacktestResult:
        if isinstance(days, bool) or not isinstance(days, int) or days <= 1:
            raise ValueError("days must be an integer greater than 1")
        if len(bars) != self.FACTOR_LOOKBACK_BARS + days or len(factor_scores) != days:
            raise ValueError("FACTOR bars/scores do not match lookback and evaluation period")
        bars = self._load_daily_bars(code, self.FACTOR_LOOKBACK_BARS + days, bars)
        if any(not math.isfinite(score) or score < 0 or score > 100 for score in factor_scores):
            raise ValueError("factor percentile scores must be finite values from 0 to 100")
        entry_index = self.FACTOR_LOOKBACK_BARS
        entry_price = bars[entry_index]["close"]
        initial_quantity = 1.0 / entry_price
        remaining_quantity = initial_quantity
        cash = 0.0
        partial_sold = False
        partial_day = None
        exit_day = days - 1
        pending_action = None
        equity_curve = [1.0]
        # Score index 0 belongs to the virtual entry close; signal-day closes
        # are known only after that close, so orders fill at the next session open.
        for offset in range(1, days):
            bar_index = entry_index + offset
            bar = bars[bar_index]
            if pending_action == "full":
                cash += remaining_quantity * bar["open"]
                remaining_quantity = 0.0
                exit_day = offset
            elif pending_action == "partial":
                quantity_to_sell = initial_quantity * 0.5
                cash += quantity_to_sell * bar["open"]
                remaining_quantity -= quantity_to_sell
                partial_day = offset
            pending_action = None

            close = bar["close"]
            current_date = datetime.strptime(bar["date"], "%Y%m%d")
            if remaining_quantity > 0.0 and offset < days - 1 and current_date.weekday() == 0:
                score = factor_scores[offset]
                if score < 40.0:
                    pending_action = "full"
                elif not partial_sold and score < 50.0 and close > bars[bar_index - 1]["close"]:
                    pending_action = "partial"
                    partial_sold = True
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
            strategy_id="FACTOR",
            params={"immediate_score": 40.0, "partial_score": 50.0, "partial_fraction": 0.5, "check_weekday": "Monday"},
            total_return=total_return,
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            sharpe=sharpe,
            avg_hold_days=avg_hold_days,
            total_trades=1,
            score=score,
        )

    def simulate_factor_universe(self, days=60, daily_bars_by_code=None) -> Dict[str, BacktestResult]:
        if isinstance(days, bool) or not isinstance(days, int) or days <= 1:
            raise ValueError("days must be an integer greater than 1")
        required_bars = self.FACTOR_LOOKBACK_BARS + days
        if daily_bars_by_code is None:
            if self.daily_chart_provider is None:
                raise RuntimeError("daily chart provider is required for FACTOR backtests")
            daily_bars_by_code = {
                code: self.daily_chart_provider(code, limit=required_bars)
                for code in self.FACTOR_UNIVERSE
            }
        if not isinstance(daily_bars_by_code, dict) or set(daily_bars_by_code) != set(self.FACTOR_UNIVERSE):
            raise ValueError("daily bars must contain exactly the approved FACTOR universe")
        histories = {
            code: self._load_daily_bars(code, required_bars, daily_bars_by_code[code])
            for code in self.FACTOR_UNIVERSE
        }
        reference_dates = [bar["date"] for bar in histories[self.FACTOR_UNIVERSE[0]]]
        if any([bar["date"] for bar in history] != reference_dates for history in histories.values()):
            raise ValueError("FACTOR universe daily bars must have the same dates")
        score_series = {code: [] for code in self.FACTOR_UNIVERSE}
        for end_index in range(self.FACTOR_LOOKBACK_BARS, required_bars):
            daily_scores = self._daily_factor_percentiles(histories, end_index)
            for code in self.FACTOR_UNIVERSE:
                score_series[code].append(daily_scores[code])
        return {
            code: self._simulate_factor_trade(code, histories[code], score_series[code], days=days)
            for code in self.FACTOR_UNIVERSE
        }

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
                datetime.strptime(bar_date, "%Y%m%d")
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
        if code not in self.FACTOR_UNIVERSE:
            raise ValueError("code must belong to the approved FACTOR universe")
        return [self.simulate_factor_universe()[code]]

    def optimize_all_strategies(self, code: str) -> Dict[str, List[BacktestResult]]:
        raise NotImplementedError("daily optimization is unavailable for ORB/BULL_FLAG until their data-driven rules are defined")

    def recommend_for_portfolio(self, codes: List[str]) -> Dict[str, dict]:
        raise NotImplementedError("data-driven portfolio recommendations require explicit per-strategy rules")

if __name__ == "__main__":
    print("Configure StrategyOptimizer(daily_chart_provider=kiwoom_api.get_daily_chart) before running a backtest.")
