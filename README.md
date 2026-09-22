# 키움 팩터/스윙 구조조정 봇

## 폴더 구조
kiwoom_trader/
  api/
    kiwoom_auth.py
    kiwoom_api.py  # paper=True면 모의투자
  strategies/
    orb_bull_flag.py
    factor_swing.py
  trading_bot.py
  trading_bot_factor.py
  kiwoom_rescue_bot.py  # 네 계좌 진단용
  backtest_factor.py

## 실행 방법
1. python kiwoom_rescue_bot.py -> 현재 계좌 진단 + 3주 분할 매도 시뮬레이션
2. python trading_bot_factor.py -> 매주 월요일 팩터 리밸런싱 (모의투자)
3. paper=False + APP_KEY 입력하면 실전 주문

## 네 계좌용 설정
- 예수금 200,918원으로는 리밸런싱 불가 -> 500만원 이상 권장
- top_n=10으로 줄이면 소액도 가능

## 확인 방법
- backtest_factor_summary.txt에서 1년 수익률 확인
- rescue_bot 실행 시 팩터 점수 확인