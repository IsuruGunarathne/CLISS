import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Animations", "lib"))
import lockwatch  # noqa: E402

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Animations", "lib")
BURST = "sh -c 'for i in $(seq 1 \"$2\"); do printf jpeg > \"$1/0$i.jpg\"; done' sh {dir} {count}"
SLOW_BURST = "sh -c 'for i in $(seq 1 \"$2\"); do printf jpeg > \"$1/0$i.jpg\"; done; sleep 3' sh {dir} {count}"


def run_keyed(camera, disarm):
    """Signal lockwatch the way the screensaver does with a PIN; return its log, photo dir and run time."""
    tmp = tempfile.mkdtemp()
    log, photos = os.path.join(tmp, "log"), os.path.join(tmp, "photos")
    target = subprocess.Popen(["sleep", "20"])
    env = dict(os.environ, CLISS_LOCK_DRYRUN=log, CLISS_PHOTO_DIR=photos, CLISS_CAMERA_CMD=camera)
    watch = subprocess.Popen([sys.executable, os.path.join(LIB, "lockwatch.py"), str(target.pid), "--sentry"],
                             env=env)
    try:
        time.sleep(1.5)
        start = time.time()
        watch.send_signal(signal.SIGUSR1)                # a key ended the screensaver
        if disarm:
            time.sleep(0.5)
            watch.send_signal(signal.SIGUSR2)            # ...and the right PIN followed
        watch.wait(30)
        took = time.time() - start
    finally:
        target.kill()
        target.wait()
    with open(log) as f:
        return f.read().splitlines(), photos, took


def run_watchdog(camera, sentry=True):
    """Run lockwatch on a short-lived process; return its dry-run log lines, photo dir and run time."""
    tmp = tempfile.mkdtemp()
    log, photos = os.path.join(tmp, "log"), os.path.join(tmp, "photos")
    target = subprocess.Popen(["sleep", "1.5"])
    threading.Thread(target=target.wait).start()   # reap it, so it doesn't linger as a zombie
    env = dict(os.environ, CLISS_LOCK_DRYRUN=log, CLISS_PHOTO_DIR=photos, CLISS_CAMERA_CMD=camera)
    args = [sys.executable, os.path.join(LIB, "lockwatch.py"), str(target.pid)]
    start = time.time()
    subprocess.run(args + (["--sentry"] if sentry else []), env=env, timeout=30)
    with open(log) as f:
        return f.read().splitlines(), photos, time.time() - start


class LockwatchTest(unittest.TestCase):
    def test_burst_then_lock_on_exit(self):
        lines, photos, took = run_watchdog(SLOW_BURST)    # still recording at lock time, like a real camera
        self.assertEqual(lines[0], "locked: exit")
        self.assertTrue(lines[1].startswith("photos: 9 in "), lines)
        folder = lines[1].split(" in ", 1)[1]
        self.assertEqual(len(os.listdir(folder)), 9)
        self.assertGreater(took, 1.5 + 2.5)          # it waited before locking

    def test_no_photos_without_flag(self):
        lines, photos, took = run_watchdog(BURST, sentry=False)
        self.assertEqual(lines, ["locked: exit"])
        self.assertFalse(os.path.exists(photos))

    def test_locks_straight_away_without_a_camera(self):
        lines, photos, took = run_watchdog("/nonexistent/camera {dir}")
        self.assertEqual(lines, ["locked: exit"])
        self.assertLess(took, 1.5 + 2.0)             # no 2.5s wait when there's no camera

    def test_locks_straight_away_when_the_camera_gives_up(self):
        lines, photos, took = run_watchdog("sh -c 'exit 1'")
        self.assertEqual(lines, ["locked: exit"])
        self.assertLess(took, 1.5 + 2.0)             # didn't sit out the 2.5s

    def test_key_signal_starts_the_burst(self):
        lines, photos, took = run_keyed(SLOW_BURST, disarm=False)
        self.assertEqual(lines[0], "locked: exit")
        self.assertTrue(lines[1].startswith("photos: 9 in "), lines)

    def test_disarm_throws_the_burst_away(self):
        lines, photos, took = run_keyed(SLOW_BURST, disarm=True)
        self.assertEqual(lines, ["locked: exit", "disarmed"])
        self.assertEqual(os.listdir(photos), [])
        self.assertLess(took, 2.5)                   # locked as soon as it was disarmed

    def test_survives_a_signal_before_its_handlers(self):
        # the launcher starts it with these ignored; a key that early mustn't kill it
        tmp = tempfile.mkdtemp()
        log = os.path.join(tmp, "log")
        target = subprocess.Popen(["sleep", "1.5"])
        threading.Thread(target=target.wait).start()

        def ignore():
            signal.signal(signal.SIGUSR1, signal.SIG_IGN)
            signal.signal(signal.SIGUSR2, signal.SIG_IGN)
        watch = subprocess.Popen([sys.executable, os.path.join(LIB, "lockwatch.py"), str(target.pid)],
                                 env=dict(os.environ, CLISS_LOCK_DRYRUN=log), preexec_fn=ignore)
        watch.send_signal(signal.SIGUSR1)            # straight away, before python is even up
        self.assertEqual(watch.wait(30), 0)
        with open(log) as f:
            self.assertEqual(f.read(), "locked: exit\n")


class CaughtTest(unittest.TestCase):
    """caught() itself, with the PIN's signals simulated by setting the flags."""

    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.log, self.photos = os.path.join(tmp, "log"), os.path.join(tmp, "photos")
        self.patches = [mock.patch.object(lockwatch, "DRY", self.log),
                        mock.patch.object(lockwatch, "SENTRY", True),
                        mock.patch.object(lockwatch, "keyed", False),
                        mock.patch.object(lockwatch, "disarmed", False),
                        mock.patch.dict(os.environ, CLISS_PHOTO_DIR=self.photos)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()

    def caught(self, reason, camera, disarm_after):
        lockwatch.keyed = reason == "exit"
        timer = threading.Timer(disarm_after, setattr, (lockwatch, "disarmed", True))
        timer.start()
        with mock.patch.dict(os.environ, CLISS_CAMERA_CMD=camera):
            lockwatch.caught(reason)
        timer.cancel()
        with open(self.log) as f:
            return f.read().splitlines()

    def test_pin_cant_disarm_an_app_switch(self):
        lines = self.caught("focus", SLOW_BURST, 0.5)
        self.assertEqual(lines[0], "locked: focus")
        self.assertTrue(lines[1].startswith("photos: 9 in "), lines)

    def test_late_pin_still_disarms_a_finished_burst(self):
        lines = self.caught("exit", BURST, 1.5)      # camera done at once, PIN in 1.5s later
        self.assertEqual(lines, ["locked: exit", "disarmed"])
        self.assertEqual(os.listdir(self.photos), [])

    def test_no_pin_keeps_the_photos(self):
        lines = self.caught("exit", BURST, 60)
        self.assertTrue(lines[1].startswith("photos: 9 in "), lines)


if __name__ == "__main__":
    unittest.main()
