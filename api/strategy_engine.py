
"""
종목별 전략 엔진 - 종목마다 다른 전략을 선택하면 그 전략대로 매매
"""
from typing import Dict
from .multi_broker_api import MultiAccountManager

class Strategy:
    def should_sell(self, pos: dict, market_data: dict) -> tuple[bool, str]:
        """return (sell?, reason)"""
        pass

class ORBStrategy(Strategy):
    """Opening Range Breakout - 단타: 9:00-9:30 고점 돌파 실패시 손절"""
    def should_sell(self, pos, market_data):
        # 예: 9:30 이전에 -2% 이상이면 손절
        if market_data.get('change_pct', 0) < -2.0:
            return True, "ORB 손절 -2%"
        return False, "ORB 홀딩"

class BullFlagStrategy(Strategy):
    """불플래그 - 3-5일 추세 유지, 이탈시 매도"""
    def should_sell(self, pos, market_data):
        # 거래대금 급감시 매도
        if market_data.get('volume_drop', False):
            return True, "불플래그 거래대금 이탈"
        return False, "불플래그 추세 유지"

class FactorStrategy(Strategy):
    """팩터 스윙 - 팩터 점수 50점 이하이면 반등시 매도"""
    def should_sell(self, pos, market_data):
        factor = market_data.get('factor_total', 50)
        if factor < 40:
            return True, f"팩터 점수 {factor} - 즉시정리"
        if factor < 50 and market_data.get('is_bounce', False):
            return True, f"팩터 {factor} 반등시 분할매도"
        return False, f"팩터 {factor} HOLD"

class RescueStrategy(Strategy):
    """구조조정 - 계좌 구조조정 전용"""
    def should_sell(self, pos, market_data):
        pl_pct = pos.get('pl_pct', 0)
        if pl_pct < -40:
            return True, f"구조조정 즉시정리 {pl_pct:.1f}%"
        if pl_pct < -20:
            return True, f"구조조정 분할매도 {pl_pct:.1f}%"
        return False, "구조조정 HOLD"

# 전략 팩토리
STRATEGIES = {
    "ORB": ORBStrategy(),
    "BULL_FLAG": BullFlagStrategy(),
    "FACTOR": FactorStrategy(),
    "RESCUE": RescueStrategy(),
}

class PerStockStrategyEngine:
    """
    종목별로 전략 선택 -> 그 전략대로 매매 실행
    예: {"005935": "FACTOR", "441680": "RESCUE", "067310": "BULL_FLAG"}
    """
    def __init__(self, manager: MultiAccountManager):
        self.manager = manager
        self.stock_strategies: Dict[str, str] = {}  # code -> strategy_id

    def set_strategy(self, code: str, strategy_id: str):
        """종목별 전략 설정"""
        if strategy_id not in STRATEGIES:
            raise ValueError(f"전략 {strategy_id} 없음. 가능한: {list(STRATEGIES.keys())}")
        self.stock_strategies[code] = strategy_id
        print(f"[전략설정] {code} -> {strategy_id}")

    def set_strategies_bulk(self, mapping: Dict[str, str]):
        for code, strat in mapping.items():
            self.set_strategy(code, strat)

    def run(self, market_data_provider=None):
        """
        모든 포지션에 대해 설정된 전략 실행
        market_data_provider: code -> market_data dict 반환 함수
        """
        balances = self.manager.get_all_balances()
        actions = []

        for pos in balances['all_positions']:
            code = pos['code']
            strategy_id = self.stock_strategies.get(code, "FACTOR")  # 기본 Factor
            strategy = STRATEGIES[strategy_id]

            # 시장 데이터 (실전은 키움 시세 API)
            market_data = {}
            if market_data_provider:
                market_data = market_data_provider(code)
            else:
                # mock 데이터 - 팩터 점수 등
                market_data = {
                    "factor_total": 30 if pos['pl_pct'] < -30 else 60,
                    "is_bounce": pos['pl_pct'] > -5,
                    "change_pct": pos['pl_pct']
                }

            should_sell, reason = strategy.should_sell(pos, market_data)

            action = {
                "code": code,
                "account_id": pos['account_id'],
                "account_name": pos['account_name'],
                "broker": pos['broker'],
                "strategy": strategy_id,
                "should_sell": should_sell,
                "reason": reason,
                "qty": pos['qty'],
                "cur": pos['cur']
            }
            actions.append(action)

            if should_sell:
                # 실제 매도 실행 (paper 모드면 모의)
                result = self.manager.sell_stock(pos['account_id'], code, pos['qty'])
                action['executed'] = result
                print(f"[매매실행] {pos['account_name']} {code} {strategy_id} -> 매도 {reason}")
            else:
                print(f"[홀딩] {pos['account_name']} {code} {strategy_id} -> {reason}")

        return actions

if __name__ == "__main__":
    mgr = MultiAccountManager("/mnt/data/kiwoom_trader/accounts.yaml")
    engine = PerStockStrategyEngine(mgr)

    # 네 보유종목별 전략 설정 예시
    engine.set_strategies_bulk({
        "005935": "FACTOR",      # 삼성전자우 - 팩터 HOLD
        "061220": "RESCUE",      # LB세미콘 - 구조조정 분할매도
        "067310": "BULL_FLAG",   # 하나마이크론 - 불플래그 추세추종
        "086520": "RESCUE",      # 에코프로 - 구조조정 즉시정리
        "253590": "FACTOR",      # 네오셈 - 팩터 반등시 매도
        "272210": "RESCUE",      # 한화시스템 - 구조조정
        "441680": "RESCUE",      # 스피어 - 구조조정 즉시정리
        "416770": "RESCUE",      # 신성에스티 - 구조조정
    })

    actions = engine.run()
    for a in actions:
        print(f"{a['code']} {a['strategy']} {'SELL' if a['should_sell'] else 'HOLD'} {a['reason']}")
