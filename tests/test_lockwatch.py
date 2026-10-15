import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Animations", "lib")
BURST = "sh -c 'for i in $(seq 1 \"$2\"); do printf jpeg > \"$1/0$i.jpg\"; done' sh {dir} {count}"
SLOW_BURST = "sh -c 'for i in $(seq 1 \"$2\"); do printf jpeg > \"$1/0$i.jpg\"; done; sleep 3' sh {dir} {count}"


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


if __name__ == "__main__":
    unittest.main()
