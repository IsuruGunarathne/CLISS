"""lockwatch - the watchdog behind `cliss lock`.

Usage: python3 lockwatch.py <pid> [--sentry]

Waits for process <pid> (the screensaver) to end, however it ends, then locks
the screen. If another app or window comes to the front while it runs, it
locks right away and stops the screensaver. The launcher starts this in the
background before it runs the screensaver.

Locking uses the system lock screen on macOS, and loginctl (or
xdg-screensaver, dm-tool, ...) on Linux. The focus check needs macOS or Linux
on X11: Wayland doesn't let apps see which window has focus.

With --sentry it records who touched the computer: a burst of webcam photos
(see snap.py), starting about 2.5s before it locks and carrying on behind the
lock screen. Without a working camera it just locks.

With a disarm PIN, the screensaver sends SIGUSR1 on the first key (start
recording now; it then reads the PIN) and SIGUSR2 once the right PIN is in
(throw the photos away and lock now). It still locks either way.

CLISS_LOCK_DRYRUN=<file> appends to <file> instead of locking (for testing).
"""

import ctypes
import os
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snap  # noqa: E402

MAC = sys.platform == "darwin"
DRY = os.environ.get("CLISS_LOCK_DRYRUN")
SENTRY = "--sentry" in sys.argv[2:]
# photos before locking: about 0.5s for the camera to start, then 2s of photos
LOCK_AFTER = 2.5

keyed = disarmed = False


def on_key(*_):
    global keyed
    keyed = True


def on_disarm(*_):
    global disarmed
    disarmed = True


def output(*cmd):
    try:
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              universal_newlines=True, timeout=2).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def front():
    """The app or window in front, or None if we can't tell."""
    if MAC:
        return output("lsappinfo", "front")
    if os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        return output("xprop", "-root", "_NET_ACTIVE_WINDOW")
    return None


def lock(reason):
    """Lock the screen. Returns False if no way of locking worked."""
    if DRY:
        with open(DRY, "a") as f:
            f.write("locked: %s\n" % reason)
        return True
    if MAC:
        ctypes.CDLL("/System/Library/PrivateFrameworks/login.framework"
                    "/Versions/Current/login").SACLockScreenImmediate()
        return True
    for cmd in (["loginctl", "lock-session"], ["xdg-screensaver", "lock"],
                ["gnome-screensaver-command", "-l"], ["dm-tool", "lock"], ["xflock4"]):
        try:
            if subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                return True
        except OSError:
            pass
    return False


def caught(reason):
    """Lock the screen, recording a burst of photos with --sentry. Returns lock()'s result."""
    shot = snap.start(reason) if SENTRY else None
    if shot:
        # wait while the camera records, but lock at once if it gives up
        end = time.time() + LOCK_AFTER
        while time.time() < end and shot[0].poll() is None and not disarmed:
            time.sleep(0.1)
    locked = lock(reason)
    photos = snap.finish(shot, stop=lambda: disarmed)
    if DRY and photos:
        with open(DRY, "a") as f:
            f.write("photos: %d in %s\n" % (len(photos), os.path.dirname(photos[0])))
    if DRY and shot and disarmed:
        with open(DRY, "a") as f:
            f.write("disarmed\n")
    return locked


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    return True


def main():
    pid = int(sys.argv[1])
    # first, since a signal's default action would kill us
    signal.signal(signal.SIGUSR1, on_key)
    signal.signal(signal.SIGUSR2, on_disarm)
    # our own session, so closing the terminal doesn't take us down with it
    os.setsid()
    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    # let focus settle first, in case we were started mid app switch
    time.sleep(1)
    start = front()
    while alive(pid) and not keyed:
        now = front()
        if start and now and now != start:
            if caught("focus"):
                # stop the screensaver; its python child first, since bash
                # would otherwise exit and leave it running
                subprocess.call(["pkill", "-TERM", "-P", str(pid)])
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            return
        time.sleep(0.25)
    caught("exit")


if __name__ == "__main__":
    main()
