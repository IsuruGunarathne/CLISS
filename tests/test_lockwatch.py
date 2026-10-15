import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Animations", "lib")
WRITE_OK = "sh -c 'printf jpeg > \"$1\"' sh {out}"


def run_watchdog(camera, photo=True):
    """Run lockwatch on a short-lived process; return the dry-run log lines and the photo dir."""
    tmp = tempfile.mkdtemp()
    log, photos = os.path.join(tmp, "log"), os.path.join(tmp, "photos")
    target = subprocess.Popen(["sleep", "1.5"])
    threading.Thread(target=target.wait).start()   # reap it, so it doesn't linger as a zombie
    env = dict(os.environ, CLISS_LOCK_DRYRUN=log, CLISS_PHOTO_DIR=photos, CLISS_CAMERA_CMD=camera)
    args = [sys.executable, os.path.join(LIB, "lockwatch.py"), str(target.pid)]
    subprocess.run(args + (["--photo"] if photo else []), env=env, timeout=20)
    with open(log) as f:
        return f.read().splitlines(), photos


class LockwatchTest(unittest.TestCase):
    def test_photo_then_lock_on_exit(self):
        lines, photos = run_watchdog(WRITE_OK)
        self.assertIn("locked: exit", lines)
        photo = [l for l in lines if l.startswith("photo: ")]
        self.assertEqual(len(photo), 1)
        self.assertTrue(os.path.isfile(photo[0][len("photo: "):]))

    def test_no_photo_without_flag(self):
        lines, photos = run_watchdog(WRITE_OK, photo=False)
        self.assertEqual(lines, ["locked: exit"])
        self.assertFalse(os.path.exists(photos))

    def test_lock_still_happens_when_photo_fails(self):
        lines, photos = run_watchdog("false {out}")
        self.assertEqual(lines, ["locked: exit"])


if __name__ == "__main__":
    unittest.main()
