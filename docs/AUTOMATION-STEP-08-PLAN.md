# Kiwoom Trader — STEP 08+ 다음 개발 계획 및 AI 핸드오프

## 상태 / 재개 지점

- 기준일: 2026-09-27 (현재 handoff 기록일이며, 이후 검증을 수행하는 AI는 새 검증일을 별도 기록하고 이 날짜를 최신 검증 시점으로 오인하지 않는다.)
- 작업 브랜치: `feat/kiwoom-rescue-demo-data-sanitization-stage-07f`
- STEP 07A–07E: 이전 단계 기록상 구현·테스트·원격 반영 완료.
- STEP 07F: 민감한 과거 파일 경로를 제거한 filtered history 위에 합성 오프라인 데모를 추가했다. 코드/테스트/문서 독립 검토와 50개 테스트가 통과한 상태다.
- 로컬 rewritten `main`과 STEP 07F 브랜치는 현재 handoff tip으로 fast-forward 통합돼 있다. GitHub 원격은 마지막 조회에서 이전 6개 branch SHA와 무태그 상태였고, 원격 write는 아직 하지 않았다. Windows PowerShell bundle/script를 사용자가 직접 실행하는 방식으로 준비 중이며, 도구에서 로그인 코드를 재요청하거나 사용자에게 credential을 채팅으로 요청하지 않는다.
- 사용자는 GitHub 인증을 이 세션에서 반복하는 대신 bundle과 PowerShell script를 받아 Windows에서 직접 실행하길 원한다. 기록된 explicit history-rewrite 승인만으로 대상 ref/SHA를 추정하지 않는다. 실행 직전 old-ref/tag snapshot이 정확히 일치할 때만 seven-ref atomic `--force-with-lease`를 사용하고, 보호 규칙을 우회하지 않으며, 실행 후 원격 ref→SHA를 다시 읽어 확인한다.
- 원본 Windows checkout은 보존한다. 새 AI는 GitHub에서 정화된 `main`을 fresh clone한 뒤 원격 SHA와 이 문서를 확인하고 시작해야 한다.

## 완료된 범위와 고정 계약

1. `api/kiwoom_api.py`의 `get_daily_chart`는 ka10081 일봉 조회를 위한 read-only 경로다. 이 메서드는 실계좌 여부와 무관하게 동작하도록 의도됐으나, 실제 Kiwoom 응답 및 운영 호환성은 아직 검증되지 않았다.
2. RESCUE 백테스트는 첫 종가 진입, 종가 기준 청산 임계치 평가, 즉시청산 우선, 부분청산 한 번, 비용 미포함 규칙을 따른다. 세부값은 `docs/AUTOMATION-STEP-07B-*.md`에서 확인한다.
3. FACTOR 백테스트는 현재 고정 8종목, 확정 가중치/품질 제외 기준, 월요일 종가 신호와 다음 거래일 시가 체결 규칙을 따른다. 새 유니버스나 기준 변경은 별도 승인과 테스트가 필요하다.
4. `base_dt` 생략은 전일 KST 달력 날짜, 명시값은 그대로 사용한다. 실 API가 실제 거래일/응답 정렬에 어떻게 반응하는지는 별도 검증 대상이다.
5. STEP 07F 데이터는 합성 오프라인 샘플뿐이다. `offline_demo_runner.py`는 신뢰된 저장소 코드에 대한 선택적 Python-level 회귀 가드이며 OS/native sandbox가 아니다.
6. 실계좌 접근, 주문 제출, 신규 매수, credential 출력/저장은 금지한다. fixture 통과를 실 API 호환성이나 실매매 준비 완료로 표현하지 않는다.

## 다음 작업 순서와 게이트

### Gate 0 — 저장소/이력 인수 확인

