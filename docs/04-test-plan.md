
# Test Plan

## Unit Test
- [ ] UT-1: RESCUE 전략 손절 기준
  - Given: pl_pct -44% 스피어 포지션
  - When: RescueStrategy.should_sell(pos, {}) 호출, immediate_th -40
  - Then: should_sell True, reason "즉시정리 -44.27%"

- [ ] UT-2: FACTOR 전략 분기
  - Given: factor_total 30, is_bounce True
  - When: FactorStrategy.should_sell
  - Then: SELL "팩터 30 - 즉시정리"

- [ ] UT-3: run_single 특정 종목만 실행
  - Given: 8종목 포트폴리오, engine.set_strategy("441680", "FACTOR")
  - When: run_single("441680")
  - Then: 441680만 결과 반환, 다른 종목 실행 안됨

- [ ] UT-4: Optimizer grid search
  - Given: code 441680
  - When: optimize_rescue("441680")
  - Then: 18개 조합 반환, score 내림차순 정렬, top -25%/-10%

## Integration Test
- [ ] IT-1: MultiAccountManager 잔고 합산
  - Given: accounts.yaml 4개 계좌
  - When: get_all_balances()
  - Then: total_asset 2,572만원, all_positions 8개

- [ ] IT-2: 전략 변경 -> 최적화 추천 적용
  - Given: 스피어 RESCUE -40/-20
  - When: optimizer 추천 -25/-10 적용, set_strategy
  - Then: run_single 예상 -15%로 개선

## E2E Test
- [ ] E2E-1: 대시보드 플로우
  - Given: 사용자가 대시보드 접속
  - When: 증권사 선택 -> KB -> 스피어 체크 -> 전략 RESCUE -> 이 종목만 실행 클릭
  - Then: SELL 결과 표시, -44% -> -15% 개선 안내

- [ ] E2E-2: 안전모드 검증
  - Given: 대시보드
  - When: 전체 실행 버튼 존재 여부 확인
  - Then: 전체 실행 버튼 없음, 선택 실행만 존재
