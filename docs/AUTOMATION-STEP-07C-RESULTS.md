# 자동 개발 STEP 07C — FACTOR 일봉 백테스트 결과 및 재개 지점

## 상태
- 코드·테스트·문서 완료; 40개 테스트와 구현/테스트/문서 독립 리뷰 통과; 구현 커밋 `a08dba709b364f638c28ad3a373c026b226062ee` 원격 SHA 확인, 후속 문서 상태 갱신은 로컬에서 push 대기
- 브랜치 `feat/kiwoom-daily-backtest-stage-07c`, 격리 worktree `/workspace/kiwoom_trader-07c`
- 기준/부모 커밋: STEP 07B `fd71b57c71f9db57ab91a8f4f3a82360a58d6a8e` (원격 일치 확인)
- 구현 커밋 `a08dba709b364f638c28ad3a373c026b226062ee`는 원격과 일치 확인. 현재 추가된 문서 상태 보정은 로컬에서 push 대기. 원본 checkout의 사용자 변경은 수정하지 않음

## 승인된 동작
- 유니버스: `005935`, `061220`, `067310`, `086520`, `253590`, `272210`, `441680`, `416770`.
- 심볼마다 312거래일을 provider에서 한 번 조회한다: 252 lookback + 60 평가. 종목 간 달력 날짜가 정확히 일치하지 않으면 실패.
- 4개 요인은 기존 `FactorSwingStrategy.calc_factors`와 같은 현재 봉 포함 행 기준/가중치: momentum `close[-21]/close[-252]-1` (최근 252행) 40%, 최근 60개 일간 수익률 표본 표준편차 역수(`ddof=1`) 30%, 최근 60행 평균 거래량 20%, 가치 대용 `-(close[-1]/close[-60]-1)` 10%. 실제 PER/PBR은 사용하지 않는다.
- 품질은 8개 중 `floor(.3 × 8)=2`개 최저 거래량을 제외한다. 동일 거래량 경계에서는 종목코드 오름차순 tie-break를 적용해 정확히 2개만 제외한다.
- 각 평가일 raw composite score의 유니버스 백분위로 0–100 점수를 만든다(평균 순위, 전체 동일/단일 점수는 50점, 품질 필터 제외는 0점).
- 월요일 종가에서만 최신 일봉 factor score와 반등 조건을 평가한다. 주문은 다음 거래일 시가에서 체결해 동일 종가 look-ahead를 방지한다. `score < 40`이면 잔량 전부 청산 우선. 그렇지 않고 `score < 50`이며 월요일 종가가 직전 거래일 종가보다 높으면 최초수량의 50%를 한 번 매도. 마지막 bar 신호는 후속 시가가 없어 체결하지 않고 잔량을 마지막 종가로 처리.
- 신규 매수·비중조절은 하지 않는다. 각 종목 첫 평가일 종가 가상 진입. 매도 캠페인당 거래 수수료·세금·슬리피지는 미포함.
- metrics: 종목별 단일 캠페인 `total_trades=1`; `win_rate`는 그 캠페인 수익이 양수면 1, 아니면 0. daily close equity 변화율로 Sharpe를 산출(무위험 수익률 0, 표본 표준편차, 연환산 √252; 변동성 0이면 0), MDD는 초기자본 1을 포함한 daily-close equity curve에서 계산. `avg_hold_days`는 거래일 offset 단위이며 partial이면 최초수량의 각 절반에 가중한 체결/종료 offset의 평균.

## 구현 내용
- `StrategyOptimizer.simulate_factor_universe()`는 8개 종목 데이터를 각 1회 받아 8개 캠페인을 계산한다. 요청 데이터 부족, OHLCV 불일치, 불가능한 날짜, 날짜축 불일치를 fail-closed 처리한다.
- `optimize_factor(code)`는 승인된 코드만 받으며, 횡단면 계산을 위해 provider에서 8개 전체 history를 각 1회 가져온 뒤 해당 코드 결과 1개를 반환한다. 유니버스 밖 코드는 조회 전에 거부.
- score는 해당 일봉 종가 확정 후 월요일 신호를 만들고, next-session-open fill로 실행한다. Factor score mapping, 즉시 우선, partial one-shot latch, 종료 후 잔량 mark와 open-gap 영향을 테스트했다.
- `optimize_all_strategies`는 ORB/BULL_FLAG 일봉 규칙이 없어서 계속 미지원. `recommend_for_portfolio`는 아직 포트폴리오 비교/선택 계약이 없어 fail-closed 유지.
- STEP 07B 결과 문서의 실제 원격 SHA 및 provider 예시를 함께 정정했다.

