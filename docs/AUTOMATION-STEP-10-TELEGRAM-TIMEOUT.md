# STEP 10 — Telegram timeout validation

## Scope

Reject non-finite Telegram request timeouts during configuration, before transport
construction or delivery. Existing scheduling and throttle settings already check
finite numeric values; TelegramConfig omitted this check.

## Verification

- RED: the new invalid-timeout regression failed for NaN and positive infinity.
- GREEN: finite positive integers and floats remain accepted and reach the injected
  transport; NaN, infinities, zero, negative values, booleans, strings and None are rejected.
- `.\.tmp-test-venv\Scripts\python.exe -m unittest discover -s tests`:
  153 tests passed (exit code 0).
- `git diff --check`: passed.

No live broker request, real order, or Telegram delivery was performed. Tests use
an injected fake transport. Commit and push are deferred; changes remain local.
