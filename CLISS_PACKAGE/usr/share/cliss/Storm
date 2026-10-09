#!/usr/bin/env python3
# cliss: A thunderstorm: gusting rain, splashes and forked lightning
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "lib"))
from clissfx import run, mix, gradient, scale


class Storm:
    def __init__(self, scr):
        self.s = scr
        w, h = scr.w, scr.h
        self.sky = gradient([(8, 10, 22), (18, 22, 38), (28, 32, 48)], h)
        self.drops = [self.drop(True) for _ in range(w * h // 9)]
        self.splashes = []
        self.wind = 0.0
        self.bolt = None
        self.bolt_t = 0.0
        self.next_bolt = random.uniform(2, 6)
        self.flash = 0.0
        # rolling clouds along the top
        self.clouds = [random.random() for _ in range(w * 2)]

    def drop(self, anywhere=False):
        s = self.s
        near = random.random()
        return [random.uniform(-s.w * 0.3, s.w * 1.3),
                random.uniform(0, s.h) if anywhere else random.uniform(-3, 0),
                12 + 38 * near, near]

    def make_bolt(self):
        """A jagged path from the clouds to the ground, with a few forks."""
        s = self.s
        segs = []
        x = random.uniform(s.w * 0.15, s.w * 0.85)
        stack = [(x, 0, s.h - 1, 1.0)]
        while stack:
            x, y, end, power = stack.pop()
            while y < end:
                dx = random.choice((-1, -1, 0, 1, 1))
                ch = "\\" if dx > 0 else "/" if dx < 0 else "|"
                segs.append((int(x), y, ch, power))
                x += dx
                y += 1
                if power > 0.4 and random.random() < 0.08:
                    stack.append((x, y, min(end, y + random.randint(3, s.h // 2)), power * 0.6))
        return segs

    def frame(self, dt, t):
        s = self.s
        w, h = s.w, s.h
        self.wind = math.sin(t * 0.15) * 0.45 + math.sin(t * 0.53) * 0.15

        # lightning: strike, flicker, fade
        self.next_bolt -= dt
        if self.next_bolt <= 0:
            self.bolt = self.make_bolt()
            self.bolt_t = 0.0
            self.flash = 1.0
            self.next_bolt = random.uniform(3, 10)
        self.flash = max(0.0, self.flash - dt * 3)
        flicker = self.flash
        if self.bolt is not None:
            self.bolt_t += dt
            if 0.08 < self.bolt_t < 0.14:
                flicker = 0.1   # the classic double flash
            elif 0.14 <= self.bolt_t < 0.2:
                flicker = 0.9
            if self.bolt_t > 0.5:
                self.bolt = None

        for y in range(h):
            bg = mix(self.sky[y], (120, 130, 170), flicker * 0.6)
            s.cells[y] = [(" ", None, bg, False)] * w

        # clouds
        for x in range(w):
            c = self.clouds[int(x + t * 2) % len(self.clouds)]
            c2 = self.clouds[int(x * 0.5 + t * 1.2 + 37) % len(self.clouds)]
            dens = (c + c2) / 2
            ch = "▓" if dens > 0.7 else "▒" if dens > 0.45 else "░"
            cloud = mix((40, 44, 60), (200, 210, 240), flicker * 0.8)
            s.put(x, 0, ch, cloud, s.cells[0][x][2])
            if dens > 0.55:
                s.put(x, 1, "░", scale(cloud, 0.7), s.cells[1][x][2])

        if self.bolt is not None and flicker > 0.3:
            for x, y, ch, power in self.bolt:
                col = mix((140, 160, 255), (255, 255, 255), power)
                s.put(x, y, ch, col, None, True)

        # rain
        lean = "/" if self.wind < -0.2 else "\\" if self.wind > 0.2 else "|"
        for d in self.drops:
            speed, near = d[2], d[3]
            d[1] += speed * dt
            d[0] += self.wind * speed * dt * 1.4
            if d[1] >= h - 1:
                if near > 0.5 and random.random() < 0.6:
                    self.splashes.append([d[0], h - 1, 0.0])
                d[:] = self.drop()
                continue
            x, y = int(d[0]), int(d[1])
            if 0 <= x < w and y >= 0:
                col = mix((50, 60, 90), (170, 190, 230), near)
                col = mix(col, (255, 255, 255), flicker * 0.5)
                s.put(x, y, lean if near > 0.35 else "'", col, s.cells[y][x][2])

        # ground and splashes
        ground = mix((15, 18, 28), (90, 100, 130), flicker * 0.6)
        for x in range(w):
            ripple = math.sin(x * 0.7 + t * 6) + math.sin(x * 0.23 - t * 3)
            s.put(x, h - 1, "~" if ripple > 0.8 else "_", (60, 75, 110), ground)
        alive = []
        for sp in self.splashes:
            sp[2] += dt
            if sp[2] < 0.25:
                alive.append(sp)
                x = int(sp[0])
                ch = "." if sp[2] < 0.08 else "o" if sp[2] < 0.16 else "°"
                if 0 <= x < w:
                    s.put(x, h - 2 if sp[2] > 0.1 else h - 1, ch, (150, 170, 210), s.get(x, h - 2)[2])
        self.splashes = alive


if __name__ == "__main__":
    run(Storm, fps=30)
