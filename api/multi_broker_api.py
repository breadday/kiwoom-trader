
"""
멀티 브로커 통합 매니저 - 키움, NH, 삼성, KB
모든 증권사가 동일한 인터페이스로 동작
"""
from abc import ABC, abstractmethod
from collections.abc import Mapping
import math
from typing import Dict, List
import yaml
from .kiwoom_api import KiwoomAPI
from .kiwoom_auth import KiwoomAuth
from order import LiveOrderDisabledError


class LiveBalanceDisabledError(RuntimeError):
    """Raised when an adapter has no approved live balance implementation."""

class BrokerAdapter(ABC):
    def __init__(self, config: dict):
        self.config = config
        self.id = config['id']
        self.name = config.get('name', self.id)
        self.broker = config['broker']
        self.paper = config.get('paper', True)

    @abstractmethod
    def get_balance(self) -> dict:
        """return {cash: int, positions: {code: {qty, avg, cur, pl}}}"""
        pass

    @abstractmethod
    def buy_market(self, code: str, qty: int) -> dict:
        pass

    @abstractmethod
    def sell_market(self, code: str, qty: int) -> dict:
        pass

    def _ensure_paper_order(self):
        if not self.paper:
            raise LiveOrderDisabledError(
                f"{self.broker} live order submission is disabled"
            )

    def _ensure_paper_balance(self):
        if not self.paper:
            raise LiveBalanceDisabledError(
                f"{self.broker} live balance retrieval is disabled"
            )

class KiwoomAdapter(BrokerAdapter):
    def __init__(self, config):
        super().__init__(config)
        # 키움 인증
        app_key = config.get('app_key', 'dummy')
        app_secret = config.get('app_secret', 'dummy')
        auth = KiwoomAuth(app_key, app_secret)
        self.api = KiwoomAPI(auth, paper=self.paper)
        # 네 기존 보유종목 mock 데이터 (실전 연결 전까지)
        if self.paper:
            self.api.paper_balance = {
                "cash": 200918,
                "positions": {
                    "005935": {"qty": 6, "avg": 229500, "cur": 208000},
                    "061220": {"qty": 400, "avg": 5630, "cur": 4330},
                }
            }

    def get_balance(self):
        self._ensure_paper_balance()
        return self.api.get_balance()

    def buy_market(self, code, qty):
        return self.api.buy_market(code, qty)

    def sell_market(self, code, qty):
        return self.api.sell_market(code, qty)

class NHAdapter(BrokerAdapter):
    """NH투자증권 Open API - https://apiportal.nhqv.com"""
    def __init__(self, config):
        super().__init__(config)
        self.app_key = config.get('app_key')
        self.app_secret = config.get('app_secret')
        self.account = config.get('account_no')
        # paper mock - NH 계좌 예시
        self.mock = {
            "cash": 1500000,
            "positions": {
                "067310": {"qty": 141, "avg": 41903, "cur": 44800},  # 하나마이크론
                "253590": {"qty": 113, "avg": 17710, "cur": 13020},  # 네오셈
            }
        }

    def get_balance(self):
        self._ensure_paper_balance()
        return self.mock

    def buy_market(self, code, qty):
        self._ensure_paper_order()
        print(f"[NH PAPER BUY] {code} {qty}주")
        return {"status": "filled", "broker": "nh"}

    def sell_market(self, code, qty):
        self._ensure_paper_order()
        print(f"[NH PAPER SELL] {code} {qty}주")
        return {"status": "filled", "broker": "nh"}

class SamsungAdapter(BrokerAdapter):
    """삼성증권 Open API - POP"""
    def __init__(self, config):
        super().__init__(config)
        self.mock = {
            "cash": 800000,
            "positions": {
                "086520": {"qty": 12, "avg": 161700, "cur": 79900},  # 에코프로
                "272210": {"qty": 20, "avg": 120600, "cur": 76500},  # 한화시스템
            }
        }

    def get_balance(self):
        self._ensure_paper_balance()
        return self.mock

    def buy_market(self, code, qty):
        self._ensure_paper_order()
        return {"status": "filled", "broker": "samsung"}

    def sell_market(self, code, qty):
        self._ensure_paper_order()
        return {"status": "filled", "broker": "samsung"}

class KBAdapter(BrokerAdapter):
    """KB증권 Open API"""
    def __init__(self, config):
        super().__init__(config)
        self.mock = {
            "cash": 500000,
            "positions": {
                "441680": {"qty": 217, "avg": 41814, "cur": 23300},  # 스피어
                "416770": {"qty": 185, "avg": 38990, "cur": 23850},  # 신성에스티
            }
        }

    def get_balance(self):
        self._ensure_paper_balance()
        return self.mock

    def buy_market(self, code, qty):
        self._ensure_paper_order()
        return {"status": "filled", "broker": "kb"}

    def sell_market(self, code, qty):
        self._ensure_paper_order()
        return {"status": "filled", "broker": "kb"}

