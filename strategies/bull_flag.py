from .base import BaseStrategy

class BullFlagStrategy(BaseStrategy):
    '''
    Bull Flag - 급등 후 3~5개 봉 횡보, 거래량 감소 후 돌파
    KIS 템플릿의 bull_flag 전략을 키움용으로 포팅
    win rate 높은 단타 중 하나
    '''
    def __init__(self, api, flag_bars=5, volume_decay=0.7):
        super().__init__(api)
        self.flag_bars = flag_bars
        self.volume_decay = volume_decay

    def should_enter(self, code, minute_bars):
        # minute_bars: 최신이 0번째
        if len(minute_bars) < 20:
            return False

        # 1. 플래그 전 강한 상승: 15분 전 대비 +2% 이상
        recent = minute_bars[0]
        past = minute_bars[10]
        pole_gain = (recent['close'] - past['close']) / past['close']
        if pole_gain < 0.02:
            return False

        # 2. 플래그 구간: 고점이 낮아지거나 횡보, 거래량 감소
        flag_section = minute_bars[1:1+self.flag_bars]
        vols = [b['volume'] for b in flag_section]
        avg_vol_before = sum([b['volume'] for b in minute_bars[10:15]]) / 5

        if sum(vols)/len(vols) > avg_vol_before * self.volume_decay:
            return False # 거래량 안줄었으면 플래그 아님

        # 3. 현재가 돌파
        flag_high = max([b['high'] for b in flag_section])
        if recent['close'] > flag_high * 1.001:
            return True
        return False

    def should_exit(self, code, position, current_price):
        entry = position['avg_price']
        pnl = (current_price - entry) / entry
        # bull flag는 짧게 먹고 빠짐
        if pnl <= -0.02 or pnl >= 0.05:
            return True
        # 진입 후 30분 지나면 청산
        if position.get('hold_minutes', 0) > 30:
            return True
        return False
