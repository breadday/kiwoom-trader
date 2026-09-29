# AUTOMATION
자동화 진행상황

- [x] daily.py 캐싱
- [x] 주문 안전성 구현 (dry-run/mock only, live order blocked)
- [x] 스캔 자동화 (read-only provider/evaluator/sink 분리, 주문 실행 없음)
- [x] 텔레그램 알림 (MATCH/ERROR 전용 result sink, 환경변수 자격증명)
- [x] 스캔 실행 엔트리포인트 (환경변수 설정, paper 고정, 기본 1회 실행)
- [x] 로컬 스케줄 안전장치 (동시 실행 잠금, 제한적 Telegram 재시도)
- [x] Kiwoom 요청 throttle (단조시계, 동시 호출 직렬화, 최소 0.21초)
- [x] 스캔 OHLCV 유한수 검증 (NaN/Infinity fail-closed)
- [x] 멀티 브로커 잔고 안전성 (명시적 paper 설정만 허용, live/mock 혼동 차단)
- [x] 전략 엔진 합성 fallback 제거 (명시적 전략·market-data provider 필수)
- [x] 다중 종목 전략 사전평가 (전체 검증 후 paper action 실행)
- [x] 다계좌 동일 종목 모호성 차단 (명시적 account_id+code 실행 경로)
- [x] 전략 분할매도 수량화 및 성공 체결 1회 래치
- [x] 분할매도 상태 원자 저장 및 재시작 중복 차단
- [x] 분할매도 상태 로컬 다중 프로세스 잠금

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

## Kiwoom 요청 제한

- `api/request_throttle.py`의 `RequestThrottle`은 `time.monotonic()`과 프로세스
  내부 잠금을 사용해 동시 호출을 직렬화하고 요청 시작 간 최소 0.21초를 보장한다.
- 일봉 페이지 조회, 분봉 조회, paper 주문 처리 및 live 잔고 조회가 같은 API
  인스턴스 throttle을 사용한다. live 주문은 기존과 같이 네트워크 전에 차단된다.
- 스캐너는 evaluator 호출 전에 모든 OHLC 가격과 거래량이 유한수인지 확인하며
  `NaN`/`Infinity`를 종목별 `ERROR`로 격리한다.

## 현재 검증 상태

- 주문·전략·일봉·optimizer·privacy·스캔·텔레그램·엔트리포인트 안전성 테스트 149개 통과.
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

## 로컬 스케줄 안전장치

- `KIWOOM_SCAN_LOCK_FILE`을 지정하면 `run_scan_once`가 OS 비차단 파일 잠금을
  획득한 뒤에만 API 객체를 생성한다. 권장값은 `automation/runs/scan.lock`이다.
  동일 호스트에서 앞선 실행이 끝나지 않았으면 `ScanAlreadyRunningError`로 즉시
  중단하며, 프로세스 종료 시 OS가 잠금을 해제하므로 stale PID 판정은 사용하지 않는다.
- Telegram 전송은 `KIWOOM_ALERT_MAX_ATTEMPTS`(기본 3회)와
  `KIWOOM_ALERT_RETRY_SECONDS`(기본 2초)로 제한한다. `TelegramDeliveryError`만
  재시도하고 상태 파일 쓰기 오류·설정 오류·코드 오류는 반복하지 않는다.
- 파일 잠금은 단일 호스트용이다. Vercel 또는 다중 인스턴스 배포에서는 외부
  distributed lock과 durable state store가 별도로 필요하다.

## 멀티 브로커 잔고 안전성

- Kiwoom, NH, Samsung, KB adapter의 `paper=False` 잔고 조회는
  `LiveBalanceDisabledError`로 네트워크 또는 mock 반환 전에 차단한다.
- `MultiAccountManager`는 `accounts.yaml`이 없을 때 암묵적 mock 계좌를 만들지
  않는다. `accounts:` 목록을 명시해야 하며 중복 ID, 미지원 broker, 잘못된 문서
  구조와 boolean이 아닌 `paper` 설정은 adapter 생성 전에 거부한다.
