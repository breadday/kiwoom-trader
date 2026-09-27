
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
  - 진행: STEP 07A~07F 구현·검증 및 독립 리뷰 완료. STEP 07F commit `7924a48f2d9b2bf1506f51a383f203382a331d8f`는 로컬 filtered history에 있고, STEP 08 이후 계획은 `docs/AUTOMATION-STEP-08-PLAN.md` 참조. 50개 전체 테스트 및 STEP 07F 전용 7개 테스트 통과.
  - 남음: 최종 STEP 07F/handoff HEAD를 GitHub의 rewritten `main` 및 stage refs에 atomic `--force-with-lease`로 반영하고 전체 ref SHA를 readback해야 한다. 현재 container GitHub 인증은 미설정이라 원격은 기존 SHA 상태. 실제 Kiwoom 응답·페이지네이션·가격부호·휴장일 호환성은 미검증; ORB/BULL_FLAG 및 portfolio recommender 계약 미정의로 fail-closed. Force-push로 다른 clone/fork/cache/server object의 물리 삭제를 보장하지 않는다.

- [ ] T8: Vercel 배포 + accounts.yaml 실전 전환 가이드
  - 파일: /docs/deployment.md
  - 완료조건: paper=False 전환 시 안전 체크리스트
