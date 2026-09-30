# STEP 16 — Unique alert batch codes

Reject repeated stock codes in one Telegram result batch before locking,
delivery, or state mutation. The scanner already uses a unique universe; direct
sink callers now receive a clear error instead of ambiguous per-stock updates.

## Verification

- RED: six duplicate scenarios were accepted (identical MATCH and conflicting
  NO_MATCH/ERROR, with in-memory and file-backed state).
- GREEN: all are rejected; transport calls and persisted bytes remain unchanged,
  and the previously recorded match remains suppressed.
- Full unittest discovery: 163 tests passed, exit code 0.
- Command: `.\.tmp-test-venv\Scripts\python.exe -m unittest discover -s tests`.

No real broker request, order, or Telegram delivery occurred. STEP 15 was already
committed as a827dbb; push failed with SEC_E_NO_CREDENTIALS and the approval
system rejected the outside-sandbox retry. STEP 16 remains local and uncommitted.
