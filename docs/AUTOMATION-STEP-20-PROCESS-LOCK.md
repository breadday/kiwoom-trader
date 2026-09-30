# STEP 20 — Real process lock regression

Production code is unchanged. New tests launch a separate Python interpreter
using sys.executable, with bounded subprocess timeouts and temporary lock files.

- A child process reports contention while the parent holds the lock, then
  acquires the same file after the parent releases it.
- A child acquires the lock and exits via os._exit(17), bypassing Python cleanup.
  The parent verifies the exit status and reacquires the OS-released lock.

## Verification

Full discovery on the current Windows environment: 171 tests passed, exit code 0.
Command: `.\.tmp-test-venv\Scripts\python.exe -m unittest discover -s tests`.
No broker or Telegram request was performed. Linux execution is not claimed.

STEP 19 was already committed as 41b3816. Push failed with SEC_E_NO_CREDENTIALS;
the approval system rejected the outside-sandbox retry. STEP 20 remains local
and uncommitted.
