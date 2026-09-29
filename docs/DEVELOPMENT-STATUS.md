# Kiwoom Trader development status

## Scope and safety boundary

- Order behavior is limited to dry-run and paper/mock execution.
- `paper=False` order submission fails closed for the local executor and all broker adapters.
- No live order, account mutation, credential access, or authenticated broker request was used for this status.

## Completed implementation

- `order.py`: validated order domain objects and deterministic dry-run executor.
- `api/kiwoom_api.py`: paper buy/sell validation, insufficient-balance rejection, and live-order blocking.
- `api/multi_broker_api.py`: non-paper order blocking for NH, Samsung, and KB adapters.
- `api/strategy_engine.py`: `run_single` and `run_selected` execution paths.
- `api/daily.py`: bounded TTL/LRU daily-chart cache connected to `KiwoomAPI`.
- `api/strategy_optimizer.py`: daily-bar provider injection for RESCUE and FACTOR backtests.
- `api/index.py`: Vercel Python handler with environment-injected credentials and hard-coded paper mode.
- `api/scanner.py`: explicit-universe read-only scanner and bounded/stoppable result runner with no order dependency.
- `api/telegram_notifications.py`: environment-configured Telegram result sink for bounded MATCH/ERROR scan alerts, with secret-safe failures.
- `api/scan_entrypoint.py`: environment-validated, paper-only composition entrypoint for one read-only scan-and-notify cycle with an explicitly injected evaluator.

## Verification

- Full discovery passes 97 tests with CPython 3.14.7 and the matching repository-local `.tmp-pydeps`; no external package installation was performed.
- The Vercel entrypoint regression verifies explicit secret injection, hard-coded paper mode, read-only output, and the supported `BaseHTTPRequestHandler` contract.
- Scan automation isolates provider/evaluator failures per symbol, validates daily bars before evaluation, and publishes result batches only through an injected sink.
- Telegram notification tests verify actionable-only delivery, no-network behavior for NO_MATCH batches, credential fail-closed behavior, secret-safe errors, and the 4,000-character message boundary.
- Scan entrypoint tests verify environment parsing, explicit evaluator injection, hard-coded paper mode, pre-request rejection of unsafe APIs, and exactly one published cycle.
- The offline demo runner preloads trusted numerical dependencies before installing process/network guards, preventing pandas platform initialization from being misclassified as demo execution.
- Fixture contract tests cover `ka10081`, `POST /api/dostk/chart`, continuation headers, normalized OHLCV rows, and fail-closed malformed responses.

## Remaining gates

1. Complete Gate 0: publish the rewritten refs with the guarded Windows bundle and verify all seven remote ref SHAs.
2. STEP 08E read-only Kiwoom smoke test is documented but blocked until an approved credential/network environment is available.
3. T8 entrypoint and deployment safety guide are implemented; actual Vercel deployment is blocked on CLI network approval, authentication, project linking, and secret registration. Live-account transition remains disabled.
4. ORB/BULL_FLAG daily optimization and data-driven portfolio recommendations remain explicitly unsupported.
5. Live Telegram delivery remains gated on approved network access and operator-provided `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`; tests use an injected offline transport.
6. A production scan evaluator remains gated on an explicitly approved, data-validated signal rule; the entrypoint intentionally has no invented default strategy.
