# 자동 개발 STEP 08D — 백테스트 품질·결과 보고 계획

## 목표

현재 승인된 RESCUE/FACTOR 백테스트 계약의 실행 가정과 성과지표가 코드·테스트·문서에서 일치하는지 확인한다.

## 고정 가정

- RESCUE: 첫 종가 진입, 이후 종가 임계치 평가, 즉시청산 우선, 부분청산 1회
- FACTOR: 252-bar lookback + 60-bar 평가, 월요일 종가 신호, 다음 거래일 시가 체결
- 수수료·세금·슬리피지·장중 체결경로는 모델링하지 않음
- 수익률·MDD·Sharpe·승률·보유일은 투자수익 보장이나 매수 추천이 아님

## 완료 조건

1. look-ahead 방지와 open-gap 체결이 회귀 테스트로 고정된다.
2. total return, MDD, Sharpe, win rate, average hold days 정의가 문서와 일치한다.
3. 합성 fixture 결과를 실적 또는 투자추천으로 표현하지 않는다.
