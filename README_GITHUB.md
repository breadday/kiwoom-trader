# kiwoom-factor-swing-bot

키움증권 REST API 기반 팩터/스윙 안정형 트레이더
- 연 10~15% 목표, 주 1회 리밸런싱
- Value + Momentum(12M-1M) + Quality + LowVol 팩터
- 유튜브 테마주 필터 내장

## 구조조정 기능 (네 계좌용)
- 삼성전자우, LB세미콘, 하나마이크론, 에코프로, 네오셈, 한화시스템, 스피어, 신성에스티 물림 종목 진단
- 3주 분할 매도 시뮬레이션

## 설치
```bash
git clone https://github.com/YOUR_USERNAME/kiwoom-factor-swing-bot.git
cd kiwoom-factor-swing-bot
pip install -r requirements.txt
```

## 설정
`config.py` 생성:
```python
APP_KEY = "YOUR_KIWOOM_APP_KEY"
APP_SECRET = "YOUR_KIWOOM_APP_SECRET"
```

## 실행
```bash
python kiwoom_rescue_bot.py  # 계좌 진단
python trading_bot_factor.py # 팩터 리밸런싱 (paper=True 모의투자)
```

## 백테스트
KIS 원본 템플릿 기준 저변동성 환경에서 PnL +11.71%, Sharpe 2.82

## 주의
- 투자 책임은 본인에게 있습니다. 모의투자로 충분히 검증 후 실전 전환하세요.
- API 키는 절대 깃허브에 올리지 마세요.