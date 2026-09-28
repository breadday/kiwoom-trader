# 자동 개발 STEP 08A — 공식 Kiwoom 일봉 API 계약 조사 검증

## 검증 방식

STEP 08A는 코드 변경보다 공식 계약 대조가 먼저인 단계다. 따라서 인증정보나 실 API를 사용하지 않고, 공식 명세 JSON과 현재 checked-in 구현을 정적으로 비교한다.

## 조사 체크리스트

| 항목 | 기대 근거 | 판정 기준 |
|---|---|---|
| Method/URL | 공식 `ka10081` 명세 | `POST /api/dostk/chart`와 일치해야 PASS |
| 요청 헤더 | 공식 `request.header` | `api-id`, `authorization`, `cont-yn`, `next-key` 처리 확인 |
| 요청 Body | 공식 `request.body` | 세 필드명과 수정주가 값 `0/1` 확인 |
| 응답 Header | 공식 `response.header` | `cont-yn`, `next-key` 재사용 확인 |
| 응답 rows | 공식 `stk_dt_pole_chart_qry` | LIST와 일봉 필드 매핑 확인 |
| 가격/수량 단위 | 공식 row descriptions | 원화 가격·1주 거래량 보존 확인 |
| 수정주가 기준일 | 공식 `upd_stkpc_tp` 설명 | 권리발생일 이후 기준일 요구를 문서화 |
| 페이지 크기/rate limit | 공식 명세에서 확인 필요 | 근거가 없으면 UNKNOWN 유지 |
| 실응답/휴장일/정렬 | 승인된 read-only 관찰 필요 | fixture만으로 PASS 주장 금지 |

## STEP 08B로 넘기는 RED 항목

- 빈 응답과 rows 필드 누락/null
- 단일 페이지와 복수 페이지의 중복 날짜
- `cont-yn=Y`인데 `next-key`가 없는 응답
- 반복 `next-key`, `max_pages` 초과
- API 오류 코드와 HTTP 오류
- 가격 부호·콤마·공백 및 OHLC 불일치
- 휴장일 누락과 응답 정렬

## 안전 검증

- 계좌, 잔고, 주문, 토큰 발급 요청을 하지 않는다.
- 실제 credential을 fixture나 문서에 기록하지 않는다.
- 공식 명세에 없는 값을 추정해 테스트 기대값으로 고정하지 않는다.
