#!/usr/bin/env python3
# cliss: Digital rain with katakana, glowing heads and depth
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "lib"))
from clissfx import run

GLYPHS = ("ｦｱｳｴｵｶｷｹｺｻｼｽｾｿﾀﾂﾃﾅﾆﾇﾈﾊﾋﾎﾏﾐﾑﾒﾓﾔﾕﾗﾘﾜ"
          "0123456789Z:.=*+-<>¦|ｸﾁﾄﾉﾌﾍﾖﾙﾚﾛﾝ")


class Drop:
    def __init__(self, x, y, h):
        self.x = x
        self.y = y
        self.depth = random.random()           # 0 = far away, 1 = close
        self.speed = 6 + 26 * self.depth ** 1.5
        self.length = random.randint(5, max(6, int(h * (0.4 + 0.6 * self.depth))))


class Matrix:
    def __init__(self, scr):
        self.s = scr
        w, h = scr.w, scr.h
        self.glyphs = [[random.choice(GLYPHS) for _ in range(w)] for _ in range(h)]
        self.target = int(w * 1.2)
        self.drops = [Drop(random.randrange(w), random.uniform(-h, h), h)
                      for _ in range(self.target)]
        self.drops.sort(key=lambda d: d.depth)  # draw near drops last
        # precomputed trail colors per depth bucket
        self.trails = {}

    def trail(self, depth, n):
        key = (int(depth * 8), n)
        pal = self.trails.get(key)
        if pal is None:
            bright = 0.35 + 0.65 * key[0] / 8
            pal = []
            for i in range(n):
                f = (1 - i / n) ** 1.6
                pal.append((int(20 * f * bright), int((40 + 215 * f) * bright), int((25 + 60 * f) * bright)))
            self.trails[key] = pal
        return pal

    def frame(self, dt, t):
        s = self.s
        w, h = s.w, s.h
        s.clear()
        g = self.glyphs
        for _ in range(w * h // 60 + 1):
            g[random.randrange(h)][random.randrange(w)] = random.choice(GLYPHS)

        alive = []
        for d in self.drops:
            d.y += d.speed * dt
            head = int(d.y)
            if head - d.length > h:
                continue
            alive.append(d)
            pal = self.trail(d.depth, d.length)
            for i in range(d.length):
                y = head - i
                if y < 0:
                    break
                if y >= h:
                    continue
                if i == 0:
                    ch = random.choice(GLYPHS) if random.random() < 0.5 else g[y][d.x]
                    s.put(d.x, y, ch, (210, 255, 220), None, True)
                else:
                    s.put(d.x, y, g[y][d.x], pal[i], None, i < 3)

        while len(alive) < self.target:
            alive.append(Drop(random.randrange(w), -random.uniform(0, h * 0.5), h))
        alive.sort(key=lambda d: d.depth)
        self.drops = alive


if __name__ == "__main__":
    run(Matrix, fps=30)
