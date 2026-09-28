"""Headless mini game core. The curses runner feeds keys and elapsed time.

Keys arrive as short names: "left", "right", "up", "down", "action", or a
digit string "1".."9". ``render()`` returns plain text lines; ``highlights()``
lists (line, column, width) cells the runner draws in reverse video.
"""

import random


class MiniGame:
    game_id = "base"
    title = "mini game"
    area = "homestead"
    controls = ""
    goal = ""
    duration = 30.0

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.elapsed = 0.0
        self.finished = False
        self.won = False
        self.score = 0
        self.outcome = ""

    def time_left(self):
        return max(0.0, self.duration - self.elapsed)

    def update(self, dt):
        if self.finished:
            return
        self.elapsed += dt
        self._update(dt)
        if not self.finished and self.elapsed >= self.duration:
            self._on_timeout()

    def handle_key(self, key):
        if not self.finished:
            self._handle_key(key)

    def finish(self, won, outcome=""):
        self.finished = True
        self.won = won
        self.outcome = outcome

    def _update(self, dt):
        pass

    def _handle_key(self, key):
        pass

    def _on_timeout(self):
        self.finish(False, "time's up")

    def render(self):
        return []

    def highlights(self):
        return []

    def status_line(self):
        return f"time {self.time_left():4.1f}s  score {self.score}"