- **Pre-push old-snapshot check:** enumerate all advertised heads with `git ls-remote --heads "$REMOTE"` and tags with `git ls-remote --tags --refs "$REMOTE"`. Compare exact ref→SHA pairs (not just names) against the six “Before rewrite” rows (`main`, STEP 07, 07B, 07C, 07D, 07E); STEP 07F must be absent. Tags must be empty, matching the 2026-09-27 observed snapshot. Any missing/extra/changed head or any tag is a hard stop.
- **Post-push readback:** repeat both commands after push and compare every exact ref→SHA pair against the seven expected pairs: `refs/heads/main`, `refs/heads/feat/kiwoom-daily-backtest-stage-07`, `refs/heads/feat/kiwoom-daily-backtest-stage-07b`, `refs/heads/feat/kiwoom-daily-backtest-stage-07c`, `refs/heads/feat/kiwoom-daily-chart-contract-stage-07d`, `refs/heads/feat/kiwoom-auth-token-log-safety-stage-07e`, and `refs/heads/feat/kiwoom-rescue-demo-data-sanitization-stage-07f`. `main` and STEP 07F must equal the reviewed final handoff HEAD captured immediately before push; the other five match the fixed filtered SHA values below. Tags remain empty. Missing/extra refs or mismatched SHA means publication is unverified and must be reported as failure.
- **Reachable-history and file check:** for each of the five filtered STEP 07–07E branch SHAs, run `git rev-list --objects <sha> | awk '$2 == "kiwoom_rescue_bot.py" {found=1} END {exit found}'`; it must return success (no exact path match). This checks the path across all commits/trees reachable from that SHA. For the intended final refs only—`FINAL_MAIN_SHA` and `FINAL_07F_SHA` captured from the verified post-push snapshot—run `git log --diff-filter=A --format=%H <ref-sha> -- kiwoom_rescue_bot.py` separately for each ref. Each command must output exactly one SHA and both outputs must be identical; this is the sole commit that adds the path, not a claim that the path was never modified later. Confirm the reported intro SHA is the reviewed STEP 07F source commit. Verify it is not a root commit (`git rev-parse <intro-sha>^` must succeed); then verify its parent lacks the path (`git cat-file -e <intro-sha>^:kiwoom_rescue_bot.py` must return nonzero) and its commit tree contains it (`git cat-file -e <intro-sha>:kiwoom_rescue_bot.py` must return zero). Review `git show <intro-sha>:kiwoom_rescue_bot.py` for synthetic `DEMO-*` samples only, no broker auth/API/order path, and no copied account-specific data; check the final file at both final refs too. Run `test_rescue_demo_script_uses_only_explicit_sample_portfolio_data`, `test_sample_portfolio_fixture_is_clearly_synthetic_and_well_formed`, `test_trusted_demo_passes_selected_python_network_guards_without_broker_imports`, and static import/content review. Any failure blocks release. This does not claim physical deletion from other clones/forks/caches.
- The seven-ref publication is limited to this exact old/new mapping. Any target/ref drift, added ref/tag, or branch-protection rejection requires stopping, not broadening or bypassing the push.
- `docs/AUTOMATION-GIT-HISTORY-REWRITE.md`의 실제 push/readback 기록이 최신인지 확인한다.
- 이 Gate가 실패하면 기능 개발을 시작하지 말고 원격 정리/인수 문제를 먼저 해결한다.

### STEP 08A — 공식 Kiwoom 일봉 API 계약 조사

- 공식 Kiwoom REST 문서의 ka10081 요청 URL, 헤더, request fields, response row fields, continuation 규칙, rate limit 및 오류 응답을 확인하고 출처/확인일을 문서화한다.
- 현재 코드의 가정(`cont-yn`, `next-key`, 날짜/가격/거래량 필드 및 부호/문자열 형식)을 항목별로 PASS/UNKNOWN/FAIL 표로 기록한다.
- 문서 근거가 불충분한 동작은 추정하지 말고 fixture/API call 전에 확인 질문 또는 fail-closed 테스트로 남긴다.
- live 계좌/주문 API는 호출하지 않는다. 시장 데이터 read-only 권한만 사용한다.

### STEP 08B — fixture 기반 응답 정규화 및 페이지네이션 회귀 검증

- 공인 문서 예제 또는 민감정보를 제거한 승인된 market-data fixture만 사용한다. 각 fixture에는 출처 URL/문서 버전 또는 관측일, schema version, sanitization/사용 승인자(또는 승인 근거)를 기록하고 credential/account fields가 없는지 확인한다.
- 실제 read-only market-data 응답을 보존하려면 별도 승인 후 민감정보를 제거하고, 저장 허용 범위/보존 위치/fixture provenance를 문서화한다. 계좌·인증·주문 응답은 fixture로 저장하지 않는다.
- 빈 응답, 단일/복수 페이지, 반복 next-key, continuation 누락, max_pages 소진, API 오류 코드, HTTP 오류, 누락/null/잘못된 row, 중복 날짜, 정렬, 가격 부호·콤마 형식, OHLC 불일치, 거래량 경계를 각각 테스트한다.
- 우선 테스트를 작성하고 기대된 RED를 확인한 뒤 최소 구현으로 GREEN 한다.
- 거래일 누락/휴장일, 수정주가, 가격 부호 해석은 공식 계약 근거 없이는 변경하지 않는다.

### STEP 08C — read-only provider와 백테스트 경계 통합

