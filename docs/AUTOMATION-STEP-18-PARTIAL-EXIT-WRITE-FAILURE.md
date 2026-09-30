# STEP 18 — Partial-exit persistence fault injection

Production behavior is unchanged; new integration regressions exercise actual
atomic file replacement failures through the strategy engine and a fake manager.

- Reservation write failure prevents selling, removes the temporary file, and
  permits a subsequent healthy call to reserve and sell once.
- Confirmation write failure after a filled paper sell preserves the pending
  reservation. Temporary files are removed and the lock is released.
- A restarted engine sees the pending reservation and does not sell again.
  Operator reconciliation remains required before explicitly resetting a campaign.

## Verification

Full discovery: 167 tests passed, exit code 0.
Command: `.\.tmp-test-venv\Scripts\python.exe -m unittest discover -s tests`.
Only injected failures and fake paper managers were used; no live orders or APIs.

STEP 17 was already committed as 2723d20. Push failed with SEC_E_NO_CREDENTIALS;
the approval system rejected the outside-sandbox retry. STEP 18 remains local
and uncommitted.
