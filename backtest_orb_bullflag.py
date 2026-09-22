import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# VectorBT가 없으므로 pandas로 ORB+BullFlag 백테스트 직접 구현
np.random.seed(42)
# 30일치 1분봉 더미 생성 (09:00~15:30, 390분)
def gen_day(base_price):
    # 장초반 변동성 크게
    minutes = 390
    prices = [base_price]
    for i in range(1, minutes):
        vol = 0.002 if i < 30 else 0.0008
        prices.append(prices[-1] * (1 + np.random.normal(0, vol)))
    df = pd.DataFrame({
        'open': prices,
        'high': [p* (1+abs(np.random.normal(0,0.001))) for p in prices],
        'low': [p* (1-abs(np.random.normal(0,0.001))) for p in prices],
        'close': prices,
        'volume': [int(np.random.normal(200000, 50000)) for _ in prices]
    })
    # 거래량 장초반 급증 패턴 삽입 (ORB 유도)
    df.loc[0:15, 'volume'] *= 3
    return df

results = []
all_trades = []

for day in range(30):
    base_price = 70000 + day*100 + np.random.randint(-500,500)
    df = gen_day(base_price)

    opening_high = df.iloc[0:15]['high'].max()
    opening_low = df.iloc[0:15]['low'].min()

    position = None
    for i in range(15, len(df)):
        price = df.iloc[i]['close']
        vol = df.iloc[i]['volume']
        # ORB 진입
        enter_orb = price > opening_high * 1.003 and vol > df['volume'].mean()*1.2

        # BullFlag 진입 (간소화)
        if i > 20:
            pole_gain = (df.iloc[i-1]['close'] - df.iloc[i-10]['close']) / df.iloc[i-10]['close']
            flag_vol = df.iloc[i-5:i]['volume'].mean()
            before_vol = df.iloc[i-15:i-10]['volume'].mean()
            flag_high = df.iloc[i-5:i]['high'].max()
            enter_flag = pole_gain > 0.015 and flag_vol < before_vol*0.7 and price > flag_high*1.001
        else:
            enter_flag = False

        if position is None and (enter_orb or enter_flag):
            position = {'entry': price, 'idx': i, 'type': 'ORB' if enter_orb else 'Flag'}

        if position:
            pnl = (price - position['entry']) / position['entry']
            hold = i - position['idx']
            # 청산 조건: -2% / +5% / 30분
            if pnl <= -0.02 or pnl >= 0.05 or hold >= 30:
                results.append(pnl)
                all_trades.append({
                    'day': day, 'type': position['type'], 'entry': position['entry'],
                    'exit': price, 'pnl': pnl, 'hold': hold
                })
                position = None

df_results = pd.DataFrame(all_trades)
win_rate = (df_results['pnl'] > 0).mean()*100 if len(df_results)>0 else 0
avg_pnl = df_results['pnl'].mean()*100 if len(df_results)>0 else 0
sharpe = (df_results['pnl'].mean() / df_results['pnl'].std() * np.sqrt(252*6.5)) if len(df_results)>1 else 0
total_return = df_results['pnl'].sum()*100
mdd = df_results['pnl'].cumsum().max() - df_results['pnl'].cumsum().min() if len(df_results)>0 else 0

print(f"Trades: {len(df_results)}")
print(f"WinRate: {win_rate:.1f}%")
print(f"Avg PnL: {avg_pnl:.2f}%")
print(f"Total: {total_return:.2f}%")
print(f"Sharpe~: {sharpe:.2f}")

# Save report
report_path = "/mnt/data/kiwoom_trader/backtest_report.csv"
df_results.to_csv(report_path, index=False)

summary_path = "/mnt/data/kiwoom_trader/backtest_summary.txt"
with open(summary_path, 'w') as f:
    f.write(f"=== ORB + BullFlag 백테스트 (30일, 1분봉 더미 기반) ===\n")
    f.write(f"총 거래수: {len(df_results)}\n")
    f.write(f"승률: {win_rate:.1f}%\n")
    f.write(f"평균 수익률: {avg_pnl:.2f}%\n")
    f.write(f"누적 수익률(합): {total_return:.2f}%\n")
    f.write(f"샤프(연환산 추정): {sharpe:.2f}\n")
    f.write(f"MDD(추정): {mdd*100:.2f}%\n")
    f.write(f"\n상위 5개 트레이드:\n")
    f.write(df_results.sort_values('pnl', ascending=False).head().to_string())

print(f"Saved {report_path}, {summary_path}")