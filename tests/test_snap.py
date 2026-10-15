import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Animations", "lib"))
import snap  # noqa: E402

BURST = "sh -c 'for i in $(seq 1 \"$2\"); do printf jpeg > \"$1/0$i.jpg\"; done' sh {dir} {count}"
FAIL = "sh -c 'exit 1' sh {dir}"
PARTIAL = "sh -c 'printf jpeg > \"$1/01.jpg\"; exit 1' sh {dir}"


class SnapTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"CLISS_PHOTO_DIR": os.path.join(self.dir, "photos")})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def camera(self, cmd):
        return mock.patch.dict(os.environ, {"CLISS_CAMERA_CMD": cmd})

    def test_burst_dir(self):
        now = time.mktime((2026, 10, 14, 15, 42, 10, 0, 0, -1))
        self.assertEqual(snap.burst_dir("focus", now),
                         os.path.join(self.dir, "photos", "2026-10-14_15-42-10_focus"))

    def test_custom_camera_cmd(self):
        with self.camera("cam --to {dir} -n {count} -i {interval}"):
            self.assertEqual(snap.camera_cmd("/x", 9, 0.5),
                             ["cam", "--to", "/x", "-n", "9", "-i", "0.5"])

    def test_burst_saves_private_photos(self):
        with self.camera(BURST):
            photos = snap.finish(snap.start("exit", count=3))
        self.assertEqual([os.path.basename(p) for p in photos], ["01.jpg", "02.jpg", "03.jpg"])
        folder = os.path.dirname(photos[0])
        self.assertTrue(folder.endswith("_exit"))
        self.assertEqual(stat.S_IMODE(os.stat(photos[0]).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(folder).st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(os.stat(snap.photo_dir()).st_mode), 0o700)

    def test_failed_burst_leaves_nothing(self):
        with self.camera(FAIL):
            self.assertEqual(snap.finish(snap.start("exit")), [])
        self.assertEqual(os.listdir(snap.photo_dir()), [])

    def test_partial_burst_keeps_what_it_got(self):
        with self.camera(PARTIAL):
            photos = snap.finish(snap.start("exit"))
        self.assertEqual([os.path.basename(p) for p in photos], ["01.jpg"])

    def test_hung_camera_times_out(self):
        with self.camera("sleep 30"):
            t = time.time()
            self.assertEqual(snap.finish(snap.start("exit"), timeout=0.5), [])
        self.assertLess(time.time() - t, 3)
        self.assertEqual(os.listdir(snap.photo_dir()), [])

    def test_missing_camera_command(self):
        with self.camera("/nonexistent/camera {dir}"):
            self.assertIsNone(snap.start("exit"))
        self.assertEqual(os.listdir(snap.photo_dir()), [])

    def test_unwritable_photo_dir(self):
        blocker = os.path.join(self.dir, "file")
        open(blocker, "w").close()
        with mock.patch.dict(os.environ, {"CLISS_PHOTO_DIR": os.path.join(blocker, "photos")}), \
                self.camera(BURST):
            self.assertIsNone(snap.start("exit"))

    def test_finish_none(self):
        self.assertEqual(snap.finish(None), [])

    def test_check_ok(self):
        with self.camera(BURST):
            self.assertIsNone(snap.check())

    def test_check_reports_failure(self):
        with self.camera(FAIL):
            self.assertIn("couldn't take a photo", snap.check())

    def test_build_helper_without_swiftc(self):
        with mock.patch.object(snap, "helper_path", return_value=os.path.join(self.dir, "none")), \
                mock.patch.object(snap.shutil, "which", return_value=None):
            self.assertIn("xcode-select --install", snap.build_helper())

    def test_build_helper_timeout_cleans_up(self):
        path = os.path.join(self.dir, "helper")

        def stall(args, **kwargs):
            with open(args[args.index("-o") + 1], "w") as f:
                f.write("partial")
            raise subprocess.TimeoutExpired(args, kwargs["timeout"])
        with mock.patch.object(snap, "helper_path", return_value=path), \
                mock.patch.object(snap.shutil, "which", return_value="/usr/bin/swiftc"), \
                mock.patch.object(snap.subprocess, "run", side_effect=stall):
            self.assertIn("took over", snap.build_helper())
        self.assertEqual(os.listdir(self.dir), [])

    @unittest.skipIf(sys.platform == "darwin", "Linux camera tools")
    def test_linux_uses_ffmpeg(self):
        bin_dir = os.path.join(self.dir, "bin")
        os.mkdir(bin_dir)
        path = os.path.join(bin_dir, "ffmpeg")
        with open(path, "w") as f:
            f.write("#!/bin/sh\n")
        os.chmod(path, 0o755)
        with mock.patch.dict(os.environ, {"PATH": bin_dir}):
            cmd = snap.camera_cmd("/x", 9, 0.5)
        self.assertEqual((cmd[0], cmd[-1]), ("ffmpeg", "/x/%02d.jpg"))
        self.assertIn("/dev/video0", cmd)
        self.assertIn("fps=2", cmd)
        self.assertEqual(cmd[cmd.index("-frames:v") + 1], "9")

    @unittest.skipIf(sys.platform == "darwin", "Linux camera tools")
    def test_linux_without_ffmpeg(self):
        with mock.patch.dict(os.environ, {"PATH": self.dir}):
            self.assertIsNone(snap.camera_cmd("/x"))
            self.assertIn("install ffmpeg", snap.check())


if __name__ == "__main__":
    unittest.main()
