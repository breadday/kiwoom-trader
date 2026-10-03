
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

- [ ] T7: 실제 키움 일봉 연동 백테스트 (부분 완료)
  - 파일: /api/kiwoom_api.py, /api/strategy_optimizer.py, /docs/AUTOMATION-STEP-07*.md
  - 완료조건: 읽기 전용 일봉 조회를 최적화 계산에 연결하고, 확정된 전략/데이터 계약으로 검증
  - 진행: 모의투자 `ka10081` read-only smoke, 실제 일봉 기반 RESCUE 최적화, FACTOR 데이터 연결과 CI 검증을 완료했다. 세부 결과는 `docs/AUTOMATION-STEP-08E-RESULTS.md`와 `docs/REAL-DATA-BACKTEST-RESULTS.md` 참조.
  - 처리: FACTOR 유니버스에서 데이터가 없는 `061220`, `416770`을 제외하고, 데이터가 확인된 6종목(`005935`, `067310`, `086520`, `253590`, `272210`, `441680`)으로 백테스트를 진행한다. ORB/BULL_FLAG 및 portfolio recommender 계약은 fail-closed.

- [ ] T8: Vercel paper 배포 + accounts.yaml 실전 전환 가이드 (paper 배포 완료)
  - 파일: /api/index.py, /vercel.json, /docs/deployment.md
  - 진행: paper-only Vercel Python entrypoint와 secret 환경변수 주입, 안전 가이드 및 회귀 테스트 구현 완료.
  - 진행: `https://kiwoom-trader.vercel.app`에 paper-only production 배포와 응답 read-back을 완료했다.
  - 남음: 실전 전환은 별도 승인 전 금지. accounts.yaml 실계좌 연결과 live 주문은 지원하지 않는다.
  - 완료조건: paper=False 전환 시 안전 체크리스트
