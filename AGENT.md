
# AGENT.md - Spec-Driven Vibe Coding Rules

이 프로젝트는 바이브코딩 시 md 파일을 자동 생성하는 규칙을 따른다.

## 필수 규칙
1. 작업 시작 전 /docs/01-prd.md, /docs/02-design.md를 반드시 읽는다
2. 각 단계가 끝나면 해당 md 파일을 생성/업데이트한다
3. 구현은 /docs/03-tasks.md 체크박스 순서대로 진행
4. 테스트는 /docs/04-test-plan.md Given-When-Then 형식
5. 검증은 /docs/05-verification.md에 기록

## 폴더 구조
/docs
  /01-prd.md
  /02-design.md
  /03-tasks.md
  /04-test-plan.md
  /05-verification.md
/memory
  /progress.md
  /decisions.md

## 자동 생성 트리거
- "설계해줘" -> 01-prd.md + 02-design.md 생성
- "구현해줘" -> 03-tasks.md 생성 + 체크박스 진행
- "테스트 만들어" -> 04-test-plan.md 생성
- "검증해줘" -> 05-verification.md 생성
- 매일 작업 종료 시 -> memory/progress.md 업데이트

## 커밋 규칙
- docs/*.md 변경 시 별도 커밋: docs: update PRD/design
- 구현 완료 시: feat: T1-T3 완료 + docs 업데이트
