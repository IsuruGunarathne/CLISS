#!/usr/bin/env python3
# cliss: A giant clock bouncing around like the DVD logo (watch for corners!)
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "lib"))
from clissfx import run, hsv, scale

FONT = {
    "0": ["███", "█ █", "█ █", "█ █", "███"],
    "1": ["██ ", " █ ", " █ ", " █ ", "███"],
    "2": ["███", "  █", "███", "█  ", "███"],
    "3": ["███", "  █", "███", "  █", "███"],
    "4": ["█ █", "█ █", "███", "  █", "  █"],
    "5": ["███", "█  ", "███", "  █", "███"],
    "6": ["███", "█  ", "███", "█ █", "███"],
    "7": ["███", "  █", "  █", "  █", "  █"],
    "8": ["███", "█ █", "███", "█ █", "███"],
    "9": ["███", "█ █", "███", "  █", "███"],
    ":": [" ", "█", " ", "█", " "],
}


def glyphs(text, blink):
    """Lay the text out as a 5-row bitmap, one column per font pixel."""
    rows = [""] * 5
    for ch in text:
        g = FONT[ch]
        if ch == ":" and not blink:
            g = [" "] * 5
        for i in range(5):
            rows[i] += g[i] + " "
    return [r[:-1] for r in rows]


class Clock:
    def __init__(self, scr):
        self.s = scr
        # "HH:MM:SS" is 27 font pixels wide; double up when there is room
        self.zoom = 2 if scr.w >= 27 * 4 + 8 and scr.h >= 22 else 1
        self.x = random.uniform(0, max(1, scr.w - 60))
        self.y = random.uniform(0, max(1, scr.h - 12))
        self.vx = random.choice((-1, 1)) * 11.0
        self.vy = random.choice((-1, 1)) * 5.0
        self.hue = random.random()
        self.party = 0.0
        self.sparks = []

    def frame(self, dt, t):
        s = self.s
        s.clear()
        now = time.localtime()
        bitmap = glyphs(time.strftime("%H:%M:%S", now), now.tm_sec % 2 == 0)
        zx, zy = 2 * self.zoom, self.zoom
        bw, bh = len(bitmap[0]) * zx, 5 * zy + 2

        self.x += self.vx * dt
        self.y += self.vy * dt
        hit_x = hit_y = False
        if self.x <= 0 or self.x + bw >= s.w:
            self.vx = -self.vx
            self.x = min(max(self.x, 0), max(0, s.w - bw))
            hit_x = True
        if self.y <= 0 or self.y + bh >= s.h:
            self.vy = -self.vy
            self.y = min(max(self.y, 0), max(0, s.h - bh))
            hit_y = True
        if hit_x or hit_y:
            self.hue = (self.hue + random.uniform(0.2, 0.5)) % 1
        if hit_x and hit_y:   # the legendary corner hit
            self.party = 4.0
            for _ in range(80):
                self.sparks.append([self.x + bw / 2, self.y + bh / 2, random.uniform(-30, 30),
                                    random.uniform(-15, 15), random.uniform(0.8, 2.0), random.random()])
        self.party = max(0.0, self.party - dt)

        ox, oy = int(self.x), int(self.y)
        for r, line in enumerate(bitmap):
            for c, px in enumerate(line):
                if px == " ":
                    continue
                if self.party:
                    col = hsv(t * 0.8 + c * 0.03 + r * 0.05)
                else:
                    col = hsv(self.hue + c * 0.006, 0.75, 1 - r * 0.06)
                for dy in range(zy):
                    for dx in range(zx):
                        X, Y = ox + c * zx + dx, oy + r * zy + dy
                        # soft drop shadow
                        if s.get(X + 1, Y + 1)[0] == " ":
                            s.put(X + 1, Y + 1, "░", scale(col, 0.3))
                        s.put(X, Y, "█", col)

        date = time.strftime("%A, %d %B %Y", now)
        if self.party:
            date = "★ CORNER! ★"
        s.text(ox + (bw - len(date)) // 2, oy + 5 * zy + 1, date,
               hsv(self.hue + 0.1, 0.4, 0.9), None, True)

        alive = []
        for sp in self.sparks:
            sp[0] += sp[2] * dt
            sp[1] += sp[3] * dt
            sp[3] += 12 * dt
            sp[4] -= dt
            if sp[4] > 0:
                alive.append(sp)
                s.put(int(sp[0]), int(sp[1]), random.choice("*+·✦"), hsv(sp[5]), None, True)
        self.sparks = alive


if __name__ == "__main__":
    run(Clock, fps=30)
