# 자동 연속 진행 개발 문서

## 이번 사이클에서 구현한 항목

- `automation/continue_safe.py` 추가
  - 저장소 로컬에서만 실행
  - 프로젝트 Python 환경의 pytest 실행
  - `api`, `strategies`, `tests`, `automation` compile 검사
  - 합성 데이터 rescue 데모 실행
  - `git diff --check` 실행
  - 결과를 Markdown으로 기록
- 실행기는 credential, broker, Telegram, Vercel, 네트워크를 사용하지 않는다.
- 실행기는 commit, push, force-push를 수행하지 않는다.
- 기존 오프라인 데모의 직접 실행 회귀 테스트와 안전 실행기 테스트를 유지한다.

## 변경 원칙

- 외부 상태 변경보다 재현 가능한 로컬 검증을 우선한다.
- 새 동작은 failing test를 먼저 추가한 뒤 구현한다.
- 실데이터가 없거나 규칙이 승인되지 않은 경우 합성 결과를 운영 결과처럼 만들지 않는다.
- 원격 ref 재작성은 현재 SHA와 명시 승인이 없으면 실행하지 않는다.

## 다음 개발 후보

1. Gate 0 rewrite bundle과 현재 원격 SHA를 별도 승인 후 재생성한다.
2. 승인된 데이터 계약이 제공되면 FACTOR 백테스트 누락 종목을 다시 조회한다.
3. 승인된 신호 규칙이 제공되면 production scan evaluator를 테스트 우선으로 구현한다.
4. 다중 인스턴스 운영이 필요하면 분산 lock/state 저장소 설계를 먼저 확정한다.
