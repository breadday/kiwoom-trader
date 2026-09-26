# 자동 개발 STEP 07B — 실행 결과 및 재개 지점

## 상태
- 단계: 07B 완료(23개 테스트·독립 리뷰·원격 SHA 확인 완료); 후속 STEP 07C FACTOR 개발 중
- 브랜치: `feat/kiwoom-daily-backtest-stage-07b`
- 기준 커밋: `87cbe121ca5aa6e5af7764997165dca920f67aa8` (STEP 07A)
- 작업 디렉터리: `/workspace/kiwoom_trader-07b` — 기존 dirty worktree와 분리된 linked worktree
- 원격 확인 커밋: `fd71b57c71f9db57ab91a8f4f3a82360a58d6a8e` (`[verified] Backtest RESCUE strategy with daily OHLCV`). `git ls-remote`의 07B 원격 브랜치 SHA와 일치한다.
- 실 API/계좌/주문: 전부 미실행

## 사용자 승인 규칙
1. 첫 거래일 종가로 가상 진입.
2. 이후 각 거래일 종가에서 진입가 대비 손익 임계치를 검사.
3. 즉시청산 임계치가 먼저 충족되면 잔여 전량 청산.
4. 부분매도 임계치만 충족되면 최초 수량의 50%를 한 번 청산하고, 잔량은 후속 즉시청산 또는 마지막 날 종가로 평가.
5. 수수료·세금·슬리피지는 제외.

## 구현
- `StrategyOptimizer(daily_chart_provider=kiwoom_api.get_daily_chart)` 형태로 provider 주입을 지원한다. `kiwoom_api`는 `KiwoomAPI` 인스턴스여야 하며, 종목당 `limit=60`으로 한 번 조회한다.
- 60개가 정확히 도착하지 않거나, 날짜 중복/비정렬 및 비정상 OHLCV이면 실패한다. mock 데이터로 대체하지 않는다.
- RESCUE 23개 parameter 조합은 같은 60일 snapshot으로 계산한다.
- 총수익, 누적자산 곡선 기준 MDD, 일별수익률 기반 연환산 Sharpe, 1개 전략 캠페인의 승률 및 가중 평균 보유일을 산출한다.
- 실제 API/fixture 모두 조회는 주문 메서드에 접근하지 않는다.
- FACTOR daily-score 계약이 없고 포트폴리오 선택 규칙도 데이터 기반으로 정의되지 않아 `optimize_factor`, `optimize_all_strategies`, `recommend_for_portfolio`는 명시적으로 NotImplementedError를 발생시킨다. 기존 synthetic 추천을 실제 성과처럼 표시하지 않는다.

## RED → GREEN
- 최초 4개 신규 테스트 실행: provider constructor 미지원/기존 synthetic fallback 때문에 예상 실패.
- 부분매도 테스트가 처음에는 경계 수익률 부동소수점 비교(`80/100`이 정확히 -20으로 표현되지 않음)로 실패. 임계 손익 퍼센트 계산 대신 종가와 임계가격을 직접 비교하도록 수정해 통과.
- grid 조회 횟수 테스트에서 처음 23회 API provider 호출을 관찰. 검색 전에 한 번만 60개를 검증·조회하고, 같은 snapshot을 각 조합에 재사용해 1회로 수정.
- Factor/전체 최적화/추천의 synthetic 결과가 노출되지 않도록 실패 테스트 3개를 추가해 RED→GREEN.
- 재검토 verdict: `passed=true`, security_concerns/logic_errors 비어 있음. 제안된 Sharpe metric은 이미 결과에 포함되어 있으며(non-blocking), 추가 risk-adjusted 지표는 향후 검토 사항.

## 최종 자동 검사
```text
PYTHONPATH=/tmp/kiwoom-chardet:/tmp/kiwoom-trader-deps python3 -W error -m unittest discover -v
Ran 23 tests — OK (14 daily-chart + 9 daily-backtest tests)
python3 -m compileall -q api strategies tests
PASS
git diff --check (core.whitespace=cr-at-eol)
PASS
```

## 제한·후속 단계
- 22개 테스트는 fixture와 fake provider만 사용. 실제 Kiwoom API schema/pagination/sign encoding은 미검증.
- 수수료/세금/슬리피지 제외; close-only 실행이라 장중 임계치 터치 및 갭 체결을 재현하지 않는다.
- RESCUE 단일 진입/최대 1회 분할매도 정책 기준. 매수 재진입이나 portfolio-level position basis는 모델링하지 않는다.
- STEP 07B 당시 FACTOR 점수와 포트폴리오 선택 규칙이 미정의여서 구현하지 않았다. 해당 계약은 사용자 승인으로 STEP 07C 계획에 정의했고 현재 구현·검증 중이다.
- 다음: STEP 07C FACTOR 고정 매도규칙 백테스트 테스트/구현/독립 리뷰/원격 푸시. 원본 worktree의 미커밋 수정은 계속 보존한다.
