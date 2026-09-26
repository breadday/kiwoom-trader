# 자동 개발 STEP 07B — 테스트 명세

## 안전 범위
모든 테스트는 fixture provider만 사용한다. 실제 API 요청·계좌 조회·매수/매도 주문 호출은 금지한다.

## RED→GREEN 사례
- `test_partial_threshold_sells_half_and_marks_remainder_at_last_close`: -20% 종가에서 50% 청산, 최종 잔량 평가로 -15% 결과.
- `test_partial_threshold_is_latched_after_rebound_and_recross`: -20% 도달 뒤 반등·재하락해도 부분매도는 한 번뿐이다.
- `test_immediate_threshold_exits_full_position_before_partial`: 즉시 임계치가 먼저 충족되면 전량 청산.
- `test_requires_exact_requested_history_and_never_uses_mock_fallback`: 59개뿐이면 오류.
- STEP 07B에서는 FACTOR 미지원 동작으로 닫혔고, 다음 07C 회귀에서는 `test_factor_optimization_rejects_code_outside_universe_without_fetching_data`가 허용 유니버스 밖 종목을 조회 전에 거부하는지 확인.
- `test_all_strategy_optimization_fails_closed_without_orb_bull_flag_rules`: 07C에서도 ORB/BULL_FLAG 일봉 규칙 미정의로 전체 전략 최적화는 fail-closed.
- `test_portfolio_recommendation_does_not_use_synthetic_history`: mock trend 기반 추천을 제거하고 명시적으로 실패.
- `test_fails_closed_when_no_daily_chart_provider_is_configured`: provider 누락 시 오류.
- `test_rescue_grid_fetches_daily_history_once_for_all_parameter_sets`: 전체 grid에서 동일 60봉 조회 1회, 23개 유효 조합, 점수 내림차순.

## 실행 명령
```sh
PYTHONPATH=/tmp/kiwoom-chardet:/tmp/kiwoom-trader-deps python3 -W error -m unittest discover -v
python3 -m compileall -q api strategies tests
```

## 완료 조건
- 위 테스트 및 STEP 07A fixture 테스트 모두 통과.
- 문서에 관측된 실제 테스트 개수와 결과, reviewer verdict를 기록.
- real/paper server 연결 및 주문 테스트는 실행하지 않는다.
