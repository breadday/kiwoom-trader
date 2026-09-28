# 자동 개발 STEP 08A — 공식 Kiwoom 일봉 API 계약 조사 결과

## 상태

- 기준일: 2026-09-28
- 결과: 조사 완료, 코드 변경 없음
- 다음 단계: STEP 08B fixture 기반 응답 정규화·페이지네이션 검증
- 안전 범위: 공식 문서와 로컬 코드의 정적 대조만 수행. 계좌·주문·실 API 호출 없음.

## 공식 계약에서 확인된 사실

| 항목 | 공식 명세 | 현재 구현 판정 |
|---|---|---|
| Method/URL | `POST https://api.kiwoom.com/api/dostk/chart`; 모의 도메인은 `https://mockapi.kiwoom.com` | PASS — `get_daily_chart`는 `POST`와 `/api/dostk/chart` 사용 |
| Content-Type | `application/json;charset=UTF-8` | PASS |
| TR 헤더 | `api-id: ka10081` | PASS |
| 인증 헤더 | `authorization: Bearer ...` | PASS — HTTP 헤더명은 대소문자 비구분이며 auth 값은 Bearer 형식 |
| 연속조회 헤더 | 요청/응답 `cont-yn`, `next-key` | PASS — 다음 요청에 두 값을 전달하고 반복 key를 거부 |
| 요청 종목코드 | `stk_cd`, 거래소별 suffix 예시 포함 | PARTIAL — 필드 전달은 확인됐지만 거래소 suffix 실응답은 미검증 |
| 기준일자 | `base_dt`, 필수, `YYYYMMDD` | PASS — 로컬 형식 검증과 전달이 일치 |
| 수정주가 | `upd_stkpc_tp`, 필수, `0` 또는 `1` | PASS — 현재 요청은 `1`로 고정 |
| 수정주가 기준일 | 권리발생일 이후 기준일로 조회/연속조회해야 과거 수정주가 적용 | DOCUMENTED — runtime 검증은 미완료 |
| 응답 rows | `stk_dt_pole_chart_qry`, LIST, 선택 필드 | PASS — list/null/row 형태를 fail-closed 검증 |
| 일자 | `dt`, `YYYYMMDD` | PASS |
| 가격 | `cur_prc`, `open_pric`, `high_pric`, `low_pric`, 단위 원 | PARTIAL — 현재가를 close로 사용하는 매핑은 공식 예시와 부합하나 실제 응답 의미·부호는 미관찰 |
| 거래량 | `trde_qty`, 단위 1주 | PASS — 정수화 및 음수 거부 |
| 추가 row 필드 | 거래대금 `trde_prica`, 전일대비 `pred_pre`, 기호 `pred_pre_sig`, 회전율 `trde_tern_rt` | UNKNOWN — 백테스트 계약에 필요하지 않아 현재 normalized row에서 보존하지 않음 |

## 근거가 부족해 UNKNOWN으로 유지한 항목

1. 공식 명세 JSON에서 `ka10081`의 페이지당 row 수와 TR별 rate limit을 확인하지 못했다.
2. HTTP 오류, API 오류 코드별 의미와 재시도 가능 여부는 실제 승인된 관찰 또는 별도 공식 오류코드 근거가 필요하다.
3. 휴장일 누락, 응답 정렬, 거래소 suffix, 가격 부호의 실제 일봉 응답 동작은 fixture/실 read-only 응답으로 검증해야 한다.
4. `base_dt` 생략 시 전일 KST 달력일을 선택하는 현재 정책은 애플리케이션 안전정책이며, 공식 API 계약으로 확인된 동작이 아니다.

## 결론

- 현재 요청 골격과 기본 일봉 row 매핑은 공식 `ka10081` 명세와 대체로 일치한다.
- 페이지 크기·rate limit·실응답 동작을 확인하기 전에는 `max_pages=10`이 충분하다고 주장하지 않는다.
- 08A에서는 추측성 코드 수정을 하지 않았다.
- 08B에서 승인된 공식 예제 또는 민감정보를 제거한 market-data fixture로 위 UNKNOWN 항목을 회귀 검증한다.

## 출처

- [키움 REST API 공식 가이드](https://openapi.kiwoom.com/guide/apiguide)
- [공식 API 명세 JSON — `ka10081`](https://raw.githubusercontent.com/Kiwoom-Securities/Kiwoom-REST-API/main/kiwoom/_data/kiwoom_api_spec.json) (2026-09-28 확인)
- [키움증권 공식 REST API 클라이언트](https://github.com/Kiwoom-Securities/Kiwoom-REST-API)
