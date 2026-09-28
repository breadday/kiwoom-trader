# 자동 개발 STEP 08D — 백테스트 품질·결과 보고 결과

## 상태

- 기준일: 2026-09-28
- 결과: 기존 계약과 회귀 검증 완료
- 관련 optimizer 테스트: 30개 통과
- 코드 변경: 지표 경계 assertion 보강

## 확인 결과

- RESCUE synthetic 경계에서 부분청산 결과는 총수익률 약 -15%, MDD 20%, 평균 보유일 30일로 계산된다.
- FACTOR는 월요일 종가에서 신호를 계산하고 다음 거래일 시가에서 체결해 동일 종가 look-ahead를 피한다.
- FACTOR의 즉시청산 우선, 부분청산 1회, 마지막 horizon 미체결 경계가 유지된다.
- 수수료·세금·슬리피지 및 장중 가격경로는 결과에 포함하지 않는다.
- 모든 수치는 synthetic/fake bar 기반이며 투자추천·수익보장으로 해석하지 않는다.

## 검증 명령

```text
python -m unittest tests.test_optimizer_daily_backtest tests.test_optimizer_factor_backtest -q
Ran 30 tests
OK
```

## 남은 한계

실제 수정주가 기준, 거래일 캘린더, 장중 체결·시장충격, 비용 모델은 승인된 데이터와 별도 정의가 필요하다.
