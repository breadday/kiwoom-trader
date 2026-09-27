# 자동 개발 STEP 07F — 구형 RESCUE 데모 합성화 / 이력 정화 계획

## 상태 헤더
| 항목 | 값 |
|---|---|
| 확인일 | 2026-09-27 |
| 브랜치 | `feat/kiwoom-rescue-demo-data-sanitization-stage-07f` |
| 기준 커밋 | 재작성된 STEP 07E SHA `8219afc718936e56c1a8ba5adad998f33f848248` |
| 범위 | 구형 데모를 오프라인 합성 샘플 전용으로 변경하고, 과거 이력에서 민감 데이터가 든 파일 경로 제거 |
| 원격 상태 | GitHub에는 아직 정화 전 6개 branch SHA가 광고됨. Docker HTTPS dry-run은 username prompt 불가로 실패; 기존 bundle/script는 handoff 문서와 최종 main integration 전 산출물이므로 재생성 필요 |

## 배경 / 승인
- 구형 `kiwoom_rescue_bot.py`의 과거 버전에 계좌처럼 보이는 하드코딩 데이터가 있었다. 숫자와 보유내역은 어떠한 문서·테스트·채팅에도 복사하지 않는다.
- 사용자는 먼저 현재 파일을 합성 샘플로 바꾸는 것과 이력 보존을 선택했으나, 독립 리뷰가 이전 이력 및 원격 `main`의 잔여 노출을 차단 사유로 제시했다.
- 사용자는 이후 결정을 변경해 과거 자료 제거를 위한 Git 이력 재작성과 force-push를 명시 승인했다.
- 로컬 fresh mirror에서 `git-filter-repo --path kiwoom_rescue_bot.py --invert-paths`를 실행해 기존 6개 branch의 과거 트리에서 해당 경로를 제거했다. SHA 매핑/제한은 `docs/AUTOMATION-GIT-HISTORY-REWRITE.md`에 기록한다.

## 구현 계약
1. 현재 데모와 별도 fixture에는 합성 샘플만 둔다.
2. 예시는 `DEMO-*` 식별자와 `가상 샘플` 이름을 사용한다.
3. checked-in demo source는 합성 fixture만 사용하고 broker/API/order 경로를 import하거나 호출하지 않는다. `offline_demo_runner`는 신뢰된 repository source에 대한 선택된 Python-level API regression guard일 뿐 OS sandbox가 아니며, native extension이나 arbitrary untrusted code를 격리하지 않는다. Broker auth/API import와 선택된 network/process Python entrypoints를 감시한다.
4. 기존 전략 계산/콘솔 데모를 유지하되 실제 운용처럼 오인시키는 문구를 쓰지 않는다. 분할 매도 예시는 전량을 3주로 균등 배분하며 실제 주문이 아니라 계획만 출력한다.
5. 필터된 이력에서 민감 파일은 과거 커밋에 존재하지 않는다. 새 파일은 안전한 STEP 07F branch에서만 다시 추가한다.
6. 합성 가격열은 SHA-256 기반 안정 seed를 사용해 프로세스 간 재현성을 보장한다.
7. Push-script acceptance criteria: before any remote write, verify the advertised old refs against the snapshot and require a single atomic push with per-ref `--force-with-lease`; use an empty expected lease for the new STEP 07F branch. Never use bare `--force`, `--mirror`, or branch-protection bypass.

## 변경 파일
- `kiwoom_rescue_bot.py` — 합성 샘플 전용 오프라인 데모.
- `api/sample_portfolio.py` — 가상 포트폴리오 fixture.
- `api/demo_portfolio.py` — 매도 계획 수량 균등 분할 helper.
- `tests/test_demo_portfolio_privacy.py` — 합성 라벨·오프라인 경계·손익 라벨·분할 배분 검사.
- `tests/offline_demo_runner.py` — checked-in trusted demo source에 선택된 Python network/process API regression guard를 적용하며 OS/native sandbox가 아님을 명시한다.
- `docs/AUTOMATION-GIT-HISTORY-REWRITE.md` — old/new refs, 검증, 복제본/캐시 제한 기록.
- `docs/03-tasks.md`, STEP 07E/07F 문서 — 재작성 후 기준 SHA 및 재개 정보.

## 완료 조건
- 과거 tree에서 `kiwoom_rescue_bot.py` 경로가 각 rewritten branch에 없고, 기존 main/07 tip 및 07E tip이 filtered mirror object database에서 접근 불가임을 확인. 이는 다른 clone/server storage 제거를 뜻하지 않는다.
- 안전 데모 branch의 코드/테스트/문서에 기존 민감값이 재등장하지 않음.
- 전체 테스트, 데모 smoke test, compileall, diff-check 통과.
- 독립 리뷰 통과 후 새 branch commit 및 검증된 bundle/PowerShell push 스크립트 준비.
- 사용자가 push한 뒤 모든 remote branch SHA를 readback으로 확인.

## 안전 경계 및 한계
Force-push는 원격 branch refs를 재작성할 뿐 기존 clone/fork/backup, GitHub cache 또는 비광고 server-side object를 완전 삭제한다고 보장하지 않는다. 현재 원격은 변경되지 않았다. 향후 원격 변경은 검토된 bundle과 독립 검증된 atomic script가 전달된 뒤 사용자가 실행할 때만 발생한다. 기존 Windows checkout은 수정하지 않는다. 실계좌·credential·market-data·주문 검증은 수행하지 않는다.
