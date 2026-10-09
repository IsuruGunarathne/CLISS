#!/usr/bin/env python3
# cliss: The classic pipes screensaver, growing in neon colors
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "lib"))
from clissfx import run, hsv

UP, RIGHT, DOWN, LEFT = range(4)
STEP = {UP: (0, -1), RIGHT: (1, 0), DOWN: (0, 1), LEFT: (-1, 0)}

# box drawing sets, indexed by the two sides of the cell a pipe connects
STYLES = [
    "┃━┏┓┗┛",   # heavy
    "│─╭╮╰╯",   # rounded
    "║═╔╗╚╝",   # double
    "│─┌┐└┘",   # light
]


def piece(style, came_from, going):
    v, h, dr, dl, ur, ul = style
    sides = {came_from, going}
    if sides == {UP, DOWN}:
        return v
    if sides == {LEFT, RIGHT}:
        return h
    if sides == {DOWN, RIGHT}:
        return dr
    if sides == {DOWN, LEFT}:
        return dl
    if sides == {UP, RIGHT}:
        return ur
    return ul


class Pipe:
    def __init__(self, w, h):
        self.x, self.y = random.randrange(w), random.randrange(h)
        self.dir = random.randrange(4)
        self.color = hsv(random.random(), random.uniform(0.5, 0.9), 1)


class Pipes:
    def __init__(self, scr):
        self.s = scr
        self.reset()

    def reset(self):
        s = self.s
        s.clear()
        self.style = random.choice(STYLES)
        self.pipes = [Pipe(s.w, s.h) for _ in range(random.randint(3, 6))]
        self.drawn = 0
        self.limit = s.w * s.h * random.uniform(1.5, 3)
        self.acc = 0.0
        self.fading = 0

    def frame(self, dt, t):
        s = self.s
        if self.fading:
            # wipe the screen a few rows at a time before starting over
            for y in range(self.fading - 1, min(s.h, self.fading + 2)):
                s.cells[y] = [(" ", None, None, False)] * s.w
            self.fading += 3
            if self.fading > s.h:
                self.reset()
            return

        self.acc += dt * 70  # cells per second, per pipe
        while self.acc >= 1:
            self.acc -= 1
            for p in self.pipes:
                old = p.dir
                if random.random() < 0.12:
                    p.dir = (p.dir + random.choice((1, 3))) % 4
                came_from = (old + 2) % 4
                s.put(p.x, p.y, piece(self.style, came_from, p.dir), p.color, None, True)
                dx, dy = STEP[p.dir]
                p.x, p.y = p.x + dx, p.y + dy
                if not (0 <= p.x < s.w and 0 <= p.y < s.h):
                    # wrap around and pick a fresh color, like the original
                    p.x %= s.w
                    p.y %= s.h
                    p.color = hsv(random.random(), random.uniform(0.5, 0.9), 1)
                self.drawn += 1
            if self.drawn > self.limit:
                self.fading = 1
                break


if __name__ == "__main__":
    run(Pipes, fps=30)
