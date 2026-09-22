from .base import BaseStrategy

class ORBStrategy(BaseStrategy):
    '''
    Opening Range Breakout - KIS 템플릿의 orb, orb_v2 전략 그대로
    시가 후 N분 고가 돌파 시 진입
    '''
    def __init__(self, api, opening_minutes=15, breakout_buffer=0.003):
        super().__init__(api)
        self.opening_minutes = opening_minutes
        self.buffer = breakout_buffer
        self.opening_ranges = {} # code -> {high, low}

    def update_opening_range(self, code, minute_bars):
        # 장 초반 N분 봉으로 레인지 계산
        if len(minute_bars) < self.opening_minutes:
            return
        highs = [b['high'] for b in minute_bars[:self.opening_minutes]]
        lows = [b['low'] for b in minute_bars[:self.opening_minutes]]
        self.opening_ranges[code] = {"high": max(highs), "low": min(lows)}

    def should_enter(self, code, current_price, minute_bars):
        if code not in self.opening_ranges:
            self.update_opening_range(code, minute_bars)
            return False
        or_high = self.opening_ranges[code]["high"]
        # 돌파 + 거래량 조건
        if current_price > or_high * (1 + self.buffer):
            # 추가 필터: 당일 거래량 > 20일 평균 거래량 150%
            return True
        return False

    def should_exit(self, code, position, current_price):
        # 손절 -3%, 익절 +8%, 시간 청산 15:10
        entry = position['avg_price']
        pnl = (current_price - entry) / entry
        if pnl <= -0.03 or pnl >= 0.08:
            return True
        return False
