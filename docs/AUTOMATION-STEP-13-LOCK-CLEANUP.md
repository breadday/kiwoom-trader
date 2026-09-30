# STEP 13 — Lock initialization cleanup

FileRunLock now closes an opened file if seek, tell, write, or flush fails during
initialization. Cleanup errors do not replace the existing initialization error.
The failed instance remains available for retry.

## Verification

- RED: all four injected initialization failures left the handle unclosed.
- GREEN: each failure closes the handle without attempting an OS lock; the same
  instance subsequently acquires and releases a real temporary lock successfully.
- Full discovery: 159 tests passed, exit code 0.
- Command: `.\.tmp-test-venv\Scripts\python.exe -m unittest discover -s tests`.

No real broker or Telegram request was made. STEP 12 is committed as 5116a98,
but its push failed with SEC_E_NO_CREDENTIALS and the approval system rejected
the outside-sandbox retry. STEP 13 remains local and uncommitted.
