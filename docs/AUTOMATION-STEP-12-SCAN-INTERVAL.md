# STEP 12 — Scan interval validation

ScanRunner now rejects non-finite intervals before scanning or publishing.
Previously NaN and positive infinity passed constructor validation and could
reach Event.wait. Finite positive fractional intervals remain supported.

## Verification

- RED: new regression failed for NaN and positive infinity.
- GREEN: invalid intervals fail at construction; a fractional interval reaches
  the injected wait and a stop signal prevents the second cycle.
- Full discovery: 158 tests passed, exit code 0.
- Command: `.\.tmp-test-venv\Scripts\python.exe -m unittest discover -s tests`.

No real network delivery or orders were performed.
STEP 11 was already committed as 99e0265. Its push failed with Windows
SEC_E_NO_CREDENTIALS; the outside-sandbox retry was rejected by the approval
system. STEP 12 changes remain local for review and publication.