- `StrategyOptimizer`의 provider 주입 경로와 `KiwoomAPI.get_daily_chart`를 fixture 기반으로 연결해 호출 횟수, limit, 날짜 정렬 및 fail-closed 오류 전달을 검증한다.
- 기존 STEP 07B/07C 전략 규칙·가중치·유니버스를 무단 변경하지 않는다.
- FACTOR 조회 필요량은 현재 코드 기준 252-bar lookback + evaluation bars다. 현재 provider default `max_pages=10`이 이 필요량을 보장한다고 가정하지 않는다. 공식 page size/rate limit 확인 뒤 충분한 커버리지를 판정하고, cap 안에 요구 bars를 못 받으면 부분/부정확 백테스트 대신 명시적 실패를 반환한다. cap을 자동으로 늘리거나 rate limit을 우회하지 않는다.
- 빈/불충분/날짜 불일치/종목 누락 데이터는 점수나 추천을 임의 생성하지 말고 명확히 실패시킨다.

### STEP 08D — 백테스트 품질 및 결과 보고

- 조정주가/비용/슬리피지/체결 가정 및 look-ahead 여부를 기존 계약과 공식 데이터 정의에 맞춰 명시한다.
- 합성 fixture와 공식 예제 fixture에서 손익, 매도 우선순위, 부분청산 수량, 잔량, 평가 시점의 경계를 검증한다.
- 성과지표(수익률·drawdown·Sharpe·승률)의 기간/연율화/거래 정의를 `docs/`에 명시한다. 재정의가 필요하면 구현 전에 사용자 승인을 받는다.
- 백테스트 결과는 투자수익 보장이나 매수 추천으로 표현하지 않는다.

### STEP 08E — read-only market-data 검증 및 운영 가이드

- 이 단계는 market-data read-only 검증만 포함하며, 계좌 잔고·paper/live 주문·주문 시뮬레이션을 실행하지 않는다.
- 별도의 paper-trading 테스트가 제안되더라도 현재 범위 밖이다. 구체적인 account/order 권한, 안전 제한 및 환경을 먼저 문서화하고 사용자에게 별도로 명시 승인을 받기 전에는 실행하지 않는다.
- `accounts.yaml`의 실전 전환은 별도 사용자 명시 승인 전 구현·활성화하지 않는다. 기존 T8 배포/전환 가이드는 별도 단계로 관리한다.

## 미결/승인 필요 항목

- 실제 Kiwoom REST 응답과 페이지네이션의 관측 증거.
- 수정주가 기준, corporate action 반영, 거래일 캘린더/휴장일 및 응답 정렬.
- 현재 테스트 fixture를 넘어선 실 API 검증을 어떤 승인된 read-only 환경에서 할지.
- 백테스트 비용·슬리피지·조정주가 성과 해석을 바꿀지 여부.
- ORB/BULL_FLAG 및 portfolio recommendation 계약은 미정의이므로 현 단계에서 fail-closed를 유지한다.

## 각 단계 완료 조건

- `docs/AUTOMATION-STEP-NN-PLAN.md`, `docs/AUTOMATION-STEP-NN-TEST.md`, `docs/AUTOMATION-STEP-NN-RESULTS.md` 형태로 단계별 계획·검증·결과를 남긴다.
- 각 behavior slice는 RED→GREEN 증거를 남기고, 전체 회귀·compile·diff 검사를 최종 문서 변경 후 재실행한다.
- 민감값 정적 검사 및 안전 경계 확인, 독립 코드/문서 리뷰 후 단계별 commit.
- 사용자가 push를 원하면 branch/commit/원격 old SHA를 확인한 뒤 push하고 `git ls-remote`로 정확한 원격 SHA를 읽어 검증한다.
- 리뷰/CI/원격 쓰기 실패 시 성공으로 표현하지 말고 blocker와 로컬 상태를 명확히 남긴다.

## 새 AI 시작 체크리스트

1. 이 문서와 `docs/03-tasks.md`, `docs/AUTOMATION-GIT-HISTORY-REWRITE.md`, STEP 07A–07F 결과 문서를 읽는다.
2. `git status --short --branch`, `git remote -v`, `git log --oneline --decorate -12`, `git ls-remote --heads origin`을 실행한다.
3. 원격 `main`에 STEP 07F와 본 문서가 실제 반영됐는지 SHA로 확인한다. 반영되지 않았다면 새 AI는 오래된 원본 branch에서 바로 개발하지 않는다.
4. 구현 전에 STEP 08A 공식 Kiwoom 계약 조사와 근거 문서를 먼저 완료하고, UNKNOWN 동작을 추측하지 않는다.
5. 실주문/실계좌/계좌정보 접근은 별도 명시 승인 없이는 하지 않는다.
