# Kiwoom Trader development status

## Scope and safety boundary

- Order behavior is limited to dry-run and paper/mock execution.
- `paper=False` order submission fails closed for the local executor and all broker adapters.
- No live order, account mutation, credential access, or authenticated broker request was used for this status.

## Completed implementation

- `order.py`: validated order domain objects and deterministic dry-run executor.
- `api/kiwoom_api.py`: paper buy/sell validation, insufficient-balance rejection, and live-order blocking.
- `api/multi_broker_api.py`: non-paper order and live-balance blocking for all adapters, plus fail-closed explicit account configuration.
- `api/strategy_engine.py`: `run_single` and `run_selected` execution paths.
- Strategy execution requires an explicit per-stock strategy and caller-supplied market-data mapping; synthetic signal fallback is disabled.
- Stock-only execution rejects positions held in multiple accounts; `run_account_position` requires an explicit account and stock pair.
- `api/daily.py`: bounded TTL/LRU daily-chart cache connected to `KiwoomAPI`.
- `api/request_throttle.py`: monotonic, thread-safe 0.21-second minimum interval for outbound broker requests.
- `api/strategy_optimizer.py`: daily-bar provider injection for RESCUE and FACTOR backtests.
- `api/index.py`: Vercel Python handler with environment-injected credentials and hard-coded paper mode.
- `api/scanner.py`: explicit-universe read-only scanner and bounded/stoppable result runner with no order dependency.
- `api/telegram_notifications.py`: environment-configured Telegram result sink for bounded MATCH/ERROR scan alerts, with secret-safe failures, in-process duplicate suppression, and optional atomic JSON state persistence.
- `api/scan_entrypoint.py`: environment-validated, paper-only composition entrypoint for one read-only scan-and-notify cycle with an explicitly injected evaluator.
- `api/scan_scheduling.py`: bounded Telegram-only retry wrapper and non-blocking OS file lock for single-host scheduled scans.

## Verification

- Full discovery passes 136 tests with CPython 3.14.7 and the matching repository-local `.tmp-pydeps`; no external package installation was performed.
- The Vercel entrypoint regression verifies explicit secret injection, hard-coded paper mode, read-only output, and the supported `BaseHTTPRequestHandler` contract.
- Scan automation isolates provider/evaluator failures per symbol, validates daily bars before evaluation, and publishes result batches only through an injected sink.
- Request-throttle tests verify immediate first use, minimum-interval waits, backward-clock safety, invalid configuration rejection, concurrent-call serialization, and throttling before live balance network access.
- Scanner validation rejects non-finite OHLCV values before evaluator execution.
- Multi-account tests verify explicit paper configuration, missing/malformed/duplicate/unsupported account rejection, live-balance blocking, and absence of network or mock fallback in non-paper mode.
- Balance aggregation validates finite non-negative cash, six-digit codes, positive integer quantities, and finite positive prices while preserving account-specific positions for duplicate stock codes.
- Strategy-engine tests verify missing provider, missing strategy, and malformed market-data results fail before any paper sell call.
- Multi-symbol strategy execution preflights every evaluation before paper actions, preserves selected order, and rejects duplicate selected codes before provider access.
- Strategy-engine account-selection tests verify that stock-only execution rejects multi-account ambiguity before provider access or paper sells, while explicit account-and-stock execution targets only the requested account.
- Telegram notification tests verify actionable-only delivery, no-network behavior for NO_MATCH batches, credential fail-closed behavior, secret-safe errors, the 4,000-character message boundary, duplicate suppression across process restarts, persisted reset after NO_MATCH, corrupt-state rejection, and retry after failed delivery.
- Scan entrypoint tests verify environment parsing, explicit evaluator injection, hard-coded paper mode, pre-request rejection of unsafe APIs, and exactly one published cycle.
- Scheduling tests verify bounded retries for `TelegramDeliveryError` only, immediate propagation of non-retryable failures, lock conflict rejection before API construction, accurate lock-path I/O failures, and automatic lock reuse after release.
- The offline demo runner preloads trusted numerical dependencies before installing process/network guards, preventing pandas platform initialization from being misclassified as demo execution.
- Fixture contract tests cover `ka10081`, `POST /api/dostk/chart`, continuation headers, normalized OHLCV rows, and fail-closed malformed responses.

## Remaining gates

1. Complete Gate 0: publish the rewritten refs with the guarded Windows bundle and verify all seven remote ref SHAs.
2. STEP 08E read-only Kiwoom smoke test is documented but blocked until an approved credential/network environment is available.
3. T8 entrypoint and deployment safety guide are implemented; actual Vercel deployment is blocked on CLI network approval, authentication, project linking, and secret registration. Live-account transition remains disabled.
4. ORB/BULL_FLAG daily optimization and data-driven portfolio recommendations remain explicitly unsupported.
5. Live Telegram delivery remains gated on approved network access and operator-provided `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`; tests use an injected offline transport.
6. A production scan evaluator remains gated on an explicitly approved, data-validated signal rule; the entrypoint intentionally has no invented default strategy.
7. Local single-scheduler runs can persist duplicate-alert state with `KIWOOM_ALERT_STATE_FILE`; serverless/multi-instance deployment still requires an external durable store with concurrency control.
8. `KIWOOM_SCAN_LOCK_FILE` prevents overlapping runs on one host only; multi-instance deployment requires a distributed lock.
