# 자동 개발 STEP 07F — 테스트 / 검증 기록

## TDD / 회귀 기록
- 기존 구현에서 privacy assertion이 hard-coded account-state marker 때문에 실패(RED).
- 오프라인 경계를 강화하자 broker auth/API import가 남아 있어 실패(RED), 이를 제거.
- 합성 fixture의 손익이 출력 라벨과 불일치하는 검사가 실패(RED), 샘플 값을 맞춘 뒤 통과.
- 기존 브랜치에서 확인한 RED→GREEN 내역을 유지하고, history-rewritten checkout에서도 전체 검증을 다시 수행했다.
- 독립 리뷰 round 4에서 deterministic subprocess test가 네트워크 차단 없이 데모를 두 번 실행하는 문제가 발견되어 공용 `tests/offline_demo_runner.py`로 in-process/subprocess 양쪽에 network 및 broker-import guard 적용(RED→GREEN).
- round 6 review에서 common Python child-process APIs 보완 후 round 7 review가 native API 우회를 지적했다. 사용자가 이 runner를 신뢰된 checked-in source의 regression test로 한정하고 security sandbox로 주장하지 않는 범위를 승인했다. OS isolation은 이 환경에서 사용할 수 없다.
- `손실률 30% 이상 (수익률 <= -30%)` 규칙의 exact -30% fixture test가 매도 계획 0건으로 실패(RED); 비교를 `<=`로 바꾸고 2/2/1주 virtual sale을 확인(GREEN).
- cross-process deterministic-output 테스트는 hash-randomized subprocess에서 먼저 실패(RED); hash 기반 seed를 SHA-256 안정 seed로 바꾼 뒤 통과(GREEN).

## 최종 검증
| 검사 | 실행 | 결과 |
|---|---|---|
| Trusted-source regression guard | `PYTHONPATH="<dependency-path>:$PYTHONPATH" python3 -W error -m unittest tests.test_demo_portfolio_privacy -v` | 7개 통과; checked-in demo에서 선택된 Python network/process entrypoints patch 및 broker import 감시. OS/native sandbox가 아니며 untrusted code 실행용이 아님 |
| 전체 회귀 | `PYTHONPATH="<dependency-path>:$PYTHONPATH" python3 -W error -m unittest discover -v` | 50개 통과 |
| 오프라인 smoke | `PYTHONPATH="<dependency-path>:$PYTHONPATH" python3 -W error kiwoom_rescue_bot.py` | exit 0; 합성 샘플 출력, broker/auth/order 호출 없음 |
| Compile | `python3 -m compileall -q api strategies tests kiwoom_rescue_bot.py` | PASS |
| Whitespace | `git diff --cached --check` | PASS |
| Rewritten history | filtered mirror의 6개 rewritten branch 각각에 `git rev-list --objects <ref>` 경로 검사; 이전 main/07 tip 및 07E tip에 `git cat-file -e <sha>^{commit}` | 여섯 branch 모두 target path 0개; old tips `87cbe121ca5aa6e5af7764997165dca920f67aa8`, `8986873e5f454c9a23424fadc7669d8f4074d46d`는 mirror object DB에서 미존재(exit 128). 이는 다른 clone/server object 삭제를 뜻하지 않음 |

의존성은 repository 밖 `<dependency-path>`에 설치했으며 Git bundle에 포함하지 않는다. 저장소 기준 설치 목록은 `requirements.txt`다. 위 명령은 Linux/Docker에서 실행한 검증 기록이며 `<dependency-path>`를 해당 환경의 설치 경로로 치환한다. Windows PowerShell에서는 `PYTHONPATH` 경로 구분자로 `;`를 사용한다. 예: `$env:PYTHONPATH = "<dependency-path>;$env:PYTHONPATH"` 후 `python -W error -m unittest discover -v`.

## 안전 검사
- runner의 보증 범위는 신뢰된 repository source의 regression testing뿐이며 OS/native sandbox가 아니다.
- 새 demo는 `DEMO-*` 코드와 `가상 샘플` label만 사용한다.
- 현재 데모 경로에는 `KiwoomAuth`, `KiwoomAPI`, 실계좌 전환 안내 및 주문 호출이 없다.
- Filtered mirror의 여섯 rewritten branch에서 target path가 없고, 확인한 이전 main/07 및 07E tip SHA가 mirror object DB에 없음을 확인했다.
- 기존 계좌형 데이터의 숫자/종목별 세부사항은 코드·테스트·문서에 복사하지 않았다.
- Staged diff 정적 스캔: hardcoded credential 0, shell execution 0, eval/exec 0, pickle load 0. legacy-marker scan의 3개 일치는 합성 fixture의 샘플 금액 및 테스트의 forbidden-marker 검사에만 있으며 실제 계좌값은 포함하지 않는다.

## 원격 상태와 제한
원격 refs는 현재 아직 기존 SHA를 가리키며, 사용자가 제공될 bundle 기반 PowerShell script를 실행하기 전까지 정화가 원격에 반영되지 않는다. Force-push는 이전 clone/fork/backup, GitHub cache 또는 비광고 server-side object의 완전 삭제를 보장하지 않는다. 상세 절차와 SHA mapping은 `AUTOMATION-GIT-HISTORY-REWRITE.md`를 참조한다.

실제 Kiwoom API, 계좌, 인증 또는 주문은 사용하지 않았으며, fixture 검증은 live 호환성 증거가 아니다.
