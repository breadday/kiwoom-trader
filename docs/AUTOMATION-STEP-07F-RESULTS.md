# 자동 개발 STEP 07F — 결과 / 재개 지점

## 상태 헤더
| 항목 | 값 |
|---|---|
| 브랜치 | `feat/kiwoom-rescue-demo-data-sanitization-stage-07f` |
| 기준 SHA | rewritten STEP 07E `8219afc718936e56c1a8ba5adad998f33f848248` |
| 상태 | STEP 07F 코드/테스트 독립 리뷰 통과, 50개 전체 및 7개 집중 테스트 통과. STEP 07F source commit `7924a48f2d9b2bf1506f51a383f203382a331d8f`에 STEP 08 handoff를 로컬 문서 commit으로 추가하고 rewritten `main`에 fast-forward 통합했다. Gate 0 문서 리뷰(`deleg_5cbccf45`) passed=true |
| 원격 상태 | GitHub에는 마지막 확인 기준 이전 6개 branch SHA와 무태그 상태가 남아 있다. 원격 write는 미실행. 사용자 실행 방식은 exact HEAD/SHA에 고정된 bundle+PowerShell script이며, Windows PowerShell에서의 실제 실행은 검증되지 않았다 |
| 계좌/주문 영향 | 없음 — offline synthetic demo; auth/API/order path 없음 |

## 작업 요약
- `kiwoom_rescue_bot.py`를 합성 샘플만 사용하는 오프라인 데모로 바꾸고, `api/sample_portfolio.py` 및 privacy 회귀 테스트를 추가했다.
- 사용자 명시 승인에 따라 fresh mirror에서 6개 branch의 과거 `kiwoom_rescue_bot.py` 경로를 이력에서 제거했다. old/new refs와 제한은 `AUTOMATION-GIT-HISTORY-REWRITE.md`에 기록했다.
- 원래 Windows checkout은 수정하지 않았다. 새 branch 작업은 rewritten STEP 07E (`8219afc...`)에서 분리했다.

## 검증 증거
- 전체 unittest: 50개 통과.
- deterministic-output regression: randomized `PYTHONHASHSEED`를 가진 두 subprocess 출력 일치; 고정 synthetic fixture의 factor 순위와 score 스냅샷도 검증.
- offline regression check: 신뢰된 checked-in demo source를 대상으로 선택된 Python DNS/socket/HTTP/urllib/requests/urllib3 및 process APIs의 monkeypatch guard와 broker auth/API import monitor를 사용. 이것은 security sandbox가 아니며 native code를 격리하지 않는다. 손실률 30% 이상 (수익률 <= -30%)인 가상 포지션은 정확히 -30% 경계를 포함해 분할 매도 대상임을 회귀검사한다. 전략 코드 import는 NumPy/Pandas뿐임을 AST로 검사.
- synthetic history의 첫/마지막 종가는 포트폴리오 avg/current와 일치; 5주 eligible position이 3주에 2/2/1주로 전량 분할 출력됨.
- 오프라인 데모 smoke test: exit 0, 합성 샘플만 출력.
- compileall 및 staged diff-check: PASS.
- filtered mirror: 6개 rewritten branch 모두 `kiwoom_rescue_bot.py` path 없음; 기존 main/07 및 07E tip은 mirror object database에서 `git cat-file -e` exit 128. 이는 외부 clone/server objects의 물리 삭제를 뜻하지 않는다.
- 상세 실행 명령과 안전 경계: `AUTOMATION-STEP-07F-TEST.md`.

## 다음 단계
1. STEP 07F code review(`deleg_7a4e5951`, `deleg_afd05a11`)와 Gate 0 문서 리뷰(`deleg_5cbccf45`)는 모두 `passed=true`이며, 차단 지적을 수정했다.
2. 검증: 전체 50개 / STEP 07F 7개 테스트, 오프라인 smoke, compileall, diff-check 통과.
3. STEP 08 handoff 문서는 rewritten `main`에 fast-forward 통합됐다. 이후 docs-only 상태 기록도 최종 artifact 생성 전에 commit하고, bundle/script를 정확한 local HEAD에 고정한다.
4. GitHub는 확인 당시 기존 6개 branch SHA와 무태그 상태였으며, 원격 write는 미실행이다. 사용자 측에서는 번들 SHA와 script 내 pin이 일치하는 한 쌍만 사용한다.
5. Windows PowerShell 실행 검증은 Linux 환경에서 불가능하다. 사용자 실행 후 성공을 전제하지 말고 `git ls-remote`로 일곱 refs의 실제 SHA를 대조해야 한다.

### 문서 독립 리뷰 보완
- 1차 STEP 08 handoff review는 승인 근거의 verbatim 부재와 “paper/read-only” 범위의 모호성을 blocker로 지적했다.
- 이력 재작성/force-push 승인과 현재 push/merge 요청을 history 문서에 verbatim 기록하고, STEP 08E를 market-data read-only로 한정했다.
- Gate 0를 정확한 7개 branch ref set, old-SHA map, expected-no-tags snapshot, `main`/STEP 07F 동일 handoff SHA, sanitized file introduction 및 지정 privacy tests로 fail-closed 확인하도록 구체화했다.
- 2차 독립 리뷰는 pre/post-push ref snapshot 구분과 file-path 단일 도입 커밋 판정이 불명확하다고 차단했다.
- 이를 보완해 pre-push 6-ref old-SHA + STEP 07F 부재, post-push 정확한 7-ref SHA readback을 분리했다.
- 3차 독립 리뷰는 `git log --all` 범위가 과도하고 “단일 commit SHA”가 path addition인지 모호하다고 차단했다.
- Gate 0의 이력 확인을 final main/07F SHA로 각각 한정하고 `git log --diff-filter=A`로 path를 추가한 commit을 검증하며, 두 결과 일치와 parent/tree 존재 검증을 명시했다. 필터링된 5개 branch의 경로 부재는 정확한 awk path match로 확인하도록 했다.
- 4차 리뷰는 parent 없는 root commit인 경우 cat-file 실패가 path 부재를 증명하지 못한다고 지적했다.
- parent SHA를 먼저 `git rev-parse <intro-sha>^`로 확인하고, 이후 parent path의 비존재와 commit tree path의 존재를 분리된 exit 조건으로 검증하도록 보완했다. 원격 readback도 ref→SHA 쌍을 대조하도록 명시했다.
- 위 보완 이후 문서 diff는 재독립 검토 대기 중이다. 통과 전에는 commit/push하지 않는다.

## 중요 제한
원격은 아직 기존 history를 보유한다. 로컬 필터링만으로 원격 데이터가 삭제된 것은 아니다. Force-push가 완료되어도 다른 clone/fork/backup, GitHub cache 및 비광고 server object의 완전 삭제는 보장하지 않는다. 이를 위한 서버측 정리는 GitHub 지원이 필요할 수 있다. 실제 Kiwoom 연결이나 실주문은 검증하지 않았다.
