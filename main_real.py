# main_real.py - 실거래 전용 진입점 (4중 잠금)
import sys
import os
from config_live import IS_REAL_ENV, LiveTradingArmed, can_place_real_order, LIVE_TRADING_PIN

print("=== 실거래 모드 진입 체크 ===")

# 1차 체크: 파일명
current_file = os.path.basename(sys.argv[0])
if current_file!= "main_real.py":
    print(f"[차단] 파일명이 {current_file} 입니다. main_real.py 로 실행해야 합니다.")
    sys.exit(1)

# 2차 체크: IS_REAL_ENV
if not IS_REAL_ENV:
    print("[차단] config_live.py 에서 IS_REAL_ENV = True 로 변경해야 실거래 가능")
    print("지금은 모의모드입니다.")
    sys.exit(1)

# 3차 체크: 무장 스위치
if not LiveTradingArmed:
    print("[차단] LiveTradingArmed = False 입니다. config_live.py에서 True로 변경하세요.")
    sys.exit(1)

# 4차 체크: PIN 입력
pin = input(f"실거래 PIN 4자리를 입력하세요 (힌트: {LIVE_TRADING_PIN[0]}***): ")
ok, msg = can_place_real_order(current_file, pin)
if not ok:
    print(f"[차단] {msg}")
    sys.exit(1)

print(f"[해제] {msg} - 실거래 시작!")

# === 여기부터 실제 매매 로직 ===
from kiwoom_broker import KiwoomBroker

broker = KiwoomBroker()
broker.is_real_mode = True
broker.pin_input = pin

print("브로커 연결 성공! 소액 테스트 주문을 넣을 준비 완료")

# 테스트용: 절대 바로 주문 넣지 말고, 먼저 잔고 조회부터
# broker.get_balance()
# broker.place_order("005930", 1, "BUY") # 삼성전자 1주 테스트
