import os
import pty
import stat
import select
import subprocess
import tempfile
import time
import unittest

CLISS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cliss")
BURST = "sh -c 'for i in $(seq 1 \"$2\"); do printf jpeg > \"$1/0$i.jpg\"; done' sh {dir} {count}"
# still recording when the PIN comes in, like a real camera
SLOW_BURST = "sh -c 'for i in $(seq 1 \"$2\"); do printf jpeg > \"$1/0$i.jpg\"; done; sleep 3' sh {dir} {count}"
PROMPT = "Disarm PIN"
NO_PIN = [(PROMPT, 0.3, b"\n"), (None, 2.0, b"x")]


def typed(text):
    """Keys for `text`, one at a time, like a person typing."""
    return [(None, 0.15, bytes([c])) for c in text.encode()]


def run(args, camera, keys=((None, 2.0, b"x"),), config=None):
    """Run cliss in a pty and type `keys`, a list of (wait for this output or None,
    then this many seconds, bytes). `config` stands in for ~/.config (a fresh one
    if None). Returns (exit status, output, dry-run log path, photo dir)."""
    tmp = tempfile.mkdtemp()
    log, photos = os.path.join(tmp, "log"), os.path.join(tmp, "photos")
    env = dict(os.environ, TERM="xterm-256color", CLISS_LOCK_DRYRUN=log,
               CLISS_PHOTO_DIR=photos, CLISS_CAMERA_CMD=camera, CLISS_PIN_WAIT="1",
               XDG_CONFIG_HOME=config or os.path.join(tmp, "config"))
    pid, fd = pty.fork()
    if pid == 0:
        os.execvpe(CLISS, [CLISS] + args, env)
    out, start, mark, keys = b"", time.time(), time.time(), list(keys)
    while time.time() - start < 20:
        if keys:
            text, delay, data = keys[0]
            if text and text.encode() not in out:
                mark = time.time()
            elif time.time() - mark > delay:
                keys.pop(0)
                mark = time.time()
                try:
                    os.write(fd, data)
                except OSError:  # cliss already exited (the --check failure test)
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
    def test_sentry_records_and_locks(self):
        status, out, log, photos = run(["lock", "--sentry", "clock"], BURST, NO_PIN)
        self.assertEqual(status, 0, out[-500:])
        self.assertTrue(wait_for(log, "photos: 9 in "), "no photos logged")
        self.assertIn("locked: exit", read(log))
        self.assertEqual(len(os.listdir(photos)), 1)                       # one folder...
        self.assertEqual(len(os.listdir(os.path.join(photos, os.listdir(photos)[0]))), 9)  # ...of 9

    def test_check_failure_stops_before_screensaver(self):
        status, out, log, photos = run(["lock", "--sentry", "clock"], "false {dir}")
        self.assertNotEqual(status, 0)
        self.assertIn("cliss lock --sentry:", out)
        self.assertNotIn("\x1b[?1049h", out)          # the screensaver never started
        time.sleep(2)
        self.assertFalse(os.path.exists(log))          # and nothing locked

    def test_pin_gets_you_back_without_photos(self):
        keys = [(PROMPT, 0.3, b"1234\n"), ("Again", 0.3, b"1234\n")] + typed("1234\n")
        keys[2] = (None, 2.0, keys[2][2])                  # the screensaver runs a while first
        status, out, log, photos = run(["lock", "--sentry", "clock"], SLOW_BURST, keys)
        self.assertEqual(status, 0, out[-500:])
        self.assertTrue(wait_for(log, "disarmed"), read(log) if os.path.exists(log) else "no log")
        self.assertIn("locked: exit", read(log))
        self.assertNotIn("photos: ", read(log))
        self.assertEqual(os.listdir(photos), [])
        self.assertNotIn("1234", out)                       # never echoed

    def test_wrong_pin_keeps_the_photos(self):
        keys = [(PROMPT, 0.3, b"1234\n"), ("Again", 0.3, b"1234\n"), (None, 2.0, b"9999\n")]
        status, out, log, photos = run(["lock", "--sentry", "clock"], SLOW_BURST, keys)
        self.assertEqual(status, 0, out[-500:])
        self.assertTrue(wait_for(log, "photos: 9 in "), "no photos logged")
        self.assertNotIn("disarmed", read(log))

    def test_mismatched_pins_stop_before_screensaver(self):
        keys = [(PROMPT, 0.3, b"1234\n"), ("Again", 0.3, b"4321\n")]
        status, out, log, photos = run(["lock", "--sentry", "clock"], BURST, keys)
        self.assertNotEqual(status, 0)
        self.assertIn("the PINs didn't match", out)
        self.assertNotIn("\x1b[?1049h", out)

    def test_short_pin_refused(self):
        status, out, log, photos = run(["lock", "--sentry", "clock"], BURST, [(PROMPT, 0.3, b"12\n")])
        self.assertNotEqual(status, 0)
        self.assertIn("at least 4 characters", out)

    def test_lock_without_sentry_unchanged(self):
        status, out, log, photos = run(["lock", "clock"], BURST)
        self.assertEqual(status, 0, out[-500:])
        self.assertNotIn(PROMPT, out)
        self.assertTrue(wait_for(log, "locked: exit"))
        self.assertNotIn("photos: ", read(log))
        self.assertFalse(os.path.exists(photos))


