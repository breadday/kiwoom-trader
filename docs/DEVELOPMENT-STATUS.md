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
- Strategy decisions carry an explicit sell fraction: immediate exits sell the current remainder, while RESCUE/FACTOR partial exits sell 50% with odd quantities rounded up and latch only after a filled paper result.
- `api/strategy_execution_state.py`: optional atomic JSON persistence for pre-order partial-exit reservations and filled results, with explicit operator reset for a new campaign.
- Partial-exit state operations use a companion OS lock file and reload the latest JSON under lock, preventing stale local processes from reserving the same position.
- `api/daily.py`: bounded TTL/LRU daily-chart cache connected to `KiwoomAPI`.
- `api/request_throttle.py`: monotonic, thread-safe 0.21-second minimum interval for outbound broker requests.
- `api/strategy_optimizer.py`: daily-bar provider injection for RESCUE and FACTOR backtests.
- `api/index.py`: Vercel Python handler with environment-injected credentials and hard-coded paper mode.
- `api/scanner.py`: explicit-universe read-only scanner and bounded/stoppable result runner with no order dependency.
- `api/telegram_notifications.py`: environment-configured Telegram result sink for bounded MATCH/ERROR scan alerts, with secret-safe failures, in-process duplicate suppression, and optional atomic JSON state persistence.
- Durable Telegram alert state reloads under a companion OS lock and serializes duplicate checks, delivery, and persistence across local processes.
- `api/scan_entrypoint.py`: environment-validated, paper-only composition entrypoint for one read-only scan-and-notify cycle with an explicitly injected evaluator.
- `api/scan_scheduling.py`: bounded Telegram-only retry wrapper and non-blocking OS file lock for single-host scheduled scans.

## Verification

- Full discovery passes 177 tests with 121 subtests using the repository-local `.venv`; no credential values are printed or committed.
- The Vercel entrypoint regression verifies explicit secret injection, hard-coded paper mode, read-only output, and the supported `BaseHTTPRequestHandler` contract.
- Scan automation isolates provider/evaluator failures per symbol, validates daily bars before evaluation, and publishes result batches only through an injected sink.
- Request-throttle tests verify immediate first use, minimum-interval waits, backward-clock safety, invalid configuration rejection, concurrent-call serialization, and throttling before live balance network access.
- Scanner validation rejects non-finite OHLCV values before evaluator execution.
- Multi-account tests verify explicit paper configuration, missing/malformed/duplicate/unsupported account rejection, live-balance blocking, and absence of network or mock fallback in non-paper mode.
- Balance aggregation validates finite non-negative cash, six-digit codes, positive integer quantities, and finite positive prices while preserving account-specific positions for duplicate stock codes.
- Strategy-engine tests verify missing provider, missing strategy, and malformed market-data results fail before any paper sell call.
- Multi-symbol strategy execution preflights every evaluation before paper actions, preserves selected order, and rejects duplicate selected codes before provider access.
- Strategy-engine account-selection tests verify that stock-only execution rejects multi-account ambiguity before provider access or paper sells, while explicit account-and-stock execution targets only the requested account.
- Partial-exit tests verify half-quantity sizing, odd-share rounding, one-shot suppression after a filled result, retry after a failed result, and full liquidation of a later immediate-exit remainder.
- Durable partial-exit tests verify restart suppression, pending-before-order persistence, explicit failed-order release, uncertain-result retention, corrupt-state rejection, pre-order write failure, and explicit campaign reset.
- State-concurrency tests verify stale-store reload before reservation and fail-closed lock contention before provider access or paper sells.
- Telegram notification tests verify actionable-only delivery, no-network behavior for NO_MATCH batches, credential fail-closed behavior, secret-safe errors, the 4,000-character message boundary, duplicate suppression across process restarts, persisted reset after NO_MATCH, corrupt-state rejection, and retry after failed delivery.
- Telegram state-concurrency tests verify stale-sink reload before delivery and fail-closed lock contention before network access.
- Scan entrypoint tests verify environment parsing, explicit evaluator injection, hard-coded paper mode, pre-request rejection of unsafe APIs, and exactly one published cycle.
- Scheduling tests verify bounded retries for `TelegramDeliveryError` only, immediate propagation of non-retryable failures, lock conflict rejection before API construction, accurate lock-path I/O failures, and automatic lock reuse after release.
- The offline demo runner preloads trusted numerical dependencies before installing process/network guards, preventing pandas platform initialization from being misclassified as demo execution.
- Fixture contract tests cover `ka10081`, `POST /api/dostk/chart`, continuation headers, normalized OHLCV rows, and fail-closed malformed responses.

## Remaining gates

1. Complete Gate 0: publish the rewritten refs with the guarded Windows bundle and verify all seven remote ref SHAs.
2. STEP 08E paper read-only Kiwoom smoke test passed against `mockapi.kiwoom.com`; real endpoint/account validation remains disabled pending separate approval.
3. T8 entrypoint and deployment safety guide are implemented; paper-only Vercel production deployment and endpoint read-back are complete. Live-account transition remains disabled.
4. ORB/BULL_FLAG daily optimization and data-driven portfolio recommendations remain explicitly unsupported.
5. Telegram Production variables are registered; local secret-safe runtime verification delivered one MATCH and one ERROR through Telegram successfully. The paper-only Vercel deployment and read-back are complete.
6. A production scan evaluator remains gated on an explicitly approved, data-validated signal rule; the entrypoint intentionally has no invented default strategy.
7. Local processes can serialize duplicate-alert state with `KIWOOM_ALERT_STATE_FILE`; serverless/multi-instance deployment still requires an external durable store with concurrency control.
8. `KIWOOM_SCAN_LOCK_FILE` prevents overlapping runs on one host only; multi-instance deployment requires a distributed lock.
9. The optional partial-exit state file supports same-host multi-process serialization and remains intentionally conservative: new campaigns require explicit reset. Multi-host execution requires a distributed store/lock, and automatic campaign rollover requires a broker-supplied stable position identity.
