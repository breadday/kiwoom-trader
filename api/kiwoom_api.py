import requests, time, random
from datetime import datetime, timedelta, timezone
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

    def get_daily_chart(self, code, base_dt=None, limit=60, max_pages=10):
        """Read adjusted daily OHLCV bars from Kiwoom ka10081.

        The official contract requires YYYYMMDD. If omitted, use the previous
        KST calendar date so an unfinished current-session bar is not selected;
        callers may provide a date explicitly. For adjusted history, the base
        date must be after the relevant corporate-action date.

        This is a read-only market-data request and is deliberately independent
        of the paper/real order mode. It never places or simulates an order.
        Returns normalized bars in ascending date order.
        """
        if not isinstance(code, str) or not code.strip():
            raise ValueError("code must be a non-empty stock code")
        if base_dt is None:
            kst = timezone(timedelta(hours=9))
            base_dt = (datetime.now(kst).date() - timedelta(days=1)).strftime("%Y%m%d")
        if not isinstance(base_dt, str) or len(base_dt) != 8 or not base_dt.isdigit():
            raise ValueError("base_dt must be a valid YYYYMMDD date")
        try:
            datetime.strptime(base_dt, "%Y%m%d")
        except ValueError as exc:
            raise ValueError("base_dt must be a valid YYYYMMDD date") from exc
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        if isinstance(max_pages, bool) or not isinstance(max_pages, int) or max_pages <= 0:
            raise ValueError("max_pages must be a positive integer")
        url = f"{self.auth.base_url.rstrip('/')}/api/dostk/chart"
        bars_by_date = {}
        total_rows = 0
        continuation = None
        seen_next_keys = set()

        for page_index in range(max_pages):
            self._throttle()
            headers = dict(self.auth.headers())
            headers.update({
                "Content-Type": "application/json;charset=UTF-8",
                "api-id": "ka10081",
            })
            if continuation is not None:
                headers["cont-yn"] = "Y"
                headers["next-key"] = continuation

            response = requests.post(
                url,
                headers=headers,
                json={"stk_cd": code, "base_dt": base_dt, "upd_stkpc_tp": "1"},
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise RuntimeError("Kiwoom daily chart response must be an object")
            return_code = payload.get("return_code")
            if return_code not in (0, "0"):
                raise RuntimeError(payload.get("return_msg") or f"Kiwoom daily chart failed: {return_code!r}")

            if "stk_dt_pole_chart_qry" not in payload or payload["stk_dt_pole_chart_qry"] is None:
                raise RuntimeError("Kiwoom daily chart rows field is missing or null")
            rows = payload["stk_dt_pole_chart_qry"]
            if not isinstance(rows, list):
                raise RuntimeError("Kiwoom daily chart rows must be a list")
            total_rows += len(rows)
            if total_rows > 10000:
                raise RuntimeError("Kiwoom daily chart response contains too many rows across pages")
            for row in rows:
                if not isinstance(row, dict):
                    raise RuntimeError(f"Invalid Kiwoom daily chart row: {row!r}")
                try:
                    date = str(row["dt"])
                    if len(date) != 8 or not date.isdigit():
                        raise ValueError("invalid date")
                    datetime.strptime(date, "%Y%m%d")
                    bar = {
                        "date": date,
                        "open": int(str(row["open_pric"]).replace(",", "").strip().lstrip("+")),
                        "high": int(str(row["high_pric"]).replace(",", "").strip().lstrip("+")),
                        "low": int(str(row["low_pric"]).replace(",", "").strip().lstrip("+")),
                        "close": int(str(row["cur_prc"]).replace(",", "").strip().lstrip("+")),
                        "volume": int(str(row["trde_qty"]).replace(",", "").strip()),
                    }
                    if (
                        min(bar["open"], bar["high"], bar["low"], bar["close"]) <= 0
                        or bar["volume"] < 0
                        or bar["low"] > min(bar["open"], bar["close"])
                        or bar["high"] < max(bar["open"], bar["close"])
                    ):
                        raise ValueError("OHLC prices must be positive and internally consistent; volume must be non-negative")
                except (KeyError, TypeError, ValueError) as exc:
                    raise RuntimeError(f"Invalid Kiwoom daily chart row: {row!r}") from exc
                bars_by_date[date] = bar

            if len(bars_by_date) >= limit:
                break
            response_headers = response.headers
            has_more = str(response_headers.get("cont-yn", "N")).upper() == "Y"
            next_key = response_headers.get("next-key", "")
            if not has_more:
                break
            if not next_key:
                raise RuntimeError("Kiwoom indicated another chart page without a next-key")
            if next_key in seen_next_keys:
                raise RuntimeError("Kiwoom repeated a daily chart next-key")
            if page_index + 1 >= max_pages:
                raise RuntimeError("Kiwoom daily chart exceeded max_pages before reaching the requested limit")
            seen_next_keys.add(next_key)
            continuation = next_key

        return [bars_by_date[date] for date in sorted(bars_by_date)[-limit:]]

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