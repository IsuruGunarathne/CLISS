#!/usr/bin/env python3
# cliss: Outrun sunset: striped sun, neon mountains and an endless grid
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "lib"))
from clissfx import run, mix, gradient, scale

SKY = [(10, 2, 30), (40, 5, 70), (120, 20, 120), (255, 80, 120), (255, 160, 90)]
SUN = [(255, 240, 120), (255, 170, 60), (255, 60, 130)]
FLOOR = (14, 0, 30)
GRID = (255, 40, 200)
GRID2 = (60, 220, 255)


class Synthwave:
    def __init__(self, scr):
        self.s = scr
        w, h = self.w, self.h = scr.w, scr.ph
        self.hz = int(h * 0.58)            # horizon row
        sky = gradient(SKY, self.hz)
        self.bg = [[sky[y]] * w for y in range(self.hz)]
        for _ in range(w * self.hz // 60):  # stars in the upper sky
            x, y = random.randrange(w), random.randrange(max(1, self.hz // 2))
            self.bg[y][x] = mix(sky[y], (255, 255, 255), random.uniform(0.3, 0.9))

        self.sun_r = min(w * 0.18, self.hz * 0.75)
        self.sun_c = (w / 2, self.hz - self.sun_r * 0.55)
        self.sun_cols = gradient(SUN, max(2, int(self.sun_r * 2) + 1))

        # two layers of mountains silhouetted against the sun
        self.ridges = []
        for layer, (col, height) in enumerate((((60, 10, 90), 0.30), ((25, 5, 50), 0.18))):
            heights = []
            phase = random.uniform(0, 100)
            for x in range(w):
                v = (math.sin(x * 0.045 + phase) * 0.5 + math.sin(x * 0.11 + phase * 2) * 0.3
                     + math.sin(x * 0.27 + phase * 3) * 0.2)
                # keep the middle low so the sun shows through
                gap = min(1.0, abs(x - w / 2) / (self.sun_r * 1.4 + 1))
                heights.append(int(self.hz * height * (0.35 + 0.65 * abs(v)) * (0.25 + 0.75 * gap)))
            self.ridges.append((col, heights))

    def frame(self, dt, t):
        w, h, hz = self.w, self.h, self.hz
        rows = [list(r) for r in self.bg]

        # sun with scrolling stripes cut out of its lower half
        cx, cy = self.sun_c
        r = self.sun_r
        for y in range(max(0, int(cy - r)), min(hz, int(cy + r) + 1)):
            dy = (y - cy) / r
            half = math.sqrt(max(0.0, 1 - dy * dy)) * r
            if dy > -0.35:
                # stripe gaps that thicken toward the horizon and drift downward
                band = ((y - cy) / max(3.0, r * 0.16) - t * 0.4) % 1.0
                if band < 0.25 + dy * 0.6:
                    continue
            col = self.sun_cols[int(y - cy + r)]
            row = rows[y]
            for x in range(max(0, int(cx - half)), min(w, int(cx + half) + 1)):
                row[x] = col

        for col, heights in self.ridges:
            for x in range(w):
                top = hz - heights[x]
                for y in range(max(0, top), hz):
                    rows[y][x] = mix(col, (255, 60, 200), 0.6) if y == top else col

        # the floor: lines are placed exactly where they project, so nothing aliases
        depth = h - hz
        for y in range(hz, h):
            fog = min(1.0, (y - hz + 1) / depth * 2.2)
            rows.append([scale(FLOOR, 1.6 - 0.6 * fog)] * w)
        glow = mix(GRID, GRID2, 0.15 + 0.15 * math.sin(t * 0.5))
        cam = 40.0
        scroll = (t * 1.6) % 1.0

        def lit(y):
            fog = min(1.0, (y - hz + 1) / depth * 2.2)
            return mix(rows[y][0], mix(glow, (255, 255, 255), 0.2 * fog), fog)

        # horizontal lines rushing toward the viewer
        n = 1
        while True:
            z = n - scroll
            n += 1
            if z <= 0:
                continue
            y = int(hz - 1 + cam / z)
            if y >= h:
                continue
            if y <= hz or cam / (z * z) < 1.5:  # stop once lines would blur together
                break
            for yy in range(y, min(h, y + max(1, int(3 / z)))):
                rows[yy] = [lit(yy)] * w
        # vertical lines fanning out from the vanishing point
        spacing = 26.0
        for y in range(hz + 1, h):
            z = cam / (y - hz + 1)
            step = spacing / z
            if step < 2:
                continue
            col = lit(y)
            row = rows[y]
            k = 0
            while True:
                off = int(k * step)
                if off > w / 2 + 1:
                    break
                for x in (int(w / 2 + k * step), int(w / 2 - k * step)):
                    if 0 <= x < w:
                        row[x] = col
                k += 1
        # horizon glow
        rows[hz] = [mix(c, (255, 120, 220), 0.7) for c in rows[hz]]
        self.s.blit_pixels(rows)


if __name__ == "__main__":
    run(Synthwave, fps=30)
