# AUTOMATION STEP 09 — Telegram alert-state lock

## Scope

- Serialize durable Telegram duplicate-state access across processes on one host.
- Reload the latest state after acquiring the lock so a stale sink cannot resend an alert already delivered by another process.
- Fail closed before network access when another process holds the state lock.
- Keep live broker, account, order, and real Telegram delivery outside this stage.

## Files

- `api/telegram_notifications.py`
- `tests/test_telegram_notifications.py`
- `docs/AUTOMATION.md`
- `docs/DEVELOPMENT-STATUS.md`

## RED → GREEN

1. RED: the new test module import failed because `TelegramStateBusyError` did not exist.
2. GREEN: `<state-file>.lock` now covers latest-state reload, duplicate evaluation, injected transport delivery, and atomic state persistence.
3. GREEN: two sink instances created from the same old snapshot produce one network call, and explicit lock contention raises before the transport is called.

## Verification matrix

| Check | Result |
|---|---|
| Two focused concurrency tests | PASS — 2 tests |
| Telegram notification regression | PASS — 15 tests |
| All tests not requiring NumPy/Pandas native extensions | PASS — 144 tests |
| Full discovery | PASS — CPython 3.11 project venv | 177 tests, 121 subtests |
| `python -m compileall -q api tests` | PASS |

The repository currently contains 177 passing tests with 121 subtests under the CPython 3.11 project venv. The privacy/demo tests now target `automation/kiwoom_rescue_demo.py`, a synthetic-data-only script; no legacy account-like path is restored.

## Safety boundary

- The lock is non-blocking and local to a shared filesystem on one host.
- The lock intentionally spans the Telegram request so two local processes cannot both pass the duplicate check before either persists success.
- A failed or indeterminate Telegram request is not recorded as delivered and remains eligible for a later scheduled retry.
- Multi-host or serverless execution still requires an external durable store with an atomic conditional update or a distributed lock.
- Tests use an injected offline transport; no credential, broker API, account mutation, order, or real Telegram request was used.
