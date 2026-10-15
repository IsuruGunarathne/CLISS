"""snap - take one photo with the webcam, for `cliss lock --photo`.

Usage: python3 snap.py --check

--check makes sure a photo can be taken, building the macOS helper the first
time and letting macOS ask for camera access, while you're still there.

macOS uses a small Swift helper (camsnap.swift), compiled once into
~/Library/Caches/cliss. Linux uses ffmpeg, or fswebcam. Photos go to
~/Pictures/cliss (or CLISS_PHOTO_DIR), readable only by you, and never leave
this machine.

CLISS_CAMERA_CMD replaces the camera command; "{out}" in it is the file to
write. CLISS_CAMERA picks the camera on Linux (default /dev/video0).
"""

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
TIMEOUT = 6


def photo_dir():
    return os.environ.get("CLISS_PHOTO_DIR") or os.path.expanduser("~/Pictures/cliss")


def photo_path(reason, now=None):
    stamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(now))
    return os.path.join(photo_dir(), "%s_%s.jpg" % (stamp, reason))


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


def camera_cmd(out):
    """The command that saves one photo to `out`, or None if there's no way to take one."""
    custom = os.environ.get("CLISS_CAMERA_CMD")
    if custom:
        return [arg.replace("{out}", out) for arg in shlex.split(custom)]
    if MAC:
        path = helper_path()
        return [path, out] if os.path.exists(path) else None
    device = os.environ.get("CLISS_CAMERA", "/dev/video0")
    if shutil.which("ffmpeg"):
        # -ss after -i drops the first, still dark, frames
        return ["ffmpeg", "-loglevel", "error", "-f", "v4l2", "-i", device,
                "-ss", "0.6", "-frames:v", "1", "-y", out]
    if shutil.which("fswebcam"):
        return ["fswebcam", "-q", "--no-banner", "-d", device, "-S", "15", out]
    return None


def start(reason):
    """Start taking a photo without waiting for it. Returns (process, path), or None."""
    try:
        os.makedirs(photo_dir(), mode=0o700, exist_ok=True)
    except OSError:
        return None
    path = photo_path(reason)
    cmd = camera_cmd(path)
    if not cmd:
        return None
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
    except OSError:
        return None
    return proc, path


def finish(shot, timeout=TIMEOUT):
    """Wait for a photo from start(). Returns where it was saved, or None."""
    if not shot:
        return None
    proc, path = shot
    try:
        ok = proc.wait(timeout) == 0
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        ok = False
    if ok and os.path.isfile(path) and os.path.getsize(path) > 0:
        os.chmod(path, 0o600)
        return path
    try:
        os.remove(path)
    except OSError:
        pass
    return None


def check():
    """Take a test photo (not kept). Returns an error message, or None if it worked."""
    if MAC and not os.environ.get("CLISS_CAMERA_CMD"):
        error = build_helper()
        if error:
            return error
    tmp = tempfile.mkdtemp()
    try:
        out = os.path.join(tmp, "test.jpg")
        cmd = camera_cmd(out)
        if not cmd:
            return "no way to take a photo: install ffmpeg or fswebcam"
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
        if code != 0 or not os.path.isfile(out) or os.path.getsize(out) == 0:
            return "couldn't take a photo (is the camera in use, or the lid closed?)"
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    if sys.argv[1:] != ["--check"]:
        sys.exit(__doc__.strip())
    error = check()
    if error:
        print("cliss lock --photo: " + error, file=sys.stderr)
        sys.exit(1)
