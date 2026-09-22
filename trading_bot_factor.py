from api.kiwoom_auth import KiwoomAuth
from api.kiwoom_api import KiwoomAPI
from strategies.factor_swing import FactorSwingStrategy
import pandas as pd
from datetime import datetime
import time

APP_KEY = "YOUR_KIWOOM_APP_KEY"
APP_SECRET = "YOUR_KIWOOM_APP_SECRET"

auth = KiwoomAuth(APP_KEY, APP_SECRET)
api = KiwoomAPI(auth, paper=True)  # 모의투자 True
strategy = FactorSwingStrategy(api, top_n=20)

# KOSPI200 리스트 (실제로는 api로 가져옴)
WATCHLIST = ["005930","000660","035720","051910","006400","035420","005380","012330","028260","055550",
             "032830","105560","003550","086790","000270","096770","015760","017670","018260","033780"]

def get_price_history():
    # 실제로는 api.get_daily_chart(code) 250일치 호출
    # 여기선 더미: 각 종목 250일 생성 (백테스트와 동일한 gen 함수)
    import numpy as np
    history = {}
    for code in WATCHLIST:
        np.random.seed(hash(code)%10000)
        prices = [50000]
        for _ in range(250):
            prices.append(prices[-1]*(1+np.random.normal(0.0005, 0.015)))
        df = pd.DataFrame({"close": prices, "volume": np.random.randint(100000,1000000, len(prices))})
        history[code] = df
    return history

def run_once():
    print(f"=== 팩터 스윙 리밸런싱 {datetime.now()} ===")
    history = get_price_history()
    picks = strategy.pick(history)
    print(picks[["code","score","mom","lowvol","close"]].head(10).to_string())

    balance = api.get_balance()
    cash = balance["cash"]
    per_stock = cash * 0.95 / len(picks)  # 95% 투자

    # 기존 보유 청산 (간소화: 전량 매도 후 재매수)
    for code in list(balance["positions"].keys()):
        if code not in picks["code"].values:
            api.sell_market(code, balance["positions"][code]["qty"], price=history[code]["close"].iloc[-1])

    # 신규 매수
    for _, row in picks.iterrows():
        code = row["code"]
        price = row["close"]
        qty = int(per_stock // price)
        if qty>0 and code not in api.get_balance()["positions"]:
            api.buy_market(code, qty, price=price)

    print(f"리밸런싱 완료. 잔고: {api.get_balance()['cash']:,}")

if __name__ == "__main__":
    run_once()