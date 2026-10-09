"""lockwatch - the watchdog behind `cliss lock`.

Usage: python3 lockwatch.py <pid>

Waits for process <pid> (the screensaver) to end, however it ends, then locks
the screen. If another app or window comes to the front while it runs, it
locks right away and stops the screensaver. The launcher starts this in the
background before it runs the screensaver.

Locking uses the system lock screen on macOS, and loginctl (or
xdg-screensaver, dm-tool, ...) on Linux. The focus check needs macOS or Linux
on X11: Wayland doesn't let apps see which window has focus.

CLISS_LOCK_DRYRUN=<file> appends to <file> instead of locking (for testing).
"""

import ctypes
import os
import signal
import subprocess
import sys
import time

MAC = sys.platform == "darwin"
DRY = os.environ.get("CLISS_LOCK_DRYRUN")


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
    # our own session, so closing the terminal doesn't take us down with it
    os.setsid()
    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    # let focus settle first, in case we were started mid app switch
    time.sleep(1)
    start = front()
    while alive(pid):
        now = front()
        if start and now and now != start:
            if lock("focus"):
                # stop the screensaver; its python child first, since bash
                # would otherwise exit and leave it running
                subprocess.call(["pkill", "-TERM", "-P", str(pid)])
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            return
        time.sleep(0.25)
    lock("exit")


if __name__ == "__main__":
    main()
