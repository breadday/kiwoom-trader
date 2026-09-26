# 자동 개발 STEP 07B — RESCUE 일봉 백테스트 계획

## 상태
- 단계: 구현 시작
- 브랜치: `feat/kiwoom-daily-backtest-stage-07b`
- 기준 커밋: `87cbe121ca5aa6e5af7764997165dca920f67aa8` (07A 원격 SHA 확인 완료)
- 작업 트리: `/workspace/kiwoom_trader-07b` (기존 미커밋 파일이 있는 원본 worktree와 분리)

## 목표
Kiwoom 일봉 차트 provider를 주입받아 RESCUE parameter grid를 실제 60일 OHLCV로 계산한다. 데이터가 없거나 60개 미만이면 mock 데이터로 대체하지 않고 명확히 실패한다.

## 승인된 시뮬레이션 규칙
- 60거래일 첫 봉 종가를 가상 진입가로 둔다.
- 각 후속 일자의 종가 기준으로 진입가 대비 손익률을 계산한다.
- 즉시청산 임계치 도달 시 잔여 전량을 해당 종가에 청산한다(부분매도보다 우선).
- 즉시청산 전 부분매도 임계치 도달 시 최초 수량의 50%를 한 번 매도한다. 잔량은 이후 즉시청산 신호 또는 60일째 종가로 처리한다.
- 수수료·세금·슬리피지는 제외한다. 실계좌 주문은 하지 않는다.
- grid search는 한 번 받은 동일한 유효 60일 데이터를 모든 파라미터 조합에서 재사용한다.

## 범위와 제외
- 이 단계는 RESCUE 전략만 대상으로 한다. FACTOR 점수 입력, 포트폴리오 전략 배정, 거래비용 모델은 현재 명세가 없어 이번 결과에 포함하지 않는다.
- 기존 원본 worktree의 `.gitignore`, `README.md`, optimizer, broker 및 main 파일 미커밋 변경은 보존한다.
- 실제 Kiwoom 네트워크/API 호출과 실주문은 하지 않는다. provider fixture로 end-to-end 계산을 검증한다.

## 완료 게이트
1. provider 주입, 실제 OHLCV 입력 의존성, 부분매도·즉시청산 케이스가 TDD RED→GREEN.
2. 60개 봉 강제, 잘못된/부족 데이터에서 fail-closed.
3. grid 전체에 API fetch 한 번만 발생.
4. 전체 테스트/compile/whitespace 및 독립 리뷰 통과.
5. docs에 정확한 결과 기재 후 커밋·푸시 시도 및 remote SHA 확인.
