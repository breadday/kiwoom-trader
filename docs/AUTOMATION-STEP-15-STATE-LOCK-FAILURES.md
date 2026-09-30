# STEP 15 — State lock failure boundaries

Telegram and partial-exit state wrappers now report that their lock could not be
acquired, rather than incorrectly identifying every acquisition failure as a file
open failure. Existing dedicated contention exceptions remain unchanged.

## Verification

- RED: both new regressions reproduced the misleading diagnostic.
- GREEN: injected acquisition failures stop before Telegram transport, market-data
  provider access, paper sell calls, and state-file creation.
- Full discovery: 162 tests passed, exit code 0.
- Command: `.\.tmp-test-venv\Scripts\python.exe -m unittest discover -s tests`.

No real broker or Telegram requests were made. STEP 14 was already committed as
2617e85. Push failed with SEC_E_NO_CREDENTIALS; the approval system rejected the
outside-sandbox retry. STEP 15 remains local and uncommitted.
