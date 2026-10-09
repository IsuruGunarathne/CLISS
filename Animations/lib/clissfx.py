"""clissfx - a tiny terminal rendering engine shared by the CLISS screensavers.

Only the Python standard library is used. An animation is a class that takes a
Screen in its constructor and implements frame(dt, t), drawing into the screen
with put()/text()/blit_pixels(). run() takes care of the terminal: alternate
screen, hidden cursor, key handling, resizes and diffed, colored output.
"""

import math
import os
import random
import select
import shutil
import signal
import sys
import termios
import time
import tty

_mode = os.environ.get("CLISS_COLOR", "").lower()
if _mode not in ("truecolor", "256"):
    _ct = os.environ.get("COLORTERM", "").lower()
    _mode = "truecolor" if _ct in ("truecolor", "24bit") else "256"
TRUECOLOR = _mode == "truecolor"

BLANK = (" ", None, None, False)


# ---------------------------------------------------------------- colors ----

def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def hsv(h, s=1.0, v=1.0):
    """h in turns (0..1, wraps), s and v in 0..1 -> (r, g, b) ints."""
    h = (h % 1.0) * 6.0
    i = int(h)
    f = h - i
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r, g, b = ((v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q))[i % 6]
    return (int(r * 255), int(g * 255), int(b * 255))


def mix(a, b, t):
    """Blend two (r, g, b) colors, t=0 -> a, t=1 -> b."""
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def scale(c, k):
    return (min(255, int(c[0] * k)), min(255, int(c[1] * k)), min(255, int(c[2] * k)))


def gradient(stops, n):
    """n colors evenly interpolated through a list of (r, g, b) stops."""
    out = []
    segs = len(stops) - 1
    for i in range(n):
        p = i / max(1, n - 1) * segs
        j = min(int(p), segs - 1)
        out.append(mix(stops[j], stops[j + 1], p - j))
    return out


_cache256 = {}


def _to256(c):
    idx = _cache256.get(c)
    if idx is None:
        r, g, b = c
        if abs(r - g) < 12 and abs(g - b) < 12:
            idx = 16 if r < 8 else 231 if r > 246 else 232 + round((r - 8) / 238 * 23)
        else:
            idx = 16 + 36 * round(r / 51) + 6 * round(g / 51) + round(b / 51)
        _cache256[c] = idx
    return idx


_sgr_cache = {}


def _sgr(fg, bg, bold):
    key = (fg, bg, bold)
    s = _sgr_cache.get(key)
    if s is None:
        parts = ["0"]
        if bold:
            parts.append("1")
        if fg is not None:
            parts.append("38;2;%d;%d;%d" % fg if TRUECOLOR else "38;5;%d" % _to256(fg))
        if bg is not None:
            parts.append("48;2;%d;%d;%d" % bg if TRUECOLOR else "48;5;%d" % _to256(bg))
        s = "\x1b[" + ";".join(parts) + "m"
        if len(_sgr_cache) > 50000:
            _sgr_cache.clear()
        _sgr_cache[key] = s
    return s


# ---------------------------------------------------------------- screen ----

