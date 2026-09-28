# 자동 개발 STEP 08E — read-only market-data 검증 및 운영 가이드 계획

## 목표

`KiwoomAPI.get_daily_chart()`를 실제 Kiwoom market-data endpoint에 연결해
응답·페이지네이션·운영 경계를 확인한다. 이 단계는 일봉 시장데이터 조회만
대상으로 하며 계좌·잔고·주문·paper/live trading API는 호출하지 않는다.

## 선행 조건

1. 사용자가 명시적으로 read-only Kiwoom API 호출과 네트워크 사용을 승인한다.
2. 승인된 실행 환경이 `app_key`·`app_secret`를 안전한 비대화형 입력으로 제공한다.
3. credential은 저장소 파일, 로그, 채팅, fixture에 기록하지 않는다.
4. 호출 대상 종목·기준일·보존 범위와 rate limit을 승인된 운영 기준으로 확정한다.

## 검증 항목

- `POST /api/dostk/chart`, `api-id=ka10081` 및 Bearer 인증
- `cont-yn`·`next-key` 연속조회와 중복/누락 key fail-closed 동작
- 실제 page size, rate limit, HTTP/API 오류 응답
- 응답 날짜 정렬, 휴장일 누락, 거래소 suffix, 가격 부호
- `upd_stkpc_tp=1` 수정주가 응답의 기준일 의미

## 완료 조건

- 승인된 read-only 호출 결과를 민감값 제거 후 검증 보고서에 기록한다.
- 계좌·주문 API 호출이 없음을 실행 로그와 코드 경계로 확인한다.
- 미확인 동작은 추측하지 않고 UNKNOWN 또는 별도 승인 항목으로 남긴다.
