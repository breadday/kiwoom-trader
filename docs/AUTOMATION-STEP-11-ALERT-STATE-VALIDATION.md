# STEP 11 — Alert state validation

## Change

Validate the entire persisted alert fingerprint, not only its status and reason.
Reject malformed status types, invalid calendar dates, non-finite or non-positive
prices, and non-numeric or negative volumes. Optional market fields remain valid;
zero volume is accepted. Apply the same validation to incoming ScanItem values
before acquiring state locks, delivering alerts, or changing persisted state.

## Verification

- RED: malformed persisted fingerprints produced seven failed assertions and one
  unexpected TypeError in the new regression.
- GREEN: invalid state is rejected with ValueError; invalid input never reaches
  transport or creates the state file.
- A restart regression preserves duplicate suppression for zero volume and ERROR
  items without market fields.
- `.\.tmp-test-venv\Scripts\python.exe -m unittest discover -s tests`:
  156 tests passed, exit code 0.

All delivery tests used injected transports. No real Telegram request, broker
request, or order was performed. Commit and push remain deferred to the user.