class Screen:
    """A grid of cells (char, fg, bg, bold) that is diffed against what is
    already on the terminal, so only changed cells get written."""

    def __init__(self, w=80, h=24):
        self.resize(w, h)

    def resize(self, w, h):
        self.w, self.h = max(1, w), max(1, h)
        self.ph = self.h * 2  # height in half-block "pixels"
        self.cells = [[BLANK] * self.w for _ in range(self.h)]
        self._shown = None  # force a full redraw

    def clear(self, bg=None):
        cell = BLANK if bg is None else (" ", None, bg, False)
        self.cells = [[cell] * self.w for _ in range(self.h)]

    def put(self, x, y, ch, fg=None, bg=None, bold=False):
        if 0 <= y < self.h and 0 <= x < self.w:
            self.cells[y][x] = (ch, fg, bg, bold)

    def get(self, x, y):
        if 0 <= y < self.h and 0 <= x < self.w:
            return self.cells[y][x]
        return BLANK

    def text(self, x, y, s, fg=None, bg=None, bold=False, transparent=False):
        """Write a string. With transparent=True spaces are skipped and the
        existing background is kept, which is handy for sprites."""
        if not 0 <= y < self.h:
            return
        row = self.cells[y]
        for i, ch in enumerate(s):
            cx = x + i
            if 0 <= cx < self.w:
                if transparent:
                    if ch == " ":
                        continue
                    row[cx] = (ch, fg, bg if bg is not None else row[cx][2], bold)
                else:
                    row[cx] = (ch, fg, bg, bold)

    def blit_pixels(self, rows, y0=0):
        """Draw a list of pixel rows (each a list of (r, g, b) or None) using
        half blocks, two pixels per cell. Row 0 of `rows` lands on pixel row
        y0. None pixels leave the cell underneath alone where possible."""
        w = self.w
        start = y0 // 2
        for cy in range(start, min(self.h, (y0 + len(rows) + 1) // 2)):
            ti, bi = cy * 2 - y0, cy * 2 + 1 - y0
            top = rows[ti] if 0 <= ti < len(rows) else None
            bot = rows[bi] if 0 <= bi < len(rows) else None
            row = self.cells[cy]
            for x in range(w):
                t = top[x] if top is not None else None
                b = bot[x] if bot is not None else None
                if t is None:
                    if b is not None:
                        row[x] = ("▄", b, row[x][2], False)
                elif b is None:
                    row[x] = ("▀", t, row[x][2], False)
                elif t == b:
                    row[x] = (" ", None, t, False)
                else:
                    row[x] = ("▀", t, b, False)

    def render(self):
        """Return the escape sequence that brings the terminal up to date."""
        out = []
        shown = self._shown
        last = None
        for y, row in enumerate(self.cells):
            old = shown[y] if shown is not None else None
            if row == old:
                continue
            cursor = -1
            for x, cell in enumerate(row):
                if old is not None and cell == old[x]:
                    continue
                if cursor != x:
                    out.append("\x1b[%d;%dH" % (y + 1, x + 1))
                attr = cell[1:]
                if attr != last:
                    out.append(_sgr(*attr))
                    last = attr
                out.append(cell[0])
                cursor = x + 1
        self._shown = [list(r) for r in self.cells]
        return "".join(out)


# ---------------------------------------------------------------- runner ----

def _write(s):
    data = s.encode("utf-8", "replace")
    fd = sys.stdout.fileno()
    while data:
        try:
            n = os.write(fd, data)
        except InterruptedError:
            continue
        except BlockingIOError:
            select.select([], [fd], [])
            continue
        data = data[n:]


def run(anim_cls, fps=30):
    """Run an animation until a key is pressed.

    Keys: space pauses, anything else quits. Ctrl+C and SIGTERM quit too.
    If CLISS_DURATION is set (seconds), exit with status 3 after that long,
    which lets the launcher cycle through screensavers.
    """
    if not sys.stdout.isatty():
        sys.stderr.write("cliss: this screensaver needs a terminal\n")
        sys.exit(1)

    try:
        duration = float(os.environ.get("CLISS_DURATION", "0"))
    except ValueError:
        duration = 0.0

    fd = sys.stdin.fileno() if sys.stdin.isatty() else None
    saved = termios.tcgetattr(fd) if fd is not None else None
    resized = [True]
    signal.signal(signal.SIGWINCH, lambda *_: resized.__setitem__(0, True))
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    status = 0
    try:
        if fd is not None:
            tty.setcbreak(fd)
        _write("\x1b[?1049h\x1b[?25l\x1b[?7l\x1b[0m\x1b[2J")
        scr = Screen()
        anim = None
        t = 0.0
        paused = False
        start = last = time.monotonic()
        budget = 1.0 / fps
        while True:
            if resized[0]:
                resized[0] = False
                cols, rows = shutil.get_terminal_size((80, 24))
                scr.resize(cols, rows)
                _write("\x1b[0m\x1b[2J")
                anim = anim_cls(scr)

            now = time.monotonic()
            dt = min(now - last, 0.1)
            last = now
            if duration and now - start >= duration:
                status = 3
                break
            if not paused:
                t += dt
                anim.frame(dt, t)
                _write(scr.render())

            wait = max(0.0, budget - (time.monotonic() - now))
            if fd is None:
                time.sleep(wait)
                continue
            ready, _, _ = select.select([fd], [], [], wait)
            if ready:
                key = os.read(fd, 64)
                if key == b" ":
                    paused = not paused
                else:
                    break
    except KeyboardInterrupt:
        pass
    finally:
        _write("\x1b[0m\x1b[?7h\x1b[?25h\x1b[?1049l")
        if saved is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, saved)
    sys.exit(status)

