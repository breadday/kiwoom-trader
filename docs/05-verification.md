
# Verification Report - 2026-09-21

## 1. 요구사항 대비 검증
| FR | 구현됨? | 테스트됨? | 비고 |
|----|---------|-----------|------|
| FR-1 멀티 브로커 통합 | O | O | 4개 mock, 합산 2,572만원 |
| FR-2 종목별 전략 개별 실행 | O | O | run_single/run_selected, 전체 실행 제거 |
| FR-3 증권사 배지 + 뷰 토글 | O | O | 🔴🟢🔵🟡 배지, 통합/선택 필터 작동 |
| FR-4 전략 최적화 | O | O | score 공식, grid search 18개, -44%->-15% |
| FR-5 보유 vs 추천 split 뷰 | O | O | 같은 8종목 split 카드 |
| FR-6 모바일 다크모드 + 작동 | O | O | useState 연결 수정 완료 |

## 2. 버그 리스트
- [x] BUG-001: 전략 드롭다운 안 바뀜 -> Fix: setStockStrategies 연결 (artifact 7)
- [x] BUG-002: 증권사 배지 없음 -> Fix: badge pill 추가 (artifact 4,6,7)
- [x] BUG-003: 전체 실행 위험 -> Fix: run_all 제거, safe mode (strategy_engine.py)
- [x] BUG-004: optimizer IndexError -> Fix: partial_th <= immediate_th 조건 수정
- [ ] BUG-005: mock_history 실제 데이터 아님 -> Phase 2에서 일봉 연동 필요

## 3. 회고
- 바이브코딩 시 md 없이 하면 3일 뒤 기억 안남 -> AGENT.md에 규칙 박음
- 전략 변경 안 되는 건 React state 미연결이 원인 -> useState 필수
- 평가 기준 못 잡을 때는 가중치 40/30/20/10으로 종합점수화하면 결정 쉬움
- API 부분은 나중에 추가하기로 하고 대시보드 먼저 통과 -> Phase 분리 좋음
