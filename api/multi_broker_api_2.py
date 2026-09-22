
"""
멀티 브로커 통합 매니저 - 키움, NH, 삼성, KB
모든 증권사가 동일한 인터페이스로 동작
"""
from abc import ABC, abstractmethod
from typing import Dict, List
import yaml
from .kiwoom_api import KiwoomAPI
from .kiwoom_auth import KiwoomAuth

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
        if self.paper:
            return self.mock
        # TODO: 실제 NH API 연동
        # import requests; requests.post("https://apiportal.nhqv.com/...", ...)
        return self.mock

    def buy_market(self, code, qty):
        print(f"[NH PAPER BUY] {code} {qty}주")
        return {"status": "filled", "broker": "nh"}

    def sell_market(self, code, qty):
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
        return self.mock if self.paper else self.mock

    def buy_market(self, code, qty):
        return {"status": "filled", "broker": "samsung"}

    def sell_market(self, code, qty):
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
        return self.mock if self.paper else self.mock

    def buy_market(self, code, qty):
        return {"status": "filled", "broker": "kb"}

    def sell_market(self, code, qty):
        return {"status": "filled", "broker": "kb"}

class MultiAccountManager:
    def __init__(self, config_path="accounts.yaml"):
        self.adapters: Dict[str, BrokerAdapter] = {}
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f)
                for acc_cfg in cfg.get('accounts', []):
                    broker = acc_cfg['broker']
                    if broker == 'kiwoom':
                        adapter = KiwoomAdapter(acc_cfg)
                    elif broker == 'nh':
                        adapter = NHAdapter(acc_cfg)
                    elif broker == 'samsung':
                        adapter = SamsungAdapter(acc_cfg)
                    elif broker == 'kb':
                        adapter = KBAdapter(acc_cfg)
                    else:
                        continue
                    self.adapters[acc_cfg['id']] = adapter
        except FileNotFoundError:
            # 기본 4개 계좌 mock 생성
            print("[MultiAccount] accounts.yaml 없음, 기본 4개 mock 계좌 생성")
            self.adapters = {
                "kiwoom_main": KiwoomAdapter({"id": "kiwoom_main", "broker": "kiwoom", "name": "키움 주계좌", "paper": True}),
                "nh_main": NHAdapter({"id": "nh_main", "broker": "nh", "name": "NH투자", "paper": True}),
                "samsung_main": SamsungAdapter({"id": "samsung_main", "broker": "samsung", "name": "삼성증권", "paper": True}),
                "kb_main": KBAdapter({"id": "kb_main", "broker": "kb", "name": "KB증권", "paper": True}),
            }

    def get_all_balances(self):
        result = []
        total_cash = 0
        total_eval = 0
        total_buy = 0
        all_pos = []

        for acc_id, adapter in self.adapters.items():
            bal = adapter.get_balance()
            cash = bal.get('cash', 0)
            positions = bal.get('positions', {})

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
