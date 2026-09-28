# 자동 개발 STEP 08C — read-only provider와 백테스트 경계 통합 계획

## 목표

`KiwoomAPI.get_daily_chart`를 `StrategyOptimizer.daily_chart_provider`에 연결하는 경계를 fixture 기반으로 검증한다. 전략 규칙·가중치·유니버스는 변경하지 않는다.

## 검증 범위

- RESCUE provider가 종목별 `limit=60`을 한 번 요청하는지
- FACTOR provider가 승인된 8종목별 `limit=312`를 한 번 요청하는지
- provider 오류와 불충분한 bar가 mock fallback 없이 fail-closed 되는지
- 날짜 정렬·OHLCV 검증이 optimizer 입구에서 유지되는지
- `max_pages=10`을 312개 확보의 근거로 간주하지 않는지

## 완료 조건

1. provider 경계 테스트가 통과한다.
2. 요청량과 승인 유니버스가 기존 계약과 일치한다.
3. 불충분한 데이터는 결과·추천을 생성하지 않고 명시적 오류가 된다.
4. 실제 API·계좌·주문 호출은 수행하지 않는다.
