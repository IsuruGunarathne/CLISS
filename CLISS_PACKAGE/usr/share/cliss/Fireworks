#!/usr/bin/env python3
# cliss: Fireworks bursting over a sleeping city skyline
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "lib"))
from clissfx import run, hsv, mix, scale

SKY_TOP, SKY_LOW = (4, 4, 16), (18, 10, 38)


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max", "color", "drag", "twinkle", "rocket", "kind")

    def __init__(self, x, y, vx, vy, life, color, drag=0.985, twinkle=False, rocket=False, kind=None):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max = life
        self.color, self.drag, self.twinkle, self.rocket, self.kind = color, drag, twinkle, rocket, kind


class Fireworks:
    def __init__(self, scr):
        self.s = scr
        self.w, self.h = w, h = scr.w, scr.ph
        self.g = h * 0.35            # gravity, pixels/s^2
        self.parts = []
        self.glow = {}                # pixel -> (r, g, b) afterglow
        self.next_launch = 0.3
        self.flash = 0.0
        # a skyline silhouette with a few lit windows
        self.skyline = [None] * w
        x = 0
        while x < w:
            bw = random.randint(4, 12)
            bh = random.randint(int(h * 0.06), int(h * 0.22))
            for i in range(x, min(w, x + bw)):
                self.skyline[i] = bh
            x += bw + random.randint(0, 2)
        self.windows = {(x, y) for x in range(1, w - 1) for y in range(h)
                        if self.skyline[x] and h - self.skyline[x] + 2 < y < h - 1
                        and x % 3 == 1 and y % 3 == 0 and random.random() < 0.3}
        self.sky = [mix(SKY_TOP, SKY_LOW, y / h) for y in range(h)]
        self.stars = [(random.randrange(w), random.randrange(int(h * 0.7))) for _ in range(w * h // 120)]

    def launch(self):
        h = self.h
        x = random.uniform(self.w * 0.1, self.w * 0.9)
        apex = random.uniform(h * 0.12, h * 0.45)
        vy = -math.sqrt(2 * self.g * (h - apex))
        kind = random.choice(("sphere", "sphere", "ring", "willow", "crackle", "double", "palm"))
        self.parts.append(Particle(x, h - 1, random.uniform(-4, 4), vy, 10, (255, 220, 160),
                                   drag=1.0, rocket=True, kind=kind))

    def burst(self, p):
        kind = p.kind
        hue = random.random()
        base = hsv(hue, 0.85, 1)
        alt = hsv(hue + 0.5, 0.7, 1)
        n = random.randint(70, 140)
        speed = self.h * random.uniform(0.35, 0.55)
        self.flash = 0.25
        for i in range(n):
            a = random.uniform(0, 2 * math.pi)
            if kind == "ring":
                v = speed
                a = i / n * 2 * math.pi
            elif kind == "palm":
                a = (i % 7) / 7 * 2 * math.pi + random.uniform(-0.08, 0.08)
                v = speed * random.uniform(0.5, 1.0)
            else:
                v = speed * random.random() ** 0.4
            col = base
            life = random.uniform(1.2, 2.2)
            drag = 0.97
            twinkle = False
            if kind == "willow":
                col, life, drag = (255, 190, 90), life * 1.7, 0.94
            elif kind == "crackle":
                twinkle = True
            elif kind == "double" and i % 2:
                col = alt
                v *= 0.55
            self.parts.append(Particle(p.x, p.y, p.vx + math.cos(a) * v, p.vy * 0.1 + math.sin(a) * v,
                                       life, col, drag=drag, twinkle=twinkle))

    def frame(self, dt, t):
        w, h = self.w, self.h
        self.next_launch -= dt
        if self.next_launch <= 0:
            for _ in range(random.choice((1, 1, 1, 2, 3))):
                self.launch()
            self.next_launch = random.uniform(0.4, 1.6)

        glow = self.glow
        alive = []
        for p in self.parts:
            p.vy += self.g * dt
            p.vx *= p.drag
            p.vy *= p.drag
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.life -= dt
            if p.rocket:
                if p.vy >= -self.g * 0.05:
                    self.burst(p)
                    continue
                key = (int(p.x), int(p.y))
                glow[key] = (255, 200, 120)
                alive.append(p)
                continue
            if p.life <= 0 or p.y >= h or not 0 <= p.x < w:
                continue
            alive.append(p)
            k = p.life / p.max
            col = scale(p.color, 0.3 + 0.9 * k)
            if p.twinkle and k < 0.6:
                col = (255, 255, 230) if random.random() < 0.3 else (0, 0, 0)
            key = (int(p.x), int(p.y))
            glow[key] = mix(glow.get(key, col), col, 0.7) if key in glow else col
        self.parts = alive

        self.flash *= 0.8
        sky = self.sky
        lift = int(self.flash * 50)
        rows = [[(min(255, sky[y][0] + lift), min(255, sky[y][1] + lift), min(255, sky[y][2] + lift))] * w
                for y in range(h)]
        for x, y in self.stars:
            if random.random() > 0.02:
                rows[y][x] = (90, 90, 120)
        fresh = {}
        for (x, y), c in glow.items():
            if 0 <= y < h and 0 <= x < w:
                bg = rows[y][x]
                rows[y][x] = (max(bg[0], c[0]), max(bg[1], c[1]), max(bg[2], c[2]))
            c = (int(c[0] * 0.8), int(c[1] * 0.78), int(c[2] * 0.75))
            if c[0] + c[1] + c[2] > 40:
                fresh[(x, y)] = c
        self.glow = fresh
        building = (8, 8, 14)
        for x in range(w):
            bh = self.skyline[x]
            if bh:
                for y in range(h - bh, h):
                    rows[y][x] = building
        for x, y in self.windows:
            rows[y][x] = (200, 170, 80) if (x * 7 + y * 13 + int(t / 4)) % 11 else (40, 35, 20)
        self.s.blit_pixels(rows)


if __name__ == "__main__":
    run(Fireworks, fps=30)
