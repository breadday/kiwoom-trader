# 자동 개발 STEP 07D — 키움 일봉 기준일 계약 정합성 결과 / 재개 지점

## 상태 헤더
| 항목 | 값 |
|---|---|
| 확인일 | 2026-09-26 |
| 작업 브랜치 | `feat/kiwoom-daily-chart-contract-stage-07d` |
| 실행 범위 | 기준일 기본값/검증 fixture 수정 |
| 실전 영향 | 실제 broker/계좌/주문/배포 없음 |

## 진행 상태
- 구현 및 테스트 완료, 독립 리뷰 통과(`deleg_3881e7b6`, `passed=true`; blocker 없음).
- 공식 명세 조사: 완료. 실제 server-side compatibility는 미검증.
- 포커스 계약 테스트: 2개 RED 후 GREEN.
- 전체 테스트 42개 통과, compileall 및 diff-check 통과.
- 커밋/push: 독립 리뷰 후 진행.

## 구현 내용
- `get_daily_chart`에 기준일 생략 시 전일 KST 날짜를 보내도록 변경.
- 명시 기준일은 실제 유효 날짜 `YYYYMMDD`로 검증하고, 문서화되지 않은 `00000000` sentinel을 거부.
- 조정주가의 역사 데이터 일관성을 위해 `base_dt`가 관련 권리발생일 이후여야 한다는 호출 주의사항 추가.
- 시간대 계산에는 외부 패키지 대신 UTC+09:00 고정 offset을 사용.

## 관찰한 RED → GREEN
- 포커스 명령:
  `PYTHONPATH=/tmp/kiwoom-chardet:/tmp/kiwoom-trader-deps python3 -W error -m unittest tests.test_kiwoom_daily_chart.KiwoomDailyChartTests.test_omitted_base_date_uses_previous_kst_calendar_day tests.test_kiwoom_daily_chart.KiwoomDailyChartTests.test_rejects_undocumented_zero_base_date_before_network_call -v`
- RED: 기존 코드는 생략 시 `00000000`을 보냈고, 명시 `00000000`을 거부하지 않았다(2 tests failed).
- GREEN: 같은 두 테스트 통과.
- 기존 명시 날짜 요청 테스트도 회귀 검증으로 통과.

## 전체 자동검사 결과
```text
PYTHONPATH=/tmp/kiwoom-chardet:/tmp/kiwoom-trader-deps python3 -W error -m unittest discover -v
Ran 42 tests — OK
(16 daily-chart + 9 RESCUE + 17 FACTOR)

python3 -m compileall -q api strategies tests
PASS

git -c core.whitespace=cr-at-eol diff --check
PASS
```

## 독립 리뷰 / 완료 게이트
- 구현·테스트·문서 exact staged diff 독립 리뷰: `deleg_3881e7b6`, `passed=true`; security_concerns 및 logic_errors 없음.
- 제안은 live Kiwoom 호환성/휴장일/조정가격 표현을 미검증으로 계속 명시하는 것뿐이며, 문서 제한사항에 반영되어 있다.
- STEP 07D 구현/테스트/문서 커밋: `b0c2a24f45deb0b38dcf301a026b82cfd15da70d` (로컬).
- Push 차단: Docker HTTPS 인증 부재로 `fatal: could not read Username for 'https://github.com': No such device or address` 반환. 원격 SHA 미확인.
- 사용자가 Windows에서 push 후 원격 SHA를 확인하면 이 결과 문서와 `docs/03-tasks.md`에 기록한다.

## 알려진 제한
- fixture 통과는 실제 Kiwoom 실/모의 서버 호환성 증거가 아니다.
- 전일이 휴일·주말일 때 서버가 반환하는 실제 날짜 범위 및 `upd_stkpc_tp=1` 가격부호 표현은 조회-only 자격증명/승인 환경에서 별도 검증할 때까지 미확인.
- 주문·계좌·실전 동작은 이 단계의 범위 밖이다.

## Sources
[1] https://openapi.kiwoom.com/m/guide/apiguide/07/ka10081 — 키움 REST API 공식 일봉 차트 명세.
