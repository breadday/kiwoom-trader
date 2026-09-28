# 자동 개발 STEP 08A — 공식 Kiwoom 일봉 API 계약 조사 계획

## 상태

- 기준일: 2026-09-28
- 대상 API: `ka10081` 주식일봉차트조회요청
- 범위: 공식 명세 조사와 현재 구현의 PASS/UNKNOWN/FAIL 판정
- 안전 경계: 계좌·주문 API와 인증정보를 호출하거나 저장하지 않는다.

## 조사 출처

1. [키움 REST API 공식 가이드](https://openapi.kiwoom.com/guide/apiguide)
2. [키움증권 공식 REST API 클라이언트의 API 명세 JSON](https://raw.githubusercontent.com/Kiwoom-Securities/Kiwoom-REST-API/main/kiwoom/_data/kiwoom_api_spec.json)
3. [키움증권 공식 REST API 클라이언트 저장소](https://github.com/Kiwoom-Securities/Kiwoom-REST-API)

## 조사 항목

- `POST` URL과 운영/모의투자 도메인
- 인증·TR·연속조회 요청/응답 헤더
- `stk_cd`, `base_dt`, `upd_stkpc_tp` 요청 필드
- 일봉 row 필드와 단위·문자열 형식
- 수정주가 적용 시 `base_dt` 제약
- 페이지 크기, rate limit, HTTP/API 오류 및 실제 응답 관찰 여부
- 거래일 누락, 가격 부호, 응답 정렬의 미확인 범위

## 완료 조건

1. 공식 문서 근거가 있는 항목과 현재 코드의 일치 여부를 표로 기록한다.
2. 공식 근거가 없는 동작은 `UNKNOWN`으로 남기고 구현하지 않는다.
3. fixture 기반 회귀 테스트가 필요한 항목을 STEP 08B 입력으로 명시한다.
4. 조사 결과를 커밋 가능한 Markdown 문서로 남긴다.
