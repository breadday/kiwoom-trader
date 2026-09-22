from api.kiwoom_auth import KiwoomAuth
from api.kiwoom_api import KiwoomAPI
from strategies.factor_swing import FactorSwingStrategy
import pandas as pd
from datetime import datetime

# === 네 실제 계좌 상태 (사진 기준) ===
REAL_POSITIONS = {
    "003400": {"name":"삼성전자우", "qty":6, "avg":229500, "current":208000}, # 005930우 -> 005935지만 예시로
    "058610": {"name":"LB세미콘", "qty":400, "avg":5630, "current":4330},
    "019310": {"name":"하나마이크론", "qty":141, "avg":41903, "current":44800},
    "086520": {"name":"에코프로", "qty":12, "avg":161700, "current":79900},
    "071950": {"name":"네오셈", "qty":113, "avg":17710, "current":13020},
    "078430": {"name":"한화시스템", "qty":20, "avg":120600, "current":76500},
    "097950": {"name":"스피어", "qty":217, "avg":41814, "current":23300},
    "297570": {"name":"신성에스티", "qty":185, "avg":38990, "current":23850},
}
CASH = 200918

APP_KEY = "YOUR_KEY"
APP_SECRET = "YOUR_SECRET"

auth = KiwoomAuth(APP_KEY, APP_SECRET)
api = KiwoomAPI(auth, paper=True)

# 실제 포지션을 paper_balance에 주입
api.paper_balance["cash"] = CASH
api.paper_balance["positions"] = {code: {"qty":v["qty"], "avg":v["avg"]} for code,v in REAL_POSITIONS.items()}

print("=== 현재 계좌 진단 ===")
total_eval = CASH
loss = 0
for code, v in REAL_POSITIONS.items():
    eval_amt = v["qty"]*v["current"]
    total_eval += eval_amt
    pnl = (v["current"]-v["avg"])*v["qty"]
    loss += pnl
    print(f"{v['name']} {code}: {v['qty']}주 {pnl:+,}원 ({pnl/v['qty']/v['avg']*100:.1f}%)")

print(f"\n총 평가: {total_eval:,}원 / 손실: {loss:+,}원")

# 팩터 전략으로 리밸런싱 시뮬레이션
strategy = FactorSwingStrategy(api, top_n=10)

# 더미 price_history 생성 (실전에서는 api.get_daily_chart로 교체)
import numpy as np
history = {}
for code in REAL_POSITIONS.keys():
    np.random.seed(hash(code)%1000)
    closes = [v["avg"] for v in [REAL_POSITIONS[code]]]
    # 현재가까지 떨어지는 추세 생성
    for i in range(250):
        closes.append(closes[-1]*(1+np.random.normal(-0.0005, 0.02)))
    history[code] = pd.DataFrame({"close": closes, "volume": np.random.randint(100000,1000000, len(closes))})

# 팩터 점수 계산
picks = strategy.calc_factors(history)
print("\n=== 팩터 점수 (네 보유종목) ===")
print(picks[["code","score","mom","lowvol"]].to_string())

print("\n=== 구조조정 시뮬레이션 (3주 분할) ===")
for week in range(1,4):
    print(f"\n[{week}주차] 매도 실행:")
    for code, v in REAL_POSITIONS.items():
        if v["current"] < v["avg"]*0.7: # -30% 이상
            qty_sell = v["qty"]//3
            if qty_sell>0:
                print(f"  {v['name']} {qty_sell}주 매도 -> 팩터 상위 종목 교체 예정")
                # api.sell_market(code, qty_sell, price=v["current"])

print("\n시뮬레이션 완료. 실제 매매하려면 paper=False로 변경하고 APP_KEY 입력하세요.")