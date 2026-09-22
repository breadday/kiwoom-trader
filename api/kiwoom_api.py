import requests, time, random
from .kiwoom_auth import KiwoomAuth

class KiwoomAPI:
    def __init__(self, auth: KiwoomAuth, paper=True):
        self.auth = auth
        self.paper = paper
        self.base_real = f"{auth.base_url}/api"
        self.base_paper = f"{auth.base_url}/api/mock" # 키움 모의투자 prefix (가정, 실제로는 동일 URL에 계좌구분)
        self.base = self.base_paper if paper else self.base_real
        self.last_req = 0
        self.paper_balance = {"cash": 10000000, "positions": {}}
        print(f"[MODE] {'모의투자' if paper else '실전'} 모드")

    def _throttle(self):
        elapsed = time.time() - self.last_req
        if elapsed < 0.21:
            time.sleep(0.21 - elapsed)
        self.last_req = time.time()

    def get_minute_chart(self, code, tick=1):
        self._throttle()
        if self.paper:
            # 모의 데이터는 백테스트에서 주입
            return []
        url = f"{self.base}/dostk/mintick"
        r = requests.post(url, headers=self.auth.headers(), json={"stk_cd": code, "tic_scope": tick})
        return r.json().get("chart", [])

    def buy_market(self, code, qty, price=50000):
        self._throttle()
        if self.paper:
            cost = qty * price
            if self.paper_balance["cash"] >= cost:
                self.paper_balance["cash"] -= cost
                pos = self.paper_balance["positions"].get(code, {"qty":0,"avg":0})
                total = pos["qty"]*pos["avg"] + cost
                pos["qty"] += qty
                pos["avg"] = total / pos["qty"]
                self.paper_balance["positions"][code] = pos
                print(f"[PAPER BUY] {code} {qty}주 @{price} 잔고 {self.paper_balance['cash']:,}")
                return {"order_no": "paper_"+str(int(time.time())), "status":"filled"}
        # 실전
        url = f"{self.base}/v1/trading/order"
        return requests.post(url, headers=self.auth.headers(), json={"stk_cd": code, "ord_qty": str(qty), "trde_tp": "3"}).json()

    def sell_market(self, code, qty, price=50000):
        self._throttle()
        if self.paper:
            pos = self.paper_balance["positions"].get(code)
            if pos and pos["qty"] >= qty:
                self.paper_balance["cash"] += qty * price
                pos["qty"] -= qty
                if pos["qty"]==0: del self.paper_balance["positions"][code]
                print(f"[PAPER SELL] {code} {qty}주 @{price} 잔고 {self.paper_balance['cash']:,}")
                return {"status":"filled"}
        url = f"{self.base}/v1/trading/order"
        return requests.post(url, headers=self.auth.headers(), json={"stk_cd": code, "ord_qty": str(qty), "trde_tp": "3", "trde_sec_tp":"1"}).json()

    def get_balance(self):
        if self.paper:
            return self.paper_balance
        url = f"{self.base}/v1/account/balance"
        return requests.get(url, headers=self.auth.headers()).json()