import unittest
from threading import Barrier, Thread

from api.request_throttle import RequestThrottle


class RequestThrottleTests(unittest.TestCase):
    def test_first_request_is_immediate_and_next_request_waits_for_interval(self):
        now = [100.0]
        waits = []

        def sleep(seconds):
            waits.append(seconds)
            now[0] += seconds

        throttle = RequestThrottle(
            min_interval_seconds=0.21,
            clock=lambda: now[0],
            sleeper=sleep,
        )

        throttle.wait()
        now[0] += 0.05
        throttle.wait()

        self.assertEqual(len(waits), 1)
        self.assertAlmostEqual(waits[0], 0.16)

    def test_backward_clock_cannot_bypass_rate_limit(self):
        now = [100.0]
        waits = []

        def sleep(seconds):
            waits.append(seconds)
            now[0] += seconds

        throttle = RequestThrottle(
            min_interval_seconds=0.21,
            clock=lambda: now[0],
            sleeper=sleep,
        )
        throttle.wait()
        now[0] = 99.0

        throttle.wait()

        self.assertEqual(len(waits), 1)
        self.assertAlmostEqual(waits[0], 1.21)

    def test_invalid_interval_fails_closed(self):
        for interval in (True, 0, -1, float("nan"), float("inf")):
            with self.subTest(interval=interval), self.assertRaises(ValueError):
                RequestThrottle(interval)

    def test_concurrent_callers_are_serialized(self):
        now = [100.0]
        waits = []
        barrier = Barrier(3)

        def sleep(seconds):
            waits.append(seconds)
            now[0] += seconds

        throttle = RequestThrottle(
            min_interval_seconds=0.21,
            clock=lambda: now[0],
            sleeper=sleep,
        )

        def call_wait():
            barrier.wait()
            throttle.wait()

        threads = [Thread(target=call_wait) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(timeout=1)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(len(waits), 1)
        self.assertAlmostEqual(waits[0], 0.21)


if __name__ == "__main__":
    unittest.main()
