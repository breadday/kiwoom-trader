# AUTOMATION
자동화 진행상황

- [x] daily.py 캐싱
- [x] 주문 안전성 구현 (dry-run/mock only, live order blocked)
- [x] 스캔 자동화 (read-only provider/evaluator/sink 분리, 주문 실행 없음)
- [x] 텔레그램 알림 (MATCH/ERROR 전용 result sink, 환경변수 자격증명)
- [x] 스캔 실행 엔트리포인트 (환경변수 설정, paper 고정, 기본 1회 실행)

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

- 주문·전략·일봉·optimizer·privacy·스캔·텔레그램·엔트리포인트 안전성 테스트 104개 통과.
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
- 텔레그램 단계에서도 주문 기능을 추가하지 않고 결과 sink adapter만 연결했다.

## 텔레그램 알림 구현

- `api/telegram_notifications.py`의 `TelegramScanResultSink`를
  `ScanRunner(result_sink=...)`에 주입한다. 주문·계좌 모듈 의존성은 없다.
- 자격증명은 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 환경변수에서만 읽으며
  누락되거나 형식이 잘못되면 네트워크 호출 전에 실패한다.
- `MATCH`와 `ERROR`만 한 번의 plain-text batch 알림으로 전송한다.
  `NO_MATCH`만 있는 주기는 전송하지 않아 반복 알림을 제한한다.
- 같은 sink 프로세스 안에서는 종목별 상태·사유·최신 일자·종가·거래량이 모두
  같은 `MATCH`/`ERROR`를 재전송하지 않는다. `NO_MATCH` 전환 후 다시 발생하거나
  fingerprint가 달라지면 새 알림으로 전송한다.
- Telegram 전송이 실패한 결과는 전송 완료 상태로 기록하지 않아 다음 주기에
  다시 시도한다.
- `KIWOOM_ALERT_STATE_FILE`을 지정하면 버전이 있는 JSON 상태를 임시 파일 작성 후
  원자적으로 교체한다. 새 프로세스도 같은 파일을 읽어 동일 알림을 억제하며, 손상·
  과대 상태 파일은 네트워크 호출 전에 거부한다. 로컬 단일 스케줄러 권장값은
  `automation/runs/telegram-alert-state.json`이며 이 디렉터리는 Git에서 제외된다.
- 상태 파일을 지정하지 않으면 기존처럼 프로세스 메모리에서만 중복을 억제한다.
  Vercel의 임시 파일시스템은 실행 간 영속성을 보장하지 않으므로 배포 환경에서는
  외부 durable store를 연결하기 전까지 이 파일 옵션을 영속 저장소로 간주하지 않는다.
- Telegram 응답 실패와 전송 예외는 토큰, 요청 URL, 응답 본문을 노출하지 않는
  `TelegramDeliveryError`로 변환한다.
- 메시지는 4,000자로 제한하며 초과 항목 수를 표시한다.
- 실제 Telegram 전송은 운영 토큰과 채팅 ID가 등록된 승인 네트워크 환경에서만
  수행한다. 현재 검증은 주입한 가짜 transport를 사용해 외부 전송 없이 완료했다.

## 스캔 실행 엔트리포인트

- `api/scan_entrypoint.py`의 `run_scan_once(evaluator=...)`는 Kiwoom 일봉 조회,
  `ReadOnlyMarketScanner`, `TelegramScanResultSink`를 조립해 정확히 한 주기만
  실행한다. 스케줄러가 호출할 때 프로세스가 누적되지 않도록 기본 반복 실행은 없다.
- API는 코드에서 `paper=True`로 고정하고 생성 결과가 paper 모드가 아니면 일봉
  조회 전에 실패한다. 주문 함수는 호출하지 않는다.
- 필수 환경변수: `KIWOOM_SCAN_CODES`(쉼표 구분 6자리 코드),
  `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
- 선택 환경변수: `KIWOOM_SCAN_LIMIT`(기본 60),
  `KIWOOM_SCAN_INTERVAL_SECONDS`(기본 300, 향후 반복 runner용).
- 투자 신호 evaluator는 호출자가 명시적으로 주입한다. 데이터로 검증되지 않은
  매매 규칙을 엔트리포인트가 임의로 선택하지 않으며, evaluator 미지정 시 실행할
  수 없다.
