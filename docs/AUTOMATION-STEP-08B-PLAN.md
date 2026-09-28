# 자동 개발 STEP 08B — fixture 기반 응답 정규화·페이지네이션 검증 계획

## 목표

STEP 08A에서 확인한 `ka10081` 계약을 실제 credential 없이 검증한다. 공식 공개 예제에서 민감정보 없는 fixture를 만들고, 응답 정규화와 연속조회 실패 경계를 fail-closed로 고정한다.

## 범위

- 공식 예제 fixture provenance와 민감정보 부재 메타데이터
- 단일/복수 페이지, 날짜 중복 제거, 오름차순 정렬
- `cont-yn`/`next-key` 누락 및 반복 key
- `max_pages` 한도
- API return code와 HTTP 오류 전달
- 콤마·공백·부호·0 거래량
- 누락/null/비정상 row와 OHLC 일관성

실 API 호출, 계좌·주문 응답 저장, rate limit 추정은 범위 밖이다.

## 완료 조건

1. fixture 출처·관측일·sanitization 상태가 기록된다.
2. 정규화·페이지네이션 경계 테스트가 RED/GREEN 증거와 함께 통과한다.
3. `StrategyOptimizer` 계약은 변경하지 않는다.
4. 실제 응답 동작이 확인되지 않은 항목은 UNKNOWN으로 유지한다.
