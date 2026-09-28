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

- 43 focused order, strategy, daily-chart, and optimizer tests pass.
- Full discovery passes all 68 tests with the approved Python 3.11 dependency target.
- The offline demo runner preloads trusted numerical dependencies before installing process/network guards, preventing pandas platform initialization from being misclassified as demo execution.
- Fixture contract tests cover `ka10081`, `POST /api/dostk/chart`, continuation headers, normalized OHLCV rows, and fail-closed malformed responses.

## Remaining gates

1. Run a read-only Kiwoom market-data smoke test only after explicit credential/network approval.
2. Keep T8 deployment and live-account transition disabled until separately approved.
3. ORB/BULL_FLAG daily optimization and data-driven portfolio recommendations remain explicitly unsupported.
