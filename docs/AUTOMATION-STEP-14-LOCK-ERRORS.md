# STEP 14 — OS lock error classification

FileRunLock distinguishes contention errors (EACCES, EAGAIN, EDEADLK) from other
OS acquisition failures. Other failures raise RuntimeError instead of incorrectly
claiming another scan is running. Failed acquisition closes the file and leaves
the instance reusable. Cleanup OSError does not mask the acquisition error.

## Verification

- RED: injected EBADF and EIO were incorrectly classified as contention.
- GREEN: contention and I/O cases produce the expected exception types, close
  their handles, and permit subsequent real temporary-file acquisition.
- Full unittest discovery: 160 tests passed, exit code 0.
- Command: `.\.tmp-test-venv\Scripts\python.exe -m unittest discover -s tests`.

No broker request, real order or Telegram delivery was performed.
STEP 13 was already committed as d879b69; its push failed with Windows
SEC_E_NO_CREDENTIALS and the approval system rejected an outside-sandbox retry.
STEP 14 remains local and uncommitted.