## RED → GREEN / 검증
- 1차 독립 리뷰 `passed=false`: 252/60행 endpoint 해석, quality 경계 동률, score index, equity metrics 지적. 확인 후 source excerpt와 일치하는 row indices를 테스트로 고정, 정확히 `floor(.3N)` 제거 및 코드 tie-break, entry offset 규칙 명확화, exit-day mark 검증을 추가.
- 2차 독립 리뷰 `passed=false`: close에서 산출한 월요일 점수를 같은 close에 체결하면 look-ahead가 발생한다는 지적. 사용자 승인에 따라 신호는 월요일 close 확정, 체결은 다음 거래일 open으로 변경. close 110 / next open 80 fixture가 구 구현에서 +10%를 내는 RED를 확인하고 수정 뒤 -20%로 검증. 추가로 마지막 horizon 월요일 partial 신호에 다음 open이 없는데 latch만 켜져 `partial_day=None` 오류가 나는 RED를 확인하고 실행 가능한 후속 bar가 있을 때만 신호를 예약하도록 수정. 해당 수정본은 3차 독립 리뷰에서 구현/테스트/문서 모두 `passed=true`를 확인.
- Factor 점수 helper와 미지원 API는 구현 전에 missing-feature/NotImplemented RED를 확인한 뒤 구현으로 통과.
- 부분매도 회귀 시나리오가 주간 날짜 fixture에서 첫 월요일 전날이 진입일과 겹치는 점을 발견. 첫 평가 월요일은 건너뛰고 2·3번째 월요일에 반등/재통과를 배치하여 진입가를 보존한 검증으로 수정.
- 잘못된 달력 날짜가 8개 데이터에서 같은 위치에 있을 때 검증되는 케이스를 RED로 재현하고 `datetime.strptime` 유효성 확인을 추가.
- 처음 전체 테스트는 환경에 `requests`가 없어 일봉 API 모듈을 불러오지 못했다. `/tmp/kiwoom-trader-deps`에 requests와 chardet 5.2.0을 설치 후 재실행.

최종 명령 결과:
```text
PYTHONPATH=/tmp/kiwoom-chardet:/tmp/kiwoom-trader-deps python3 -W error -m unittest discover -v
Ran 40 tests — OK
(14 daily-chart + 9 RESCUE + 17 FACTOR)

python3 -m compileall -q api strategies tests
PASS

git -c core.whitespace=cr-at-eol diff --check
PASS
```

## 제한 및 남은 범위
- 체결은 다음 거래일 시가로 가정해 open gap을 반영하지만, 일봉 OHLC 기반이므로 장중 가격경로·주문 대기열/시장충격은 모델링하지 않는다. 수수료·세금·슬리피지는 제외.
- 테스트는 fake provider만 사용. 실제 Kiwoom ka10081 schema/pagination/가격 부호 규약과 live/paper 호환성은 미검증이며, 실 API·계좌·주문을 실행하지 않음.
- 값/기간별 수익과 점수는 승인된 가정 하의 결정론적 시뮬레이션일 뿐 수익 보장이나 투자 권유가 아님.
- PER/PBR 등 실제 재무자료를 쓰지 않고 60일 역모멘텀을 가치 대용치로 쓴다. 기존 원본 전략 코드의 값/품질 proxy 정의를 그대로 따른다.
- 일봉 샘플은 키움 시장 휴일/수정주가의 실제 기준을 외부에서 검증해야 함. 현재 client는 adjusted-bar request flag를 사용하나 live contract 검증은 별개.
- 다음 단계: Windows에서 브랜치 `feat/kiwoom-daily-backtest-stage-07c`를 push하고 원격 브랜치 SHA를 현재 로컬 HEAD와 대조한다. 컨테이너 push는 HTTPS Username 자격증명 부족으로 실패했으며 SSH 인증도 설정되어 있지 않다. 원격 반영 전.
- 전체 미완료 범위: 실제 Kiwoom API 응답/페이지네이션/가격 부호 규약은 fixture 밖에서 미검증. ORB/BULL_FLAG 규칙과 portfolio recommender 계약은 미정의/미지원이며 별도 설계가 필요하다.
