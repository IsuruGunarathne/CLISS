#!/usr/bin/env python3
# cliss: Demoscene plasma in full color, slowly morphing between palettes
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "lib"))
from clissfx import run, mix

N = 1024          # sine table size
M = N - 1
SIN = [math.sin(i / N * 2 * math.pi) for i in range(N)]


def cosine_palette(a, b, c, d, n=256):
    """Inigo Quilez style palette: a + b*cos(2pi(c*t + d)), cyclic for integer c."""
    out = []
    for i in range(n):
        t = i / n
        out.append(tuple(int(255 * max(0.0, min(1.0, a[k] + b[k] * math.cos(2 * math.pi * (c[k] * t + d[k])))))
                         for k in range(3)))
    return out


PALETTES = [
    cosine_palette((0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (1, 1, 1), (0.00, 0.33, 0.67)),   # rainbow
    cosine_palette((0.5, 0.3, 0.5), (0.5, 0.3, 0.5), (1, 1, 1), (0.80, 0.90, 0.30)),   # synth
    cosine_palette((0.5, 0.4, 0.2), (0.5, 0.4, 0.2), (1, 1, 1), (0.00, 0.10, 0.20)),   # lava
    cosine_palette((0.2, 0.5, 0.5), (0.2, 0.5, 0.5), (1, 1, 1), (0.50, 0.20, 0.25)),   # ocean
    cosine_palette((0.3, 0.5, 0.3), (0.3, 0.5, 0.4), (1, 1, 2), (0.00, 0.25, 0.25)),   # toxic
]
HOLD = 14.0   # seconds per palette
FADE = 4.0    # seconds of crossfade


class Plasma:
    def __init__(self, scr):
        self.s = scr
        w, h = scr.w, scr.ph
        cx, cy = w / 2, h / 2
        k = N / (2 * math.pi)
        # per-pixel distance from the centre, already as a sine table index
        self.dist = [[int(math.hypot(x - cx, y - cy) * 0.18 * k) for x in range(w)] for y in range(h)]
        self.diag = [int(i * 0.06 * k) for i in range(w + h)]
        self.kx = 0.09 * k
        self.ky = 0.13 * k

    def palette(self, t):
        cyc = HOLD + FADE
        i = int(t // cyc) % len(PALETTES)
        p = t % cyc
        cur = PALETTES[i]
        if p < HOLD:
            return cur
        nxt = PALETTES[(i + 1) % len(PALETTES)]
        f = (p - HOLD) / FADE
        return [mix(a, b, f) for a, b in zip(cur, nxt)]

    def frame(self, dt, t):
        s = self.s
        w, h = s.w, s.ph
        ti = int(t * 160)
        # two moving wave fronts, one per axis, evaluated once per column / row
        sx = [SIN[(int(x * self.kx) + ti) & M] + SIN[(int(x * self.kx * 0.5) - ti // 2 + 300) & M] * 0.5
              for x in range(w)]
        sy = [SIN[(int(y * self.ky) - ti) & M] + SIN[(int(y * self.ky * 0.4) + ti // 3) & M] * 0.5
              for y in range(h)]
        pal = self.palette(t)
        shift = int(t * 40)
        rt = int(t * 220)
        dt_ = int(t * 90)
        diag = self.diag
        rows = []
        for y in range(h):
            ry = sy[y]
            drow = self.dist[y]
            rows.append([pal[(int((sx[x] + ry + SIN[(drow[x] - rt) & M] + SIN[(diag[x + y] + dt_) & M]) * 40)
                              + shift) & 255]
                         for x in range(w)])
        s.blit_pixels(rows)


if __name__ == "__main__":
    run(Plasma, fps=24)
