# STEP 19 — Reservation release and reset failures

Production code is unchanged. Fault-injection integration tests verify:

- After an explicit paper rejection, a failed reservation-release write leaves
  the pending record intact. A restarted engine blocks another sell until an
  explicit successful reset; after reset a healthy paper sell is possible.
- A failed explicit reset preserves the filled record byte-for-byte and prevents
  another sell on the same engine. Temporary files are removed and locks released.

## Verification

Full discovery: 169 tests passed, exit code 0.
Command: `.\.tmp-test-venv\Scripts\python.exe -m unittest discover -s tests`.
Tests used fake managers and injected disk failures; no live orders or API calls.

STEP 18 was already committed as 4396776. Push failed with SEC_E_NO_CREDENTIALS;
the approval system rejected the outside-sandbox retry. STEP 19 remains local
and uncommitted.
