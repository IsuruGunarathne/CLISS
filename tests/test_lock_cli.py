import os
import pty
import select
import subprocess
import tempfile
import time
import unittest

CLISS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cliss")
WRITE_OK = "sh -c 'printf jpeg > \"$1\"' sh {out}"


def run(args, camera, key_after=2.0):
    """Run cliss in a pty, press a key, return (exit status, output, dry-run log path, photo dir)."""
    tmp = tempfile.mkdtemp()
    log, photos = os.path.join(tmp, "log"), os.path.join(tmp, "photos")
    env = dict(os.environ, TERM="xterm-256color", CLISS_LOCK_DRYRUN=log,
               CLISS_PHOTO_DIR=photos, CLISS_CAMERA_CMD=camera)
    pid, fd = pty.fork()
    if pid == 0:
        os.execvpe(CLISS, [CLISS] + args, env)
    out, start, sent = b"", time.time(), False
    while time.time() - start < 15:
        if not sent and time.time() - start > key_after:
            sent = True
            try:
                os.write(fd, b"x")
            except OSError:      # cliss already exited (the --check failure test)
                pass
        r, _, _ = select.select([fd], [], [], 0.05)
        if r:
            try:
                data = os.read(fd, 65536)
            except OSError:
                break
            if not data:
                break
            out += data
    _, status = os.waitpid(pid, 0)
    return status, out.decode("utf-8", "replace"), log, photos


def read(path):
    with open(path) as f:
        return f.read()


def wait_for(path, text, secs=12):
    end = time.time() + secs
    while time.time() < end:
        if os.path.exists(path) and text in read(path):
            return True
        time.sleep(0.2)
    return False


class LockCliTest(unittest.TestCase):
    def test_photo_and_lock(self):
        status, out, log, photos = run(["lock", "--photo", "clock"], WRITE_OK)
        self.assertEqual(status, 0, out[-500:])
        self.assertTrue(wait_for(log, "photo: "), "no photo logged")
        self.assertIn("locked: exit", read(log))
        self.assertEqual(len(os.listdir(photos)), 1)

    def test_check_failure_stops_before_screensaver(self):
        status, out, log, photos = run(["lock", "--photo", "clock"], "false {out}")
        self.assertNotEqual(status, 0)
        self.assertIn("cliss lock --photo:", out)
        self.assertNotIn("\x1b[?1049h", out)          # the screensaver never started
        time.sleep(2)
        self.assertFalse(os.path.exists(log))          # and nothing locked

    def test_lock_without_photo_unchanged(self):
        status, out, log, photos = run(["lock", "clock"], WRITE_OK)
        self.assertEqual(status, 0, out[-500:])
        self.assertTrue(wait_for(log, "locked: exit"))
        self.assertNotIn("photo: ", read(log))
        self.assertFalse(os.path.exists(photos))


if __name__ == "__main__":
    unittest.main()
