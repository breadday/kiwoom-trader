
# Decisions ADR

## ADR-001: 전체 실행 제거 (2026-09-21)
- Context: 전체 실행은 위험해서 특정 종목만 전략 바꾸자
- Decision: run_all() 제거, run_single(code), run_selected(codes)만 허용
- Consequence: 안전모드, paper=True 필수

## ADR-002: 평가 기준 가중치 (2026-09-21)
- Context: 내가 결정하기 어려워서 평가 기준 못 잡음
- Decision: 총수익 40%, MDD 30%, 승률 20%, 샤프 10% 종합점수
- Formula: score = (return+50)*0.8 + (30-MDD) + win_rate*30 + sharpe*10

## ADR-003: 증권사 배지 필수 (2026-09-21)
- Context: 카드에는 증권사가 없네, 통합 vs 선택 화면 구분 안됨
- Decision: 카드 맨 위에 pill 배지 - 키움 빨강, NH 초록, 삼성 파랑, KB 노랑
- View: 통합으로 보기 vs 선택하여 보기 토글 + 서브탭

## ADR-004: Spec-Driven Vibe Coding (2026-09-21)
- Context: 바이브코딩 시 md 없이 하면 3일 뒤 기억 안남
- Decision: /docs 5개 md + /memory 2개 md + AGENT.md 규칙 고정
- Automation: 3가지 방법 - AGENT.md 트리거, 프롬프트 템플릿, 커밋 훅
