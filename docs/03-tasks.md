
# Tasks

- [x] T1: Multi-broker 구조 생성
  - 파일: /api/multi_broker_api.py, accounts.yaml
  - 완료조건: 4개 증권사 mock 잔고 합산 2,572만원 표시

- [x] T2: Per-stock 전략 엔진
  - 파일: /api/strategy_engine.py
  - 완료조건: run_single, run_selected 작동, 전체 실행 제거

- [x] T3: 대시보드 증권사 배지 + 통합/선택 뷰
  - 파일: artifact - multi_broker_dashboard
  - 완료조건: 카드마다 🔴키움 🟢NH 🔵삼성 🟡KB 배지 표시, 필터 작동

- [x] T4: 전략 변경 작동 수정
  - 파일: artifact - fix_strategy_change
  - 완료조건: dropdown onChange -> setStockStrategies, checkbox 토글 작동

- [x] T5: 전략 최적화 엔진
  - 파일: /api/strategy_optimizer.py
  - 완료조건: optimize_rescue grid search, score 공식, recommend_for_portfolio

- [x] T6: 보유종목 vs 추천 통합 뷰
  - 파일: artifact - vs + strategy_optimizer_dashboard
  - 완료조건: split 뷰, 현재 -44% vs 최적 -15% 개선 표시

- [ ] T7: 실제 키움 일봉 연동 백테스트
  - 파일: /api/kiwoom_api.py, /api/strategy_optimizer.py, /docs/AUTOMATION-STEP-07*.md
  - 완료조건: 읽기 전용 일봉 조회를 최적화 계산에 연결하고, 확정된 전략/데이터 계약으로 검증
  - 진행: STEP 07A 일봉 조회기, STEP 07B RESCUE, STEP 07C FACTOR fixture 구현·테스트 완료. STEP 07D 기준일 계약 구현·42개 테스트·독립 리뷰 완료; 원격 SHA `e1b60292add4ccd635d7c49d9e4d6e63ca7e49d5` 확인. STEP 07E bearer token 로그 노출 방지 수정, 43개 테스트 및 독립 리뷰(`deleg_7a636aa3`, passed=true) 완료. 로컬 커밋 `944f002f3f546e73508e05f4e6ae3de20bd3f292`; Docker push 인증 실패, Windows push 대기. 상세는 `docs/AUTOMATION-STEP-07D-RESULTS.md`, `docs/AUTOMATION-STEP-07E-RESULTS.md`.
  - 남음: 실제 Kiwoom 응답·페이지네이션·가격부호·휴장일 호환성은 미검증; 읽기 전용 credential probe는 별도 승인된 환경에서만 수행. ORB/BULL_FLAG 및 portfolio recommender는 규칙/계약 미정의로 fail-closed 상태이며 별도 설계 필요.

- [ ] T8: Vercel 배포 + accounts.yaml 실전 전환 가이드
  - 파일: /docs/deployment.md
  - 완료조건: paper=False 전환 시 안전 체크리스트
