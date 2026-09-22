import pandas as pd
import numpy as np

class FactorSwingStrategy:
    '''
    팩터/스윙 안정형 - 연 10~15% 목표
    Value + Momentum(12M-1M) + Quality + LowVol(1/60일 변동성)
    Z-Score 합산 후 상위 N종목 동일비중, 주 1회 리밸런싱
    KIS 템플릿의 kis_hhong 로직을 키움용으로 포팅
    '''
    def __init__(self, api, top_n=20):
        self.api = api
        self.top_n = top_n

    def calc_factors(self, price_history: dict):
        '''
        price_history: {code: DataFrame with close, volume, ... 최소 250일}
        '''
        rows = []
        for code, df in price_history.items():
            if len(df) < 200:
                continue
            close = df['close']
            # 1. Momentum 12M-1M: 252일~21일 전 수익률
            try:
                mom_12_1 = (close.iloc[-21] / close.iloc[-252] - 1) if len(close) > 252 else (close.iloc[-21]/close.iloc[0]-1)
            except:
                mom_12_1 = 0
            # 2. LowVol: 1 / std(60일 수익률)
            ret_60 = close.pct_change().iloc[-60:]
            vol = ret_60.std()
            lowvol = 1/vol if vol and vol>0 else 0
            # 3. Quality 대용: 60일 평균 거래대금 (유동성 필터)
            quality = df['volume'].iloc[-60:].mean() if 'volume' in df else 0
            # 4. Value 대용: 60일 모멘텀 역전 (저평가 프록시, 실제는 PER/PBR 연동 필요)
            # 여기서는 단순화: 60일 하락 후 반등 종목 선호
            mom_60 = (close.iloc[-1] / close.iloc[-60] - 1)
            value_proxy = -mom_60  # 과매도 종목에 가점

            rows.append({
                "code": code,
                "mom": mom_12_1,
                "lowvol": lowvol,
                "quality": quality,
                "value": value_proxy,
                "close": close.iloc[-1]
            })
        factor_df = pd.DataFrame(rows)
        if factor_df.empty:
            return factor_df

        # Z-Score 정규화
        for col in ["mom","lowvol","quality","value"]:
            mean = factor_df[col].mean()
            std = factor_df[col].std()
            factor_df[col+"_z"] = (factor_df[col]-mean)/(std+1e-9)

        # 유동성 필터: quality 하위 30% 제외 (거래대금 적은 잡주 제거)
        factor_df = factor_df[factor_df["quality"] > factor_df["quality"].quantile(0.3)]

        # 종합 점수: 가중치 mom 40% + lowvol 30% + quality 20% + value 10%
        factor_df["score"] = factor_df["mom_z"]*0.4 + factor_df["lowvol_z"]*0.3 + factor_df["quality_z"]*0.2 + factor_df["value_z"]*0.1

        return factor_df.sort_values("score", ascending=False)

    def pick(self, price_history):
        df = self.calc_factors(price_history)
        return df.head(self.top_n)

    def should_rebalance(self, last_date, today):
        # 주 1회 월요일 리밸런싱
        return today.weekday() == 0  # 0=월요일