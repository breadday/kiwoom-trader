import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from api.scan_scheduling import (
    FileRunLock,
    RetryingResultSink,
    ScanAlreadyRunningError,
)


class RetryingResultSinkTests(unittest.TestCase):
    def test_retries_only_configured_exception_with_bounded_waits(self):
        attempts = []
        waits = []

        def sink(batch):
            attempts.append(batch)
            if len(attempts) < 3:
                raise ConnectionError("temporary")
            return "sent"

        retrying = RetryingResultSink(
            sink,
            max_attempts=3,
            retry_seconds=2,
            retry_exceptions=(ConnectionError,),
            sleeper=waits.append,
        )

        self.assertEqual(retrying(["batch"]), "sent")
        self.assertEqual(len(attempts), 3)
        self.assertEqual(waits, [2.0, 2.0])

    def test_unconfigured_exception_is_not_retried(self):
        attempts = []

        def sink(_batch):
            attempts.append(True)
            raise RuntimeError("state persistence failed")

        retrying = RetryingResultSink(
            sink,
            max_attempts=3,
            retry_seconds=2,
            retry_exceptions=(ConnectionError,),
            sleeper=lambda _seconds: self.fail("must not wait"),
        )

        with self.assertRaisesRegex(RuntimeError, "state persistence"):
            retrying([])
        self.assertEqual(len(attempts), 1)


class FileRunLockTests(unittest.TestCase):
    def test_second_holder_is_rejected_until_first_releases(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "scan.lock"
            first = FileRunLock(path)
            second = FileRunLock(path)

            with first:
                with self.assertRaises(ScanAlreadyRunningError):
                    second.acquire()

            with second:
                self.assertTrue(path.exists())

    def test_unusable_lock_path_is_not_reported_as_contention(self):
        with TemporaryDirectory() as directory:
            parent_file = Path(directory) / "not-a-directory"
            parent_file.write_text("occupied", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "could not be opened"):
                FileRunLock(parent_file / "scan.lock").acquire()


if __name__ == "__main__":
    unittest.main()
