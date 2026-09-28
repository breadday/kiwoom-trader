# AUTOMATION
자동화 진행상황

- [x] daily.py 캐싱
- [x] 주문 안전성 구현 (dry-run/mock only, live order blocked)
- [x] 스캔 자동화 (read-only provider/evaluator/sink 분리, 주문 실행 없음)
- [ ] 텔레그램 알림

진행할 때마다 여기에 적고 Codex에게 시킴

## daily.py 캐싱 구현

- `api/daily.py`의 메모리 캐시를 `KiwoomAPI.get_daily_chart()`에 연결.
- API 인스턴스별 보관, TTL 300초, 최대 128개 항목(LRU). 프로세스 종료 시 소멸하며 디스크에는 저장하지 않음.
- 키: API URL, 종목코드, 확정된 기준일(KST 기본값 포함), limit, max_pages, 수정주가 구분.
- 검증 및 페이지 조회가 성공한 비어 있지 않은 결과만 저장. 오류와 빈 결과는 다음 요청에서 재조회.
- 반환값은 복사하여 호출자의 수정이 캐시를 오염시키지 않음.
- `get_daily_chart("005930", refresh=True)`로 해당 조건을 무효화하고 재조회.
- `api.clear_daily_cache()`로 인스턴스 전체 캐시 삭제.
- 기본값 및 명시적 당일 조회 모두 TTL 적용: 최신 값이 즉시 필요하면 `refresh=True` 사용.

## 현재 검증 상태

- 주문·전략·일봉·optimizer·privacy·스캔 안전성 테스트 86개 통과.
- `paper=False` 주문은 모든 adapter에서 fail-closed 처리.
- 저장소 로컬 `.tmp-pydeps` 경로의 `pandas`·`numpy`를 사용해 전체 unittest discovery를 통과함.
- 실제 Kiwoom read-only API 호출과 실주문은 인증·운영 승인 전까지 실행하지 않음.

## 스캔 자동화 구현

- `api/scanner.py`의 `ReadOnlyMarketScanner`는 명시된 6자리 종목코드만
  설정 순서대로 조회하며 종목당 provider를 한 번 호출한다.
- 조회 결과는 OHLCV·날짜 정렬을 다시 검증한 뒤 외부에서 주입한 evaluator에만
  전달한다. 스캐너가 투자 규칙이나 추천 기준을 임의 생성하지 않는다.
- provider/evaluator 오류가 발생한 종목은 `ERROR`, `matched=False`로 닫고
  다른 종목 스캔은 계속한다.
- `ScanRunner`는 결과 sink로만 batch를 전달한다. broker/order 모듈을 사용하지
  않으며 `max_cycles` 또는 stop event로 안전하게 중단할 수 있다.
- 다음 텔레그램 단계에서는 주문 기능을 추가하지 않고 결과 sink adapter만
  연결한다.
