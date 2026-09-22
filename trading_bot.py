from api.kiwoom_auth import KiwoomAuth
from api.kiwoom_api import KiwoomAPI
from strategies.orb import ORBStrategy
from strategies.bull_flag import BullFlagStrategy
import time
from datetime import datetime

# === 설정 ===
APP_KEY = "YOUR_KIWOOM_APP_KEY"
APP_SECRET = "YOUR_KIWOOM_APP_SECRET"
WATCHLIST = ["005930", "000660", "035720"] # 삼성전자, 하이닉스, 카카오
QTY = 5

auth = KiwoomAuth(APP_KEY, APP_SECRET)
api = KiwoomAPI(auth)

orb = ORBStrategy(api, opening_minutes=15)
bull_flag = BullFlagStrategy(api)

positions = {} # code -> {avg_price, qty, entry_time}

def run():
    print(f"=== 키움 ORB+BullFlag 봇 시작 {datetime.now()} ===")
    while True:
        now = datetime.now()
        # 장시간 09:05~15:15만 동작 (KIS 템플릿과 동일)
        if not (9 <= now.hour <= 15):
            time.sleep(60)
            continue

        for code in WATCHLIST:
            try:
                minute_bars = api.get_minute_chart(code, tick=1) # 1분봉
                if not minute_bars:
                    # API 연결 전이면 더미 데이터로 테스트
                    minute_bars = [{"open":10000,"high":10200,"low":9900,"close":10100,"volume":100000}]*20
                current_price = minute_bars[0]['close'] if minute_bars else 0

                # 보유 중이면 청산 체크
                if code in positions:
                    pos = positions[code]
                    pos['hold_minutes'] = (now - pos['entry_time']).seconds // 60
                    if orb.should_exit(code, pos, current_price) or bull_flag.should_exit(code, pos, current_price):
                        api.sell_market(code, pos['qty'])
                        del positions[code]
                        print(f"[EXIT] {code} 청산 @ {current_price}")
                    continue

                # 진입 체크 - ORB 또는 BullFlag 둘 중 하나라도 True면 진입
                enter_orb = orb.should_enter(code, current_price, minute_bars)
                enter_flag = bull_flag.should_enter(code, minute_bars)

                if enter_orb or enter_flag:
                    reason = "ORB" if enter_orb else "BullFlag"
                    print(f"[ENTER] {code} {reason} 진입 @ {current_price}")
                    api.buy_market(code, QTY)
                    positions[code] = {"avg_price": current_price, "qty": QTY, "entry_time": now}

            except Exception as e:
                print(f"[ERROR] {code} {e}")

        time.sleep(5) # 5초마다 스캔

if __name__ == "__main__":
    run()
