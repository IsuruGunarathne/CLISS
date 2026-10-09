#!/usr/bin/env python3
# cliss: The famous spinning ASCII donut, now with color and lighting
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "lib"))
from clissfx import run, hsv

SHADES = ".,-~:;=!*#$@"
R1, R2 = 1.0, 2.0          # tube radius, ring radius
K2 = 5.0                    # distance from viewer


def ring(n):
    return [(math.cos(i / n * 2 * math.pi), math.sin(i / n * 2 * math.pi)) for i in range(n)]


class Donut:
    def __init__(self, scr):
        self.s = scr
        # fit the donut to the screen; cells are about twice as tall as wide
        self.k1 = min(scr.w / 2, scr.h) * K2 * 3 / (8 * (R1 + R2))
        # sample densely enough that a big donut has no holes
        self.theta = ring(max(60, int(self.k1 * 3)))
        self.phi = ring(max(160, int(self.k1 * 8)))

    def frame(self, dt, t):
        s = self.s
        w, h = s.w, s.h
        s.clear()
        A, B = t * 0.9, t * 0.45
        cA, sA, cB, sB = math.cos(A), math.sin(A), math.cos(B), math.sin(B)
        k1 = self.k1
        cx, cy = w / 2, h / 2
        zbuf = {}
        hue = t * 0.03
        for ct, st in self.theta:
            circx = R2 + R1 * ct
            circy = R1 * st
            for cp, sp in self.phi:
                x = circx * (cB * cp + sA * sB * sp) - circy * cA * sB
                y = circx * (sB * cp - sA * cB * sp) + circy * cA * cB
                ooz = 1 / (K2 + cA * circx * sp + circy * sA)
                xp = int(cx + k1 * ooz * x * 2)
                yp = int(cy - k1 * ooz * y)
                lum = cp * ct * sB - cA * ct * sp - sA * st + cB * (cA * st - ct * sA * sp)
                key = yp * w + xp
                if lum > 0 and 0 <= xp < w and 0 <= yp < h and ooz > zbuf.get(key, 0):
                    zbuf[key] = ooz
                    li = lum / 1.42
                    ch = SHADES[min(11, int(li * 12))]
                    col = hsv(hue + ct * 0.08 + cp * 0.05, 0.75 - 0.4 * li, 0.25 + 0.75 * li)
                    s.put(xp, yp, ch, col, None, li > 0.7)


if __name__ == "__main__":
    run(Donut, fps=30)
