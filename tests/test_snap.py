import os
import stat
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Animations", "lib"))
import snap  # noqa: E402

WRITE_OK = "sh -c 'printf jpeg > \"$1\"' sh {out}"
WRITE_FAIL = "sh -c 'printf jpeg > \"$1\"; exit 1' sh {out}"


class SnapTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"CLISS_PHOTO_DIR": os.path.join(self.dir, "photos")})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def camera(self, cmd):
        return mock.patch.dict(os.environ, {"CLISS_CAMERA_CMD": cmd})

    def test_photo_path(self):
        now = time.mktime((2026, 10, 14, 15, 42, 10, 0, 0, -1))
        self.assertEqual(snap.photo_path("focus", now),
                         os.path.join(self.dir, "photos", "2026-10-14_15-42-10_focus.jpg"))

    def test_custom_camera_cmd(self):
        with self.camera("cam --to {out} -q"):
            self.assertEqual(snap.camera_cmd("/x.jpg"), ["cam", "--to", "/x.jpg", "-q"])

    def test_capture_saves_private_photo(self):
        with self.camera(WRITE_OK):
            path = snap.finish(snap.start("exit"))
        self.assertTrue(path.endswith("_exit.jpg"))
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(snap.photo_dir()).st_mode), 0o700)

    def test_failed_capture_leaves_no_file(self):
        with self.camera(WRITE_FAIL):
            self.assertIsNone(snap.finish(snap.start("exit")))
        self.assertEqual(os.listdir(snap.photo_dir()), [])

    def test_hung_capture_times_out(self):
        with self.camera("sleep 30"):
            t = time.time()
            self.assertIsNone(snap.finish(snap.start("exit"), timeout=0.5))
        self.assertLess(time.time() - t, 3)

    def test_missing_camera_command(self):
        with self.camera("/nonexistent/camera {out}"):
            self.assertIsNone(snap.start("exit"))

    def test_unwritable_photo_dir(self):
        blocker = os.path.join(self.dir, "file")
        open(blocker, "w").close()
        with mock.patch.dict(os.environ, {"CLISS_PHOTO_DIR": os.path.join(blocker, "photos")}), \
                self.camera(WRITE_OK):
            self.assertIsNone(snap.start("exit"))

    def test_finish_none(self):
        self.assertIsNone(snap.finish(None))

    def test_check_ok(self):
        with self.camera(WRITE_OK):
            self.assertIsNone(snap.check())

    def test_check_reports_failure(self):
        with self.camera(WRITE_FAIL):
            self.assertIn("couldn't take a photo", snap.check())

    def test_build_helper_without_swiftc(self):
        with mock.patch.object(snap, "helper_path", return_value=os.path.join(self.dir, "none")), \
                mock.patch.object(snap.shutil, "which", return_value=None):
            self.assertIn("xcode-select --install", snap.build_helper())

    @unittest.skipIf(sys.platform == "darwin", "Linux camera tools")
    def test_linux_prefers_ffmpeg(self):
        bin_dir = os.path.join(self.dir, "bin")
        os.mkdir(bin_dir)
        for tool in ("ffmpeg", "fswebcam"):
            path = os.path.join(bin_dir, tool)
            with open(path, "w") as f:
                f.write("#!/bin/sh\n")
            os.chmod(path, 0o755)
        with mock.patch.dict(os.environ, {"PATH": bin_dir}):
            cmd = snap.camera_cmd("/x.jpg")
        self.assertEqual((cmd[0], cmd[-1]), ("ffmpeg", "/x.jpg"))
        self.assertIn("/dev/video0", cmd)

    @unittest.skipIf(sys.platform == "darwin", "Linux camera tools")
    def test_linux_without_tools(self):
        with mock.patch.dict(os.environ, {"PATH": self.dir}):
            self.assertIsNone(snap.camera_cmd("/x.jpg"))
            self.assertIn("install ffmpeg or fswebcam", snap.check())


if __name__ == "__main__":
    unittest.main()
