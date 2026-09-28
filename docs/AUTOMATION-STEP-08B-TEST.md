# 자동 개발 STEP 08B — fixture 기반 응답 정규화·페이지네이션 테스트

## fixture

- 파일: `tests/fixtures/ka10081_official_example.json`
- 출처: 키움증권 공식 REST API 명세 JSON의 `ka10081` 공개 예제
- 관측일: 2026-09-28
- 계좌·credential 포함 여부: 없음

## 테스트 목록

| 구분 | 검증 |
|---|---|
| 공식 예제 정규화 | row 날짜 정렬, 현재가/거래량 매핑 |
| 연속조회 | `cont-yn=Y`인데 `next-key`가 없으면 실패 |
| 반복 방지 | 같은 `next-key`가 재사용되면 실패 |
| 조회 상한 | `max_pages` 안에 limit을 채우지 못하면 실패 |
| HTTP 오류 | `raise_for_status()` 오류를 정상 결과로 변환하지 않음 |
| 숫자 형식 | 콤마·공백·`+` 및 0 거래량 허용 |

기존 `test_kiwoom_daily_chart.py`의 malformed row, 중복 날짜, 음수 가격, 누락/null rows, OHLC 경계 테스트도 함께 유지한다.

## 안전 경계

- 모든 HTTP 요청은 `unittest.mock.patch`로 대체한다.
- 실제 토큰·계좌·주문 API는 호출하지 않는다.
- fixture는 공식 공개 예제에서 필요한 시장 데이터 row만 보존한다.
