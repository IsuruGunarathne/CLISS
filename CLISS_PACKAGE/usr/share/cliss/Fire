#!/usr/bin/env python3
# cliss: Roaring Doom-style fire with drifting embers
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "lib"))
from clissfx import run

# The classic 37-step palette from the PSX Doom fire
_HEX = ("070707 1F0707 2F0F07 470F07 571707 671F07 771F07 8F2707 9F2F07 AF3F07 "
        "BF4707 C74707 DF4F07 DF5707 DF5707 D75F07 D75F07 D7670F CF6F0F CF770F "
        "CF7F0F CF8717 C78717 C78F17 C7971F BF9F1F BF9F1F BFA727 BFA727 BFAF2F "
        "B7AF2F B7B72F B7B737 CFCF6F DFDF9F EFEFC7 FFFFFF").split()
PALETTE = [None] + [tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) for h in _HEX[1:]]
TOP = len(PALETTE) - 1


class Fire:
    def __init__(self, scr):
        self.s = scr
        self.w, self.h = scr.w, scr.ph
        self.f = [0] * (self.w * self.h)
        base = (self.h - 1) * self.w
        for x in range(self.w):
            self.f[base + x] = TOP
        self.rnd = [random.getrandbits(2) for _ in range(1 << 16)]
        # how much heat a pixel loses per row, tuned so flames fill ~65% of the height
        loss = TOP / (0.65 * self.h)
        self.decay = [int(loss) + (random.random() < loss % 1) for _ in range(1 << 16)]
        self.embers = []
        self.gust = 0.0

    def frame(self, dt, t):
        w, h, f, rnd = self.w, self.h, self.f, self.rnd
        mask = len(rnd) - 1
        k = random.randrange(len(rnd))
        decay_tab = self.decay
        base = (h - 1) * w
        for x in range(w):  # a flickering source keeps the flames lively
            f[base + x] = TOP if random.random() < 0.92 else TOP - 6
        for i in range(w, w * h):
            v = f[i]
            if v == 0:
                f[i - w] = 0
                continue
            r = rnd[k & mask]
            k += 1
            decay = decay_tab[(k * 7) & mask]
            dst = i - r + 1 - w
            if dst >= 0:
                f[dst] = v - decay if v > decay else 0

        rows = [[PALETTE[v] for v in f[y * w:(y + 1) * w]] for y in range(h)]
        s = self.s
        s.clear()
        s.blit_pixels(rows)

        # embers drift up out of the flames on a wavering breeze
        self.gust += (random.random() - 0.5) * dt * 4
        self.gust *= 0.98
        if random.random() < 0.4 + w / 200:
            self.embers.append([random.uniform(0, w), s.h * random.uniform(0.55, 0.9),
                                random.uniform(4, 12), random.uniform(1.2, 3.5)])
        alive = []
        for e in self.embers:
            e[0] += (self.gust * 6 + random.uniform(-3, 3)) * dt
            e[1] -= e[2] * dt
            e[3] -= dt
            if e[3] > 0 and e[1] >= 0:
                alive.append(e)
                heat = min(1.0, e[3] / 2)
                ch = "*" if heat > 0.6 else "+" if heat > 0.3 else "."
                col = (255, int(120 + 120 * heat), int(40 * heat))
                cell = s.get(int(e[0]), int(e[1]))
                s.put(int(e[0]), int(e[1]), ch, col, cell[2])
        self.embers = alive


if __name__ == "__main__":
    run(Fire, fps=30)
