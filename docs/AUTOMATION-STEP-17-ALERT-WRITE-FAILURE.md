# STEP 17 — Alert persistence failure regression

This stage adds fault-injection coverage; production behavior is unchanged.

## Verified behavior

- Failure replacing state after accepted delivery propagates RuntimeError and is
  not immediately retried by the TelegramDeliveryError-only retry wrapper.
- The previous state file remains byte-for-byte intact, temporary files are
  cleaned, and the state lock is released.
- A failure saving NO_MATCH state prevents actionable delivery in the same batch.
  A subsequent healthy call can persist that state.
- A restart after accepted delivery but failed persistence can resend the alert.
  This is an explicit duplicate-delivery window, not an exactly-once guarantee.
  The later successful persistence restores duplicate suppression.

## Verification

Injected os.replace failures and fake transports only; no live API calls.
Full discovery: 165 tests passed, exit code 0, using
`.\.tmp-test-venv\Scripts\python.exe -m unittest discover -s tests`.

STEP 16 was already committed as 1893907. Push failed with
SEC_E_NO_CREDENTIALS and the approval system rejected the outside-sandbox retry.
STEP 17 tests and this report remain local and uncommitted.
