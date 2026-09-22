import pandas as pd, numpy as np, pathlib

np.random.seed(7)
# 1년치 백테스트: 매주 월요일 리밸런싱
WATCHLIST = [f"{i:06d}" for i in range(20)]
days = 252
# 종목별 가격 생성
prices = {code: [50000 + np.random.randint(-5000,5000)] for code in WATCHLIST}
history_daily = {code: [] for code in WATCHLIST}
for d in range(days):
    for code in WATCHLIST:
        last = prices[code][-1]
        # 일부 종목은 모멘텀 강하게
        drift = 0.001 if int(code)%5==0 else 0.0002
        new = last * (1 + np.random.normal(drift, 0.015))
        prices[code].append(new)
        history_daily[code].append(new)

# 팩터 백테스트
cash = 10000000
positions = {}
nav = []

for day in range(60, days):
    if day % 5 != 0: # 월요일만
        # NAV 계산
        total = cash + sum(positions.get(c,{}).get('qty',0)*prices[c][day] for c in WATCHLIST)
        nav.append(total)
        continue

    # 250일 히스토리로 팩터 계산
    rows = []
    for code in WATCHLIST:
        closes = pd.Series(prices[code][day-250:day])
        if len(closes)<200: continue
        mom = closes.iloc[-21]/closes.iloc[0]-1
        vol = closes.pct_change().iloc[-60:].std()
        lowvol = 1/vol if vol else 0
        rows.append({"code":code, "mom":mom, "lowvol":lowvol, "close":closes.iloc[-1]})

    df = pd.DataFrame(rows)
    if df.empty: continue
    for col in ["mom","lowvol"]:
        df[col+"_z"] = (df[col]-df[col].mean())/(df[col].std()+1e-9)
    df["score"] = df["mom_z"]*0.6 + df["lowvol_z"]*0.4
    df = df.sort_values("score", ascending=False)
    picks = df.head(5)

    # 전량 청산 후 재매수
    for code in list(positions.keys()):
        cash += positions[code]['qty'] * prices[code][day]
    positions = {}
    per = cash * 0.95 / len(picks)
    for _, r in picks.iterrows():
        qty = int(per // r["close"])
        if qty>0:
            positions[r["code"]] = {"qty": qty}
            cash -= qty * r["close"]

    total = cash + sum(positions[c]['qty']*prices[c][day] for c in positions)
    nav.append(total)

nav_s = pd.Series(nav)
ret = nav_s.pct_change().fillna(0)
total_ret = (nav_s.iloc[-1]/10000000 -1)*100
win_m = (ret>0).mean()*100
sharpe = (ret.mean()/ret.std()* (252/5)**0.5) if ret.std()>0 else 0
mdd = (nav_s.cummax() - nav_s) / nav_s.cummax()
mdd = mdd.max()*100

out = pathlib.Path("/mnt/data/kiwoom_trader/backtest_factor_summary.txt")
out.write_text(f'''=== 팩터/스윙 백테스트 (1년, 주간 리밸런싱, 20종목 중 Top5) ===
초기자금: 10,000,000
최종 NAV: {nav_s.iloc[-1]:,.0f}
총 수익률: {total_ret:.2f}%
월 평균 승률(주): {win_m:.1f}%
샤프: {sharpe:.2f}
MDD: {mdd:.2f}%
거래수: {len(nav)}
전략: mom 60% + lowvol 40%, 월요일 리밸런싱
''', encoding='utf-8')

print(out.read_text())
# NAV csv
pd.DataFrame({"nav": nav}).to_csv("/mnt/data/kiwoom_trader/backtest_factor_nav.csv", index=False)