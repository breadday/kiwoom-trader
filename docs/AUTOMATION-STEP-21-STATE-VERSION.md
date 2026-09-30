# STEP 21 — Strict persisted state versions

Both Telegram alert state and partial-exit state now require an integer version
equal to 1. Python equality previously allowed JSON true and 1.0 to masquerade
as version 1. Existing files written by these modules remain compatible.

## Verification

- RED: both loaders accepted true and 1.0 (four failing subtests).
- GREEN: booleans, floats, strings, null, and unsupported integers are rejected;
  valid integer version 1 loads successfully in both modules.
- Full discovery: 173 tests passed, exit code 0.
- Command: `.\.tmp-test-venv\Scripts\python.exe -m unittest discover -s tests`.

No real API calls or orders. Changes remain local and uncommitted; no push was
requested or attempted in this stage.
