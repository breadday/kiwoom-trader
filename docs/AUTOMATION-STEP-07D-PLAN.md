# 자동 개발 STEP 07D — 키움 일봉 기준일 계약 정합성 계획

## 상태 헤더
| 항목 | 값 |
|---|---|
| 확인일 | 2026-09-26 |
| 작업 브랜치 | `feat/kiwoom-daily-chart-contract-stage-07d` |
| 실행 범위 | `ka10081` 조회 기준일을 공식 명세의 `YYYYMMDD` 계약과 일치 |
| 실전 영향 | fixture만 사용; 키움 서버·계좌·주문·배포 호출 없음 |

## 구현 범위
- 기준일을 생략하면 KST 기준 전일의 달력 날짜를 요청한다. 당일 미완료 일봉을 포함할 위험을 피하기 위한 보수적인 기본값이다.
- 명시한 `base_dt`는 유효한 `YYYYMMDD`로 검증하고 그대로 보낸다.
- 공식 계약에 없는 `00000000`을 거부한다.
- 조정주가 조회의 기준일은 해당 권리발생일 이후여야 한다는 호출자 책임을 코드 문서와 결과 기록에 남긴다.

## 제외 범위 / 안전 경계
- 실/모의 키움 API, 인증, 계좌, 주문 호출을 하지 않는다. 실제 broker 호환성을 통과로 표시하지 않는다.
- 전략 백테스트 규칙, ORB/BULL_FLAG, 포트폴리오 추천 계약을 바꾸지 않는다.
- 휴장일/거래일 달력 조회는 이 단계에서 추가하지 않는다. 전일이 비거래일이면 서버가 그 기준일 이전의 이용 가능한 일봉을 반환하는지 실제 서버로 확인하지 않는다.

## 공식 계약 근거
키움 공식 `ka10081` 가이드는 `POST /api/dostk/chart`, 운영 도메인 `https://api.kiwoom.com`, 필수 `base_dt` 형식 `YYYYMMDD`, 필수 `upd_stkpc_tp` 값 `0 or 1`을 기재한다. 수정주가 사용 시에는 권리발생일 이후 날짜를 `base_dt`로 지정하도록 안내한다.[1]

> “base_dt 기준일자 String Y 8 YYYYMMDD”
>
> “수정주가 적용을 원하시는 경우, 권리발생일 이후 일자를 base_dt에 넣어 조회 또는 연속조회해주시기 바랍니다.”

## 변경 파일
- `api/kiwoom_api.py` — 기준일 선택 및 입력 검증.
- `tests/test_kiwoom_daily_chart.py` — KST 날짜 기본값 및 미지원 sentinel 거부 테스트.
- `docs/AUTOMATION-STEP-07D-PLAN.md` — 계약·범위.
- `docs/AUTOMATION-STEP-07D-TEST.md` — RED/GREEN 및 검증 계획.
- `docs/AUTOMATION-STEP-07D-RESULTS.md` — 실제 결과와 재개 상태.
- `docs/03-tasks.md` — T7 현재 단계/잔여 범위.

## 완료 게이트
1. 새 계약 테스트가 기존 코드에서 의도한 이유로 RED가 된다.
2. 최소 수정 뒤 포커스 및 전체 테스트 GREEN이다.
3. Python compileall, whitespace/security scan 통과한다.
4. 독립 리뷰 `passed=true`; 최종 문서에 실제 검증 결과 기록.
5. 문서 포함 STEP 07D 커밋·푸시 후 원격 SHA를 로컬 HEAD와 대조한다.

## Sources
[1] https://openapi.kiwoom.com/m/guide/apiguide/07/ka10081 — 키움 REST API 공식 일봉 차트 명세.
