import os
import signal
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Animations", "lib"))
import clissfx  # noqa: E402
import lockpin  # noqa: E402


class LockpinTest(unittest.TestCase):
    def test_spec_matches_only_its_pin(self):
        value = lockpin.spec(b"1234")
        self.assertNotIn("1234", value)
        self.assertTrue(lockpin.matches(b"1234", value))
        self.assertFalse(lockpin.matches(b"1235", value))
        self.assertFalse(lockpin.matches(b"", value))

    def test_salted(self):
        self.assertNotEqual(lockpin.spec(b"1234"), lockpin.spec(b"1234"))

    def test_bad_value_never_matches(self):
        for value in ("", "nonsense", "zz:abc", "a:b:c"):
            self.assertFalse(lockpin.matches(b"1234", value), value)

    def test_entry(self):
        self.assertEqual(lockpin.entry(b"1234\n"), b"1234")
        self.assertEqual(lockpin.entry(b"1234\r"), b"1234")
        self.assertEqual(lockpin.entry(b"125\x7f34\n"), b"1234")
        self.assertEqual(lockpin.entry(b"\x7f\x7f12\n9"), b"12")


class ReadPinTest(unittest.TestCase):
    """clissfx._read_pin, with ourselves standing in for the watchdog."""

    def setUp(self):
        self.got = []
        self.old = [signal.signal(s, lambda n, _: self.got.append(n))
                    for s in (signal.SIGUSR1, signal.SIGUSR2)]
        self.r, self.w = os.pipe()
        self.value = lockpin.spec(b"1234")

    def tearDown(self):
        signal.signal(signal.SIGUSR1, self.old[0])
        signal.signal(signal.SIGUSR2, self.old[1])
        os.close(self.r)
        os.close(self.w)

    def read_pin(self, first, rest):
        os.write(self.w, rest)
        start = time.monotonic()
        clissfx._read_pin(self.r, first, os.getpid(), self.value)
        return time.monotonic() - start

    def test_right_pin_disarms(self):
        self.read_pin(b"1", b"234\n")
        self.assertEqual(self.got, [signal.SIGUSR1, signal.SIGUSR2])

    def test_wrong_pin_only_triggers(self):
        self.read_pin(b"1", b"235\n")
        self.assertEqual(self.got, [signal.SIGUSR1])

    def test_no_enter_gives_up_after_the_window(self):
        took = self.read_pin(b"1", b"234")
        self.assertEqual(self.got, [signal.SIGUSR1])
        self.assertGreaterEqual(took, lockpin.WINDOW - 0.1)


if __name__ == "__main__":
    unittest.main()
