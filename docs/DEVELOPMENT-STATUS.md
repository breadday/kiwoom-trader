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

## Verification

- Full unittest discovery passes all 76 order, strategy, daily-chart, optimizer, and privacy tests when run with the repository-local `.tmp-pydeps` path.
- The repository-local offline dependency path provides `pandas 3.0.6` and `numpy 2.4.6`; no package installation outside the repository was used.
- The offline demo runner preloads trusted numerical dependencies before installing process/network guards, preventing pandas platform initialization from being misclassified as demo execution.
- Fixture contract tests cover `ka10081`, `POST /api/dostk/chart`, continuation headers, normalized OHLCV rows, and fail-closed malformed responses.

## Remaining gates

1. Complete Gate 0: publish the rewritten refs with the guarded Windows bundle and verify all seven remote ref SHAs.
2. STEP 08E read-only Kiwoom smoke test is documented but blocked until an approved credential/network environment is available.
3. T8 deployment safety guide is documented; actual Vercel deployment and live-account transition remain disabled until separately approved and wired through a reviewed secret entrypoint.
4. ORB/BULL_FLAG daily optimization and data-driven portfolio recommendations remain explicitly unsupported.
