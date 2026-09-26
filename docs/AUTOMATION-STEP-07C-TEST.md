# 자동 개발 STEP 07C — FACTOR 백테스트 테스트 명세

## 안전 경계
테스트는 fake OHLCV provider만 사용하며 계좌/API 주문은 실행하지 않는다. 8개 유니버스 각 312개 일봉(252 lookback + 60 평가)을 요구한다.

## RED → GREEN 시나리오
- `_factor_percentiles`: 4종목 교차순위, 동점 평균 순위, 품질 제외 0점 처리.
- `_factor_measurements`는 기존 `FactorSwingStrategy`의 현재 봉 포함 252행/60행 인덱스 규칙, 표본 표준편차(`ddof=1`), 거래량 평균과 일치하며 파생 비유한 수익률/요인을 거부.
- `_exclude_low_quality`: 8종목 중 정확히 floor(30%) 제외; 품질 동률은 코드 오름차순으로 고정하고 비유한 품질은 거부.
- 단일 종목/전체 동점 composite score는 중립 백분위 50점.
- entry offset 0의 동일 종가에서 신호/매도를 실행하지 않는다. 월요일 종가의 score와 bounce로 신호를 확정하고, 다음 거래일 시가를 매도가로 적용한다. 마지막 evaluation bar의 월요일 신호는 미래 open이 없으므로 실행하지 않고 horizon 종가로 잔량 평가.
- 체결 종가(다음 거래일 open)로 수익/MDD가 반영되고, 전량청산 후 자산곡선이 현금으로 평탄해지는지 확인.
- 월요일 close만 매도 신호를 평가하고 score <40 전량청산을 score <50 부분매도보다 우선.
- score <50 및 월요일 종가 상승에서 최초수량의 절반을 1회 매도; 다음 월요일 재통과에도 중복 매도하지 않고 최종 종가 잔량 평가.
- 8개 심볼에 각각 정확히 한 번 `limit=312` 조회, 결과 8개 반환.
- 서로 다른 날짜 축, 잘못된 달력 날짜, 부족/비정상 OHLCV는 fail-closed.
- 허용 목록 밖 `optimize_factor` 코드는 데이터 조회 전에 거부.
- 사용 코드 패턴과 provider 반복 호출 여부를 고정하여 회귀 방지.

## 실행 명령
```sh
python3 -m unittest tests.test_optimizer_factor_backtest -v
python3 -W error -m unittest discover -v
python3 -m compileall -q api strategies tests
git diff --check
```

## 완료 조건
07A 일봉 클라이언트, 07B RESCUE, 07C FACTOR 테스트가 모두 통과해야 한다. 최종 테스트 개수·리뷰 verdict·원격 SHA는 결과 문서에 관측된 값으로 기록한다.
