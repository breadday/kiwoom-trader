
# PRD: kiwoom_trader - 멀티 브로커 통합 트레이딩

## 1. Goal
키움, NH, 삼성, KB 4개 증권사를 통합하여 보유종목 관리, 전략별 자동매매, 최적화 추천을 제공하는 대시보드

## 2. User Story
- As a 개인 투자자, I want 4개 증권사 잔고를 한 화면에서 보고 싶다, So that 전체 자산 -945만원을 파악할 수 있다
- As a 트레이더, I want 종목별로 전략(ORB, BULL_FLAG, FACTOR, RESCUE)을 다르게 설정하고 싶다, So that 특정 종목만 안전하게 매매할 수 있다
- As a 의사결정 어려운 투자자, I want 전략 최적화가 자동으로 평가 기준에 따라 추천되길 원한다, So that -44% 스피어 같은 종목을 어떻게 정리할지 결정할 수 있다

## 3. Requirements
- [ ] FR-1: 멀티 브로커 잔고 통합 조회 (MultiAccountManager)
- [ ] FR-2: 종목별 전략 선택 및 개별 실행 (PerStockStrategyEngine run_single/run_selected)
- [ ] FR-3: 증권사 배지 표시 및 통합/선택 뷰 토글
- [ ] FR-4: 전략 최적화 엔진 - 총수익 40%, MDD 30%, 승률 20%, 샤프 10% 종합점수
- [ ] FR-5: 보유종목 vs 최적화 추천 split 뷰
- [ ] FR-6: 대시보드 - 모바일 최적화, 다크모드, 체크박스 + 드롭다운 작동

- [ ] NFR-1: paper=True 안전모드 기본, 전체 실행 금지
- [ ] NFR-2: 전략 변경 즉시 state 반영 (React useState)
- [ ] NFR-3: 초당 5회 API 제한 throttle 0.21s

## 4. Out of Scope
- 실전 주문 (paper=False 전환은 Phase 2)
- NH/삼성/KB 실전 API 연동 (현재 mock)
- 일봉 기반 백테스트 실제 데이터 연동
