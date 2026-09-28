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

- STEP 08E offline smoke and focused daily-chart/optimizer regression pass 52 tests.
- Full discovery is currently blocked by CPython 3.14 NumPy/Pandas binaries in repository-local `.tmp-pydeps` while the runner is Python 3.11; no external package installation was performed.
- The offline demo runner preloads trusted numerical dependencies before installing process/network guards, preventing pandas platform initialization from being misclassified as demo execution.
- Fixture contract tests cover `ka10081`, `POST /api/dostk/chart`, continuation headers, normalized OHLCV rows, and fail-closed malformed responses.

## Remaining gates

1. Complete Gate 0: publish the rewritten refs with the guarded Windows bundle and verify all seven remote ref SHAs.
2. STEP 08E read-only Kiwoom smoke test is documented but blocked until an approved credential/network environment is available.
3. T8 deployment safety guide is documented; actual Vercel deployment and live-account transition remain disabled until separately approved and wired through a reviewed secret entrypoint.
4. ORB/BULL_FLAG daily optimization and data-driven portfolio recommendations remain explicitly unsupported.