class DefaultPinTest(unittest.TestCase):
    def setUp(self):
        self.config = tempfile.mkdtemp()
        self.pin_file = os.path.join(self.config, "cliss", "pin")

    def set_default(self, pin):
        keys = [("Default disarm PIN", 0.3, pin + b"\n")] + ([("Again", 0.3, pin + b"\n")] if pin else [])
        return run(["--set-default-pin"], BURST, keys, self.config)

    def lock(self, keys):
        return run(["lock", "--sentry", "clock"], SLOW_BURST, keys, self.config)

    def test_set_and_remove(self):
        status, out, _, _ = self.set_default(b"1234")
        self.assertEqual(status, 0, out)
        self.assertIn("Saved.", out)
        self.assertNotIn("1234", out)
        self.assertEqual(stat.S_IMODE(os.stat(self.pin_file).st_mode), 0o600)
        self.assertNotIn("1234", read(self.pin_file))       # only its hash
        status, out, _, _ = self.set_default(b"")
        self.assertEqual(status, 0, out)
        self.assertFalse(os.path.exists(self.pin_file))

    def test_bad_default_refused(self):
        status, out, _, _ = self.set_default(b"12")
        self.assertNotEqual(status, 0)
        self.assertIn("at least 4 characters", out)
        self.assertFalse(os.path.exists(self.pin_file))

    def test_default_used_when_you_walk_away(self):
        self.set_default(b"1234")
        # nothing typed at the prompt; it gives up after CLISS_PIN_WAIT (1s)
        status, out, log, photos = self.lock([("Using your default PIN", 2.0, b"1234\n")])
        self.assertEqual(status, 0, out[-500:])
        self.assertTrue(wait_for(log, "disarmed"), read(log) if os.path.exists(log) else "no log")
        self.assertEqual(os.listdir(photos), [])

    def test_default_used_on_enter(self):
        self.set_default(b"1234")
        status, out, log, photos = self.lock([(PROMPT, 0.3, b"\n"), ("Using your default PIN", 2.0, b"1234\n")])
        self.assertEqual(status, 0, out[-500:])
        self.assertTrue(wait_for(log, "disarmed"))

    def test_typed_pin_replaces_the_default(self):
        self.set_default(b"1234")
        keys = [(PROMPT, 0.3, b"5678\n"), ("Again", 0.3, b"5678\n"), (None, 2.0, b"1234\n")]
        status, out, log, photos = self.lock(keys)
        self.assertNotIn("Using your default PIN", out)
        self.assertTrue(wait_for(log, "photos: 9 in "), "the default disarmed it")
        self.assertNotIn("disarmed", read(log))

    def test_no_default_and_no_answer_still_locks(self):
        status, out, log, photos = self.lock([(PROMPT, 2.0, b"x")])
        self.assertEqual(status, 0, out[-500:])
        self.assertTrue(wait_for(log, "photos: 9 in "))
        self.assertNotIn("disarmed", read(log))


if __name__ == "__main__":
    unittest.main()
