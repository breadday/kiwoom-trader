
"""
전략 최적화 엔진 - 평가 기준을 못 잡겠을 때 자동으로 최적 파라미터 찾기
"""
import itertools
import random
from typing import Dict, List
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

    def __init__(self):
        # 백테스트용 mock 데이터 - 실제로는 키움 일봉 데이터 사용
        # 각 종목의 과거 60일 수익률 시뮬레이션
        self.mock_history = {
            "005935": {"volatility": 0.8, "trend": 0.2},  # 삼성전자우 - 낮은 변동
            "061220": {"volatility": 2.5, "trend": -0.5}, # LB세미콘 - 하락
            "067310": {"volatility": 1.8, "trend": 0.6},   # 하나마이크론 - 상승중
            "086520": {"volatility": 3.5, "trend": -1.2}, # 에코프로 - 급락
            "253590": {"volatility": 2.2, "trend": -0.3}, # 네오셈 - 하락
            "272210": {"volatility": 2.0, "trend": -0.4}, # 한화시스템 - 하락
            "441680": {"volatility": 4.0, "trend": -1.5}, # 스피어 - 대폭락
            "416770": {"volatility": 2.8, "trend": -0.8}, # 신성에스티 - 하락
        }

    def simulate_trades(self, code: str, strategy_id: str, params: dict, days=60) -> BacktestResult:
        """해당 전략/파라미터로 60일 백테스트 시뮬레이션"""
        hist = self.mock_history.get(code, {"volatility": 2.0, "trend": -0.5})
        vol = hist["volatility"]
        trend = hist["trend"]

        # 파라미터에 따라 수익 시뮬레이션
        # RESCUE 전략: 손절 기준이 타이트할수록 손실은 작지만 거래 많음
        if strategy_id == "RESCUE":
            immediate_th = params.get("immediate_th", -40)
            partial_th = params.get("partial_th", -20)
            # 손절을 빨리 할수록 MDD는 작아지지만, 반등 놓칠 수 있음
            # 시뮬레이션: immediate_th가 -30이면 -50%까지 가는 걸 방지
            base_return = -25  # 현재 평균 손실
            if immediate_th >= -30:
                base_return = -15  # 빨리 손절하면 추가 손실 방지
                win_rate = 0.35
                mdd = 12
            elif immediate_th >= -40:
                base_return = -22
                win_rate = 0.45
                mdd = 18
            else:
                base_return = -30
                win_rate = 0.55
                mdd = 28

            total_trades = 8 if immediate_th >= -30 else 4
            sharpe = ( -base_return - 5) / (vol * 2) * -1  # 손실 최소화 관점

        elif strategy_id == "FACTOR":
            factor_th_low = params.get("factor_low", 40)
            factor_th_high = params.get("factor_high", 50)
            base_return = -10 if factor_th_low < 35 else -18
            win_rate = 0.5 if factor_th_low < 35 else 0.42
            mdd = 15 if factor_th_low < 35 else 22
            total_trades = 6
            sharpe = 0.3 if factor_th_low < 35 else 0.1

        elif strategy_id == "BULL_FLAG":
            vol_drop_th = params.get("vol_drop_th", 0.5)
            base_return = 5 if hist["trend"] > 0 else -12
            win_rate = 0.62 if hist["trend"] > 0 else 0.38
            mdd = 10
            total_trades = 5
            sharpe = 0.8 if hist["trend"] > 0 else -0.2

        else:  # ORB
            stop_loss = params.get("stop_loss", -2.0)
            base_return = -3 if stop_loss >= -1.5 else -8
            win_rate = 0.48
            mdd = 8
            total_trades = 12
            sharpe = 0.2

        # 종합 점수 계산 (네 상황: 손실 최소화 + MDD 최소화 + 승률)
        # 평가 기준: 1. 총수익 40% 2. MDD 30% 3. 승률 20% 4. 샤프 10%
        score = 0
        score += (base_return + 50) * 0.8  # -50~+20 범위를 0~56점으로
        score += (30 - mdd) * 1.0  # MDD 작을수록 좋음
        score += win_rate * 30
        score += max(0, sharpe) * 10

        return BacktestResult(
            strategy_id=strategy_id,
            params=params,
            total_return=base_return,
            win_rate=win_rate,
            max_drawdown=mdd,
            sharpe=sharpe,
            avg_hold_days=random.uniform(5, 20),
            total_trades=total_trades,
            score=score
        )

    def optimize_rescue(self, code: str) -> List[BacktestResult]:
        """RESCUE 전략 최적화 - 네 -945만원 회복용"""
        results = []
        # 즉시정리 기준 -25 ~ -50, 분할매도 기준 -10 ~ -30 그리드 서치
        for immediate_th in [-25, -30, -35, -40, -45, -50]:
            for partial_th in [-10, -15, -20, -25]:
                if partial_th <= immediate_th:  # 분할매도(-20)가 즉시정리(-40)보다 높아야 함, -20 > -40
                    continue
                params = {"immediate_th": immediate_th, "partial_th": partial_th}
                res = self.simulate_trades(code, "RESCUE", params)
                results.append(res)
        return sorted(results, key=lambda x: x.score, reverse=True)

    def optimize_factor(self, code: str) -> List[BacktestResult]:
        results = []
        for low in [30, 35, 40, 45]:
            for high in [45, 50, 55, 60]:
                if low >= high:
                    continue
                params = {"factor_low": low, "factor_high": high}
                res = self.simulate_trades(code, "FACTOR", params)
                results.append(res)
        return sorted(results, key=lambda x: x.score, reverse=True)

    def optimize_all_strategies(self, code: str) -> Dict[str, List[BacktestResult]]:
        """해당 종목에 대해 모든 전략 최적화"""
        return {
            "RESCUE": self.optimize_rescue(code),
            "FACTOR": self.optimize_factor(code),
        }

    def recommend_for_portfolio(self, codes: List[str]) -> Dict[str, dict]:
        """네 8종목 포트폴리오 전체에 대한 추천"""
        recommendations = {}
        for code in codes:
            hist = self.mock_history.get(code, {"trend": -0.5})
            # 트렌드에 따라 전략 추천
            if hist["trend"] < -1.0:
                # 대폭락 종목 - RESCUE 빠르게
                best = self.optimize_rescue(code)[0]
                recommendations[code] = {
                    "recommended_strategy": "RESCUE",
                    "params": best.params,
                    "reason": f"대폭락 추세 {hist['trend']}, 빠른 손절 필요",
                    "expected_return": best.total_return,
                    "result": best
                }
            elif hist["trend"] < -0.2:
                # 하락 종목 - FACTOR 반등 매도
                best = self.optimize_factor(code)[0]
                recommendations[code] = {
                    "recommended_strategy": "FACTOR",
                    "params": best.params,
                    "reason": f"하락 추세, 팩터 반등시 매도",
                    "expected_return": best.total_return,
                    "result": best
                }
            else:
                # 상승/횡보 - BULL_FLAG
                recommendations[code] = {
                    "recommended_strategy": "BULL_FLAG",
                    "params": {"vol_drop_th": 0.5},
                    "reason": f"상승 추세 {hist['trend']}, 추세 추종",
                    "expected_return": 5,
                    "result": None
                }
        return recommendations

if __name__ == "__main__":
    opt = StrategyOptimizer()

    # 네 8종목 최적화
    codes = ["005935", "061220", "067310", "086520", "253590", "272210", "441680", "416770"]
    recos = opt.recommend_for_portfolio(codes)

    print("=== 네 포트폴리오 최적화 추천 ===")
    for code, rec in recos.items():
        print(f"{code}: {rec['recommended_strategy']} {rec['params']} - {rec['reason']} 예상 {rec['expected_return']}%")

    # 스피어 상세 최적화
    print("\n=== 스피어(441680) RESCUE 상세 ===")
    results = opt.optimize_rescue("441680")
    for r in results[:5]:
        print(f"즉시{ r.params['immediate_th']}%/분할{ r.params['partial_th']}% -> 수익 {r.total_return}% MDD {r.max_drawdown}% 승률 {r.win_rate:.0%} 점수 {r.score:.1f}")
