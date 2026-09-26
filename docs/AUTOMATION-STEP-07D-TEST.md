# 자동 개발 STEP 07D — 테스트 명세 및 실행 기록

## 상태 헤더
| 항목 | 값 |
|---|---|
| 확인일 | 2026-09-26 |
| 작업 브랜치 | `feat/kiwoom-daily-chart-contract-stage-07d` |
| 실행 범위 | `ka10081` 기준일 입력 계약 fixture 검증 |
| 실전 영향 | 네트워크/계좌/주문 호출 없음 |

## 상태
- 신규 기준일 계약 테스트 2개: RED 확인 후 GREEN.
- 전체 테스트: 42개 통과(16 daily-chart + 9 RESCUE + 17 FACTOR).
- `compileall` 및 `git diff --check`: 통과.
- 독립 리뷰: `deleg_3881e7b6` `passed=true`, blocker 없음.
- 구현 커밋 `b0c2a24f45deb0b38dcf301a026b82cfd15da70d` 생성 완료.
- Push 미완료: HTTPS 인증 누락으로 원격 SHA 확인 불가.

## 기준
공식 가이드에서 `base_dt`는 필수 `YYYYMMDD`로 명시되고, 조정주가를 얻으려면 권리발생일 이후 기준일을 넣도록 안내한다.[1] 테스트는 이 입력 계약과 미완료 당일봉 회피 기본값을 검증한다. 실제 서버의 응답·거래일 달력 동작은 검증하지 않는다.

## RED → GREEN 기록
- `test_omitted_base_date_uses_previous_kst_calendar_day`: 기존 기본값 `00000000`이 `20260926` 대신 전송되어 RED. 수정 후 KST 2026-09-27 00:30 fixture에서 전일 `20260926`을 보내 GREEN.
- `test_rejects_undocumented_zero_base_date_before_network_call`: 기존 구현은 `00000000`을 거부하지 않고 HTTP 호출하여 RED. 수정 후 요청 전에 `ValueError`를 발생시키고 호출 횟수 0으로 GREEN.
- 기존 명시 날짜 요청 테스트는 전달한 날짜와 `upd_stkpc_tp="1"`을 유지하는 회귀 검증으로 실행한다.

## 검증 명령
```text
PYTHONPATH=/tmp/kiwoom-chardet:/tmp/kiwoom-trader-deps python3 -W error -m unittest tests.test_kiwoom_daily_chart -v
PYTHONPATH=/tmp/kiwoom-chardet:/tmp/kiwoom-trader-deps python3 -W error -m unittest discover -v
python3 -m compileall -q api strategies tests
git -c core.whitespace=cr-at-eol diff --check
```

## 안전 경계
모든 HTTP 응답은 fake fixture다. `get_daily_chart` 요청의 URL/payload assertion 외 실제 시세망·paper host·실전 host 접근은 없고, 매매 API는 호출하지 않는다.

## Sources
[1] https://openapi.kiwoom.com/m/guide/apiguide/07/ka10081 — 키움 REST API 공식 일봉 차트 명세.