class MultiAccountManager:
    def __init__(self, config_path="accounts.yaml"):
        self.adapters: Dict[str, BrokerAdapter] = {}
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError("accounts config file was not found") from None

        if not isinstance(cfg, Mapping):
            raise ValueError("accounts config must be a mapping")
        accounts = cfg.get('accounts')
        if not isinstance(accounts, list):
            raise ValueError("accounts must be a list")

        adapter_types = {
            'kiwoom': KiwoomAdapter,
            'nh': NHAdapter,
            'samsung': SamsungAdapter,
            'kb': KBAdapter,
        }
        validated = []
        seen_ids = set()
        for acc_cfg in accounts:
            if not isinstance(acc_cfg, Mapping):
                raise ValueError("each account must be a mapping")
            account_id = acc_cfg.get('id')
            broker = acc_cfg.get('broker')
            paper = acc_cfg.get('paper', True)
            if not isinstance(account_id, str) or not account_id.strip():
                raise ValueError("account id must be a non-empty string")
            if account_id in seen_ids:
                raise ValueError("duplicate account id")
            if broker not in adapter_types:
                raise ValueError("unsupported broker")
            if not isinstance(paper, bool):
                raise ValueError("account paper flag must be boolean")
            seen_ids.add(account_id)
            validated.append((account_id, adapter_types[broker], dict(acc_cfg)))

        for account_id, adapter_type, acc_cfg in validated:
            self.adapters[account_id] = adapter_type(acc_cfg)

    def get_all_balances(self):
        result = []
        total_cash = 0
        total_eval = 0
        total_buy = 0
        all_pos = []

        for acc_id, adapter in self.adapters.items():
            bal = self._validate_balance(adapter.get_balance())
            cash = bal['cash']
            positions = bal['positions']

            acc_eval = 0
            acc_buy = 0
            for code, pos in positions.items():
                qty = pos.get('qty', 0)
                avg = pos.get('avg', 0)
                cur = pos.get('cur', avg)
                acc_eval += qty * cur
                acc_buy += qty * avg
                all_pos.append({
                    "broker": adapter.broker,
                    "account_id": acc_id,
                    "account_name": adapter.name,
                    "code": code,
                    "qty": qty,
                    "avg": avg,
                    "cur": cur,
                    "pl": (cur - avg) * qty,
                    "pl_pct": ((cur - avg) / avg * 100) if avg else 0
                })

            total_cash += cash
            total_eval += acc_eval
            total_buy += acc_buy

            result.append({
                "id": acc_id,
                "name": adapter.name,
                "broker": adapter.broker,
                "cash": cash,
                "eval": acc_eval,
                "buy": acc_buy,
                "pl": acc_eval - acc_buy,
                "pl_pct": ((acc_eval - acc_buy) / acc_buy * 100) if acc_buy else 0,
                "positions": positions
            })

        return {
            "accounts": result,
            "summary": {
                "total_cash": total_cash,
                "total_eval": total_eval,
                "total_buy": total_buy,
                "total_pl": total_eval - total_buy,
                "total_pl_pct": ((total_eval - total_buy) / total_buy * 100) if total_buy else 0,
                "total_asset": total_cash + total_eval
            },
            "all_positions": all_pos
        }

    @staticmethod
    def _validate_balance(balance):
        if not isinstance(balance, Mapping):
            raise ValueError("balance must be a mapping")
        cash = balance.get('cash')
        positions = balance.get('positions')
        if (
            isinstance(cash, bool)
            or not isinstance(cash, (int, float))
            or not math.isfinite(cash)
            or cash < 0
        ):
            raise ValueError("balance cash must be a non-negative finite number")
        if not isinstance(positions, Mapping):
            raise ValueError("balance positions must be a mapping")

        normalized_positions = {}
        for code, position in positions.items():
            if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
                raise ValueError("balance position code must be a six-digit string")
            if not isinstance(position, Mapping):
                raise ValueError("balance position must be a mapping")
            qty = position.get('qty')
            avg = position.get('avg')
            current = position.get('cur')
            if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
                raise ValueError("balance position quantity must be a positive integer")
            if any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0
                for value in (avg, current)
            ):
                raise ValueError("balance position prices must be positive finite numbers")
            normalized_positions[code] = {
                "qty": qty,
                "avg": avg,
                "cur": current,
            }
        return {"cash": cash, "positions": normalized_positions}

    def sell_stock(self, account_id: str, code: str, qty: int):
        if account_id not in self.adapters:
            return {"error": f"계좌 {account_id} 없음"}
        return self.adapters[account_id].sell_market(code, qty)

# 사용 예시
if __name__ == "__main__":
    mgr = MultiAccountManager()
    summary = mgr.get_all_balances()
    print(f"총 자산: {summary['summary']['total_asset']:,}원")
    print(f"총 손익: {summary['summary']['total_pl']:,}원")
    for acc in summary['accounts']:
        print(f"- {acc['name']} ({acc['broker']}): {acc['eval']:,}원 손익 {acc['pl']:,}")
