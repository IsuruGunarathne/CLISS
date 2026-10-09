#!/usr/bin/env python3
# cliss: Conway's Game of Life, colored by age with glowing afterimages
import os
import random
import sys
from collections import Counter
from itertools import chain

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "lib"))
from clissfx import run, hsv, gradient, scale

GLIDER = [(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)]
AGE_COLORS = gradient([(255, 255, 255), (120, 255, 200), (60, 170, 255), (140, 80, 255), (90, 40, 170)], 40)
STEPS_PER_SEC = 14


class Life:
    def __init__(self, scr):
        self.s = scr
        self.w, self.h = w, h = scr.w, scr.ph
        n = w * h
        self.nbrs = []
        for i in range(n):
            y, x = divmod(i, w)
            self.nbrs.append(tuple(((y + dy) % h) * w + (x + dx) % w
                                   for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy))
        self.ghost_tint = hsv(random.random(), 0.8, 1)
        self.seed()

    def seed(self):
        n = self.w * self.h
        self.live = {i for i in range(n) if random.random() < 0.28}
        self.age = dict.fromkeys(self.live, 0)
        self.ghost = {}
        self.gen = 0
        self.history = []
        self.acc = 0.0
        self.ghost_tint = hsv(random.random(), 0.8, 1)

    def drop_glider(self):
        ox, oy = random.randrange(self.w), random.randrange(self.h)
        fx, fy = random.choice((1, -1)), random.choice((1, -1))
        for gx, gy in GLIDER:
            i = ((oy + gy * fy) % self.h) * self.w + (ox + gx * fx) % self.w
            self.live.add(i)
            self.age[i] = 0

    def step(self):
        live = self.live
        counts = Counter(chain.from_iterable(self.nbrs[i] for i in live))
        new = {i for i, c in counts.items() if c == 3 or (c == 2 and i in live)}
        age = self.age
        self.age = {i: age.get(i, -1) + 1 for i in new}
        for i in live - new:
            self.ghost[i] = 1.0
        self.live = new
        self.gen += 1

        # reseed when the world has died out or settled into a loop
        pop = len(new)
        self.history.append(pop)
        if len(self.history) > 120:
            self.history.pop(0)
        stale = len(self.history) == 120 and max(self.history) - min(self.history) <= 6
        if pop < self.w * self.h * 0.01 or stale:
            self.seed()
        elif random.random() < 0.02:
            self.drop_glider()

    def frame(self, dt, t):
        self.acc += dt * STEPS_PER_SEC
        while self.acc >= 1:
            self.acc -= 1
            self.step()

        w, h = self.w, self.h
        flat = [None] * (w * h)
        fade = 0.86
        ghost = {}
        tint = self.ghost_tint
        for i, g in self.ghost.items():
            g *= fade
            if g > 0.06:
                ghost[i] = g
                flat[i] = scale(tint, g * 0.45)
        self.ghost = ghost
        last = len(AGE_COLORS) - 1
        for i, a in self.age.items():
            flat[i] = AGE_COLORS[a if a < last else last]

        s = self.s
        s.clear()
        s.blit_pixels([flat[y * w:(y + 1) * w] for y in range(h)])
        label = " gen %d · pop %d " % (self.gen, len(self.live))
        s.text(s.w - len(label) - 1, s.h - 1, label, (150, 150, 170), (20, 20, 30))


if __name__ == "__main__":
    run(Life, fps=30)
