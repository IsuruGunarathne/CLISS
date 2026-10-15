"""snap - take a burst of webcam photos, for `cliss lock --sentry`.

Usage: python3 snap.py --check

--check makes sure photos can be taken, building the macOS helper the first
time and letting macOS ask for camera access, while you're still there.

Each burst goes in its own folder, ~/Pictures/cliss/<date>_<time>_<reason>/
(or under CLISS_PHOTO_DIR), as 01.jpg, 02.jpg, ..., readable only by you and
never leaving this machine. macOS uses a small Swift helper (camsnap.swift),
compiled once into ~/Library/Caches/cliss. Linux uses ffmpeg.

CLISS_CAMERA_CMD replaces the camera command; {dir}, {count} and {interval} in
it are filled in. CLISS_CAMERA picks the camera on Linux (default /dev/video0).
"""

import glob
import hashlib
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

MAC = sys.platform == "darwin"
HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "camsnap.swift")
COUNT = 9         # photos in a burst...
INTERVAL = 0.5    # ...one every half second


def photo_dir():
    return os.environ.get("CLISS_PHOTO_DIR") or os.path.expanduser("~/Pictures/cliss")


def burst_dir(reason, now=None):
    stamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(now))
    return os.path.join(photo_dir(), "%s_%s" % (stamp, reason))


def helper_path():
    # named after the source's hash, so an upgrade rebuilds it
    with open(SOURCE, "rb") as f:
        digest = hashlib.sha1(f.read()).hexdigest()[:12]
    return os.path.expanduser("~/Library/Caches/cliss/camsnap-" + digest)


def build_helper():
    """Compile the macOS helper if needed. Returns an error message, or None."""
    path = helper_path()
    if os.path.exists(path):
        return None
    if not shutil.which("swiftc"):
        return "taking photos needs the Xcode Command Line Tools: xcode-select --install"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    print("Building the camera helper (first time only, about a minute)...", file=sys.stderr)
    tmp = path + ".tmp"
    r = subprocess.run(["swiftc", "-O", "-swift-version", "5", SOURCE, "-o", tmp],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, universal_newlines=True)
    if r.returncode != 0:
        return "couldn't build the camera helper:\n" + r.stderr.strip()
    os.replace(tmp, path)
    return None


def camera_cmd(out_dir, count=COUNT, interval=INTERVAL):
    """The command that saves `count` photos into `out_dir`, or None if there's no way to."""
    custom = os.environ.get("CLISS_CAMERA_CMD")
    if custom:
        fill = {"{dir}": out_dir, "{count}": str(count), "{interval}": "%g" % interval}
        args = shlex.split(custom)
        for key, value in fill.items():
            args = [arg.replace(key, value) for arg in args]
        return args
    if MAC:
        path = helper_path()
        return [path, out_dir, str(count), "%g" % interval] if os.path.exists(path) else None
    if shutil.which("ffmpeg"):
        device = os.environ.get("CLISS_CAMERA", "/dev/video0")
        # -ss after -i drops the first second, while the camera sets its exposure
        return ["ffmpeg", "-loglevel", "error", "-f", "v4l2", "-i", device, "-ss", "1",
                "-vf", "fps=%g" % (1 / interval), "-frames:v", str(count), "-y",
                os.path.join(out_dir, "%02d.jpg")]
    return None


def photos_in(folder):
    return sorted(p for p in glob.glob(os.path.join(folder, "*.jpg")) if os.path.getsize(p) > 0)


def start(reason, count=COUNT, interval=INTERVAL):
    """Start a burst without waiting for it. Returns (process, folder), or None."""
    folder = burst_dir(reason)
    try:
        os.makedirs(photo_dir(), mode=0o700, exist_ok=True)
        os.makedirs(folder, mode=0o700, exist_ok=True)
    except OSError:
        return None
    cmd = camera_cmd(folder, count, interval)
    if cmd:
        try:
            return subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL), folder
        except OSError:
            pass
    shutil.rmtree(folder, ignore_errors=True)
    return None


def finish(shot, timeout=COUNT * INTERVAL + 6):
    """Wait for a burst from start(). Returns the photos it saved (maybe none)."""
    if not shot:
        return []
    proc, folder = shot
    try:
        proc.wait(timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    # keep whatever was saved, even if the camera failed partway
    photos = photos_in(folder)
    for photo in photos:
        os.chmod(photo, 0o600)
    if not photos:
        shutil.rmtree(folder, ignore_errors=True)
    return photos


def check():
    """Take a test photo (not kept). Returns an error message, or None if it worked."""
    if MAC and not os.environ.get("CLISS_CAMERA_CMD"):
        error = build_helper()
        if error:
            return error
    tmp = tempfile.mkdtemp()
    try:
        cmd = camera_cmd(tmp, 1)
        if not cmd:
            return "no way to take photos: install ffmpeg"
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            # long enough for the owner to answer macOS's permission prompt
            code = proc.wait(60)
        except OSError:
            return "couldn't run the camera command: " + cmd[0]
        except subprocess.TimeoutExpired:
            proc.kill()
            return "the camera didn't respond"
        if MAC and code == 3:
            return ("camera access is off for this terminal app; turn it on in "
                    "System Settings > Privacy & Security > Camera")
        if code != 0 or not photos_in(tmp):
            return "couldn't take a photo (is the camera in use, or the lid closed?)"
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    if sys.argv[1:] != ["--check"]:
        sys.exit(__doc__.strip())
    error = check()
    if error:
        print("cliss lock --sentry: " + error, file=sys.stderr)
        sys.exit(1)
