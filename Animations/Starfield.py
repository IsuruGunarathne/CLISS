#!/usr/bin/env python3
# cliss: Fly through space, with the occasional jump to warp speed
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "lib"))
from clissfx import run, scale

TINTS = [(255, 255, 255), (190, 210, 255), (255, 235, 200), (200, 255, 255), (255, 200, 220)]


def star():
    return [random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0.05, 1.0),
            random.choice(TINTS)]


def streak_char(dx, dy):
    if abs(dx) > 2 * abs(dy):
        return "─"
    if abs(dy) > 2 * abs(dx):
        return "│"
    return "╲" if (dx > 0) == (dy > 0) else "╱"


class Starfield:
    def __init__(self, scr):
        self.s = scr
        self.stars = [star() for _ in range(max(60, scr.w * scr.h // 10))]
        self.speed = 0.25

    def project(self, x, y, z):
        s = self.s
        cx, cy = s.w / 2, s.h / 2
        # cells are about twice as tall as wide, so stretch x to keep it round
        return cx + x / z * cx, cy + y / z * cx * 0.5

    def frame(self, dt, t):
        s = self.s
        s.clear()
        # cruise, then every ~25 seconds punch it to warp
        phase = (t % 25) / 25
        warp = max(0.0, math.sin(phase * math.pi * 2 - 1.2)) ** 3
        self.speed = 0.25 + 2.6 * warp
        dz = self.speed * dt

        for st in self.stars:
            x, y, z, tint = st
            ox, oy = self.project(x, y, z)
            z -= dz
            if z <= 0.02:
                st[:] = star()
                st[2] = 1.0
                continue
            st[2] = z
            px, py = self.project(x, y, z)
            if not (0 <= px < s.w and 0 <= py < s.h):
                st[:] = star()
                st[2] = 1.0
                continue
            near = 1 - z
            col = scale(tint, 0.15 + 0.85 * near ** 1.5)
            # long streaks while warping
            dx, dy = px - ox, py - oy
            steps = int(max(abs(dx), abs(dy)))
            if steps > 1:
                ch = streak_char(dx, dy)
                for i in range(1, steps):
                    k = i / steps
                    s.put(int(ox + dx * k), int(oy + dy * k), ch, scale(col, 0.25 + 0.6 * k))
            ch = "·" if near < 0.4 else "•" if near < 0.75 else "✦" if near < 0.93 else "★"
            s.put(int(px), int(py), ch, col, None, near > 0.75)

        if warp > 0.3:
            msg = " W A R P " if int(t * 3) % 2 else "         "
            s.text((s.w - len(msg)) // 2, s.h - 2, msg, scale((120, 200, 255), warp), None, True)


if __name__ == "__main__":
    run(Starfield, fps=30)
