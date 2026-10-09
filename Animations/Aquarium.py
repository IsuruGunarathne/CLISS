#!/usr/bin/env python3
# cliss: A cozy aquarium with fish, a crab, swaying kelp and bubbles
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "lib"))
from clissfx import run, hsv, mix, gradient

# right-facing sprites; left-facing ones are mirrored automatically
FISH = [
    ["><>"],
    ["><(((°>"],
    ["><((('>"],
    ["  __",
     "\\/ °\\",
     "/\\__/"],
    ["   /|",
     ">=='  °>",
     "   \\|"],
    ["    _____",
     "\\  /. . .\\",
     " >(  . . °>",
     "/  \\_____/"],
]
MIRROR = str.maketrans("<>()/\\[]{}'`", "><)(\\/][}{`'")
CRAB = ["(\\/) (°,,,°) (\\/)", "(\\/)(°,,,°)(\\/)"]


def mirror(art):
    width = max(len(r) for r in art)
    return [r.ljust(width)[::-1].translate(MIRROR) for r in art]


class Fish:
    def __init__(self, w, h, anywhere=False):
        art = random.choice(FISH)
        self.dir = random.choice((-1, 1))
        self.art = art if self.dir > 0 else mirror(art)
        self.width = max(len(r) for r in self.art)
        self.speed = random.uniform(3, 12) / (1 + len(self.art) * 0.25)
        self.base = random.uniform(3, max(4, h - 4 - len(self.art)))
        self.phase = random.uniform(0, 6.3)
        if anywhere:
            self.x = random.uniform(0, w)
        else:
            self.x = -self.width if self.dir > 0 else w
        self.color = hsv(random.random(), random.uniform(0.6, 1), 1)
        self.eye = mix(self.color, (255, 255, 255), 0.7)

    def y(self, t):
        return int(self.base + math.sin(t * 0.8 + self.phase) * 1.2)


class Aquarium:
    def __init__(self, scr):
        self.s = scr
        w, h = scr.w, scr.h
        self.water = gradient([(10, 70, 120), (5, 35, 80), (3, 15, 45)], h)
        self.fish = [Fish(w, h, True) for _ in range(max(4, w * h // 350))]
        self.bubbles = []
        self.kelp = [(random.randrange(w), random.randint(3, max(4, h // 2)), random.uniform(0, 6))
                     for _ in range(max(3, w // 12))]
        self.sand = [random.choice("..,:'_ ") for _ in range(w * 2)]
        self.crab_x = random.uniform(0, w)
        self.crab_v = random.choice((-1, 1)) * 2.5
        self.vents = [random.randrange(w) for _ in range(max(1, w // 40))]

    def frame(self, dt, t):
        s = self.s
        w, h = s.w, s.h
        for y in range(h):
            s.cells[y] = [(" ", None, self.water[y], False)] * w

        # light rays and the rippling surface
        for x in range(w):
            wave = math.sin(x * 0.25 + t * 2.2) + math.sin(x * 0.11 - t * 1.3)
            ch = "~" if wave > 0.6 else "^" if wave > 0 else "-" if wave > -0.8 else "_"
            s.put(x, 0, ch, (170, 220, 255), self.water[0], True)
            ray = math.sin(x * 0.08 + t * 0.3) + math.sin(x * 0.031 - t * 0.2)
            if ray > 1.4:
                for y in range(1, h - 2):
                    bg = mix(self.water[y], (60, 140, 190), (ray - 1.4) * 0.5 * (1 - y / h))
                    s.cells[y][x] = (" ", None, bg, False)

        # sea floor
        sand = (194, 170, 110)
        for x in range(w):
            s.put(x, h - 1, self.sand[(x + w) % len(self.sand)], (120, 100, 60), sand)
            s.put(x, h - 2, self.sand[x], mix(sand, (90, 80, 50), 0.5), mix(self.water[h - 2], sand, 0.35))

        # swaying kelp
        for kx, length, ph in self.kelp:
            for i in range(length):
                y = h - 3 - i
                sway = math.sin(t * 1.3 + ph + i * 0.45) * (i / max(1, length)) * 2.2
                ch = "(" if (i + int(t * 2 + ph)) % 2 else ")"
                g = 120 + int(100 * i / max(1, length))
                s.put(int(kx + sway), y, ch, (30, g, 60), self.water[y] if 0 <= y < h else None, True)

        # crab scuttling along the bottom
        self.crab_x += self.crab_v * dt
        if self.crab_x < 0 or self.crab_x > w - len(CRAB[0]):
            self.crab_v = -self.crab_v
            self.crab_x = min(max(self.crab_x, 0), w - len(CRAB[0]))
        if random.random() < 0.004:
            self.crab_v = -self.crab_v
        crab = CRAB[int(t * 4) % 2]
        s.text(int(self.crab_x), h - 2, crab, (255, 90, 60), None, True, transparent=True)

        # bubbles from vents and from the fish
        for vx in self.vents:
            if random.random() < 0.15:
                self.bubbles.append([vx + random.uniform(-0.5, 0.5), h - 3.0, random.uniform(3, 6)])
        for f in self.fish:
            if random.random() < 0.008:
                bx = f.x + (f.width if f.dir > 0 else 0)
                self.bubbles.append([bx, f.y(t), random.uniform(3, 6)])

        # fish
        for f in self.fish:
            f.x += f.speed * f.dir * dt
            if f.x > w + 2 or f.x < -f.width - 2:
                self.fish.remove(f)
                self.fish.append(Fish(w, h))
                continue
            fy = f.y(t)
            for i, row in enumerate(f.art):
                y = fy + i
                if not 1 <= y < h - 2:
                    continue
                for j, ch in enumerate(row):
                    if ch != " ":
                        col = f.eye if ch in "o°'" else f.color
                        s.put(int(f.x) + j, y, ch, col, s.get(int(f.x) + j, y)[2], True)

        alive = []
        for b in self.bubbles:
            b[1] -= b[2] * dt
            b[0] += math.sin(t * 5 + b[2] * 3) * dt
            if b[1] > 1:
                alive.append(b)
                ch = "." if b[1] > h * 0.66 else "o" if b[1] > h * 0.33 else "O"
                x, y = int(b[0]), int(b[1])
                s.put(x, y, ch, (200, 240, 255), s.get(x, y)[2])
        self.bubbles = alive


if __name__ == "__main__":
    run(Aquarium, fps=20)
