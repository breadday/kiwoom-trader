
"""
종목별 전략 엔진 - 종목마다 다른 전략을 선택하면 그 전략대로 매매
"""
from collections.abc import Mapping
from typing import Dict
from .multi_broker_api import MultiAccountManager


class MarketDataRequiredError(RuntimeError):
    """Raised when strategy evaluation has no explicit market-data provider."""


class StrategyNotConfiguredError(RuntimeError):
    """Raised when a held stock has no explicitly selected strategy."""

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

    @staticmethod
    def _require_market_data_provider(market_data_provider):
        if market_data_provider is None:
            raise MarketDataRequiredError(
                "an explicit market data provider is required"
            )
        if not callable(market_data_provider):
            raise TypeError("market_data_provider must be callable")
        return market_data_provider

    def _configured_strategy(self, code):
        strategy_id = self.stock_strategies.get(code)
        if strategy_id is None:
            raise StrategyNotConfiguredError(
                f"no strategy is configured for {code}"
            )
        return strategy_id, STRATEGIES[strategy_id]

    @staticmethod
    def _market_data_for(code, market_data_provider):
        market_data = market_data_provider(code)
        if not isinstance(market_data, Mapping):
            raise ValueError("market data provider must return a mapping")
        return dict(market_data)

    def _evaluate_position(self, pos, market_data_provider):
        code = pos['code']
        strategy_id, strategy = self._configured_strategy(code)
        market_data = self._market_data_for(code, market_data_provider)
        should_sell, reason = strategy.should_sell(pos, market_data)
        if not isinstance(should_sell, bool):
            raise ValueError("strategy sell decision must be boolean")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("strategy reason must be a non-empty string")
        return {
            "code": code,
            "account_id": pos['account_id'],
            "account_name": pos['account_name'],
            "broker": pos['broker'],
            "strategy": strategy_id,
            "should_sell": should_sell,
            "reason": reason,
            "qty": pos['qty'],
            "cur": pos['cur'],
        }

    def _execute_action(self, action):
        if action.get("error") is not None:
            return action
        if action['should_sell']:
            action['executed'] = self.manager.sell_stock(
                action['account_id'],
                action['code'],
                action['qty'],
            )
            print(
                f"[매매실행] {action['account_name']} {action['code']} "
                f"{action['strategy']} -> 매도 {action['reason']}"
            )
        else:
            print(
                f"[홀딩] {action['account_name']} {action['code']} "
                f"{action['strategy']} -> {action['reason']}"
            )
        return action

    def run(self, market_data_provider=None):
        """
        모든 포지션에 대해 설정된 전략 실행
        market_data_provider: code -> market_data dict 반환 함수
        """
        market_data_provider = self._require_market_data_provider(
            market_data_provider
        )
        balances = self.manager.get_all_balances()
        actions = [
            self._evaluate_position(pos, market_data_provider)
            for pos in balances['all_positions']
        ]
        return [self._execute_action(action) for action in actions]

    def run_single(self, code: str, market_data_provider=None):
        """Evaluate and, when signalled, paper-execute one held stock."""
        market_data_provider = self._require_market_data_provider(
            market_data_provider
        )
        balances = self.manager.get_all_balances()
        for pos in balances['all_positions']:
            if pos['code'] != code:
                continue
            action = self._evaluate_position(pos, market_data_provider)
            return self._execute_action(action)

        return {"error": f"{code} 보유종목 없음"}

    def run_selected(self, codes: list[str], market_data_provider=None):
        """Evaluate the requested stock codes in the given order."""
        market_data_provider = self._require_market_data_provider(
            market_data_provider
        )
        if not isinstance(codes, list) or any(
            not isinstance(code, str) or len(code) != 6 or not code.isdigit()
            for code in codes
        ):
            raise ValueError("codes must be a list of six-digit strings")
        if len(set(codes)) != len(codes):
            raise ValueError("selected codes must be unique")

        positions = self.manager.get_all_balances()['all_positions']
        first_position_by_code = {}
        for pos in positions:
            first_position_by_code.setdefault(pos['code'], pos)

        actions = []
        for code in codes:
            pos = first_position_by_code.get(code)
            if pos is None:
                actions.append({"error": f"{code} 보유종목 없음"})
            else:
                actions.append(
                    self._evaluate_position(pos, market_data_provider)
                )
        return [self._execute_action(action) for action in actions]

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