- paper adapter의 mock 잔고는 명시적으로 `paper: true`인 경우에만 사용할 수 있다.
- 통합 전 각 balance의 현금, 6자리 종목코드, 양의 정수 수량, 유한한 양수
  평균가·현재가를 검증한다. 음수·boolean·`NaN`·`Infinity`·잘못된 구조는
  총계 계산 전에 실패한다.
- 같은 종목이 여러 계좌에 있어도 계좌별 포지션을 유지하며 임의로 평균단가나
  수량을 합쳐 하나의 포지션으로 만들지 않는다.

## 전략 엔진 입력 안전성

- `PerStockStrategyEngine`은 `run`, `run_single`, `run_selected`에서 호출자가
  제공한 market-data provider를 필수로 요구한다. provider가 없을 때 손익률로
  가짜 factor/bounce/change 값을 생성하던 fallback은 제거했다.
- 각 보유 종목은 `set_strategy` 또는 `set_strategies_bulk`로 전략을 명시해야 한다.
  전략이 없는 종목을 자동으로 `FACTOR`에 배정하지 않는다.
- provider 결과가 mapping이 아니면 평가·paper 매도 전에 실패한다. 여러 종목을
  실행할 때는 모든 포지션의 전략·market-data·판정 결과를 먼저 검증한 후에만
  paper action을 순서대로 실행한다.
- `run_selected`는 중복 종목코드를 평가 전에 거부해 같은 포지션을 두 번 매도하지
  않으며, 선택 순서를 유지한다. 후속 종목의 검증 실패는 앞 종목의 paper action도
  실행되기 전에 전파된다.
- 같은 종목을 여러 계좌에서 보유하면 종목코드만 받는 `run_single`과
  `run_selected`는 provider 조회와 paper 매도 전에 `AmbiguousPositionError`로
  중단한다. 특정 포지션은 `run_account_position(account_id, code, provider)`로
  계좌와 종목을 함께 지정해야 하며, 해당 계좌의 포지션만 실행한다.
- 각 전략 판정은 `should_sell`, `sell_fraction`, `reason`을 반환한다. 즉시정리와
  손절은 현재 수량 전부, RESCUE·FACTOR 분할매도는 현재 수량의 50%를 매도하며
  홀수 수량은 위험 축소 방향으로 올림한다.
- `PerStockStrategyEngine(..., partial_exit_state_file=...)`을 지정하면 계좌·종목·전략별
  분할매도 상태를 버전이 있는 JSON 파일에 임시 파일 작성 후 원자 교체한다. 권장
  로컬 경로는 Git에서 제외된 `automation/runs/partial-exit-state.json`이다.
- 분할매도 주문 전에 `pending` 예약을 먼저 저장하고 성공(`status=filled`) 후
  `filled`로 확정한다. 예약 저장 실패 시 주문을 호출하지 않으며 명시적 오류 응답만
  예약을 해제해 재시도할 수 있다. 주문 예외·불명 응답·주문 도중 프로세스 종료는
  체결 여부가 불명확하므로 `pending`을 유지해 재실행을 차단한다. 운영자가 체결
  여부를 확인한 뒤 `reset_partial_exit(account_id, code)`를 명시적으로 호출해야 한다.
- 상태 파일을 지정하지 않아도 같은 엔진 인스턴스에서는 메모리 상태로 반복 실행을
  막는다. 새 포지션 캠페인을 자동 추정하지 않으며 reset 전에는 보수적으로 차단한다.
- 상태 파일의 `contains`, `reserve`, `confirm`, `release`는 `<state-file>.lock` OS 잠금
  안에서 최신 JSON을 다시 읽고 처리한다. 오래된 프로세스가 기존 예약을 덮어쓰지
  못하며 잠금 충돌·잠금 파일 오류는 provider와 주문 전에 fail-closed 처리한다.
- 이 잠금은 같은 호스트의 공유 파일시스템 범위다. 서버리스·다중 호스트에서는
  원자적 조건부 쓰기를 지원하는 외부 저장소나 분산 잠금이 필요하다.
