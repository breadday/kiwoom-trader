# 자동 연속 진행 테스트 계획

## 자동 실행 대상

| 대상 | 목적 | 실패 시 조치 |
|---|---|---|
| `pytest -q` | 전체 회귀 검증 | 실패 테스트를 재현하고 코드 변경 전 원인 확인 |
| `compileall` | Python 문법·import 기본 검증 | 오류 파일을 수정하고 다시 실행 |
| `automation/kiwoom_rescue_demo.py` | 합성 데이터 오프라인 경로 검증 | broker/credential 의존성이 들어오지 않았는지 확인 |
| `git diff --check` | 공백 오류 방지 | 변경 파일의 whitespace 수정 |

## 테스트 우선 규칙

1. 새 기능 또는 버그마다 최소 회귀 테스트를 먼저 작성한다.
2. 해당 테스트가 예상된 이유로 실패하는지 확인한다.
3. 가장 작은 구현으로 통과시킨다.
4. 대상 테스트와 전체 테스트를 모두 실행한다.
5. 결과를 `docs/AUTOMATED-CONTINUATION-RESULTS.md`에 기록한다.

## 안전 테스트 범위

- 실계좌, 실주문, credential 값, Telegram 실제 전송, Vercel 변경, 원격 push는 이 자동 테스트에서 다루지 않는다.
- 운영 검증이 필요한 항목은 테스트 성공으로 간주하지 않는다.
- 미완료 항목은 `docs/UNRESOLVED.md`의 상태와 재개 조건을 기준으로 판단한다.
