from minigames.base import MiniGame


class EggCatchGame(MiniGame):
    """Slide the basket to catch eggs rolling out of the henhouse."""

    game_id = "eggcatch"
    title = "egg catch"
    area = "livestock"
    controls = "←/→ (h/l) move the basket"
    goal = "catch 12 eggs; 3 broken and the round ends"
    duration = 45.0

    WIDTH = 21
    HEIGHT = 10
    TARGET = 12
    MAX_BROKEN = 3

    def __init__(self, rng=None):
        super().__init__(rng)
        self.basket = self.WIDTH // 2
        self.eggs = []  # [column, row(float), speed]
        self.caught = 0
        self.broken = 0
        self._spawn_in = 0.5

    def spawn_interval(self):
        return max(0.6, 1.3 - self.elapsed / self.duration * 0.7)

    def _update(self, dt):
        self._spawn_in -= dt
        if self._spawn_in <= 0:
            self._spawn_in = self.spawn_interval()
            speed = self.rng.uniform(3.5, 5.5) + self.elapsed / 15.0
            self.eggs.append([self.rng.randint(0, self.WIDTH - 1), 0.0, speed])
        landed = []
        for egg in self.eggs:
            egg[1] += egg[2] * dt
            if egg[1] >= self.HEIGHT - 1:
                landed.append(egg)
        for egg in landed:
            self.eggs.remove(egg)
            if abs(egg[0] - self.basket) <= 1:
                self.caught += 1
                self.score += 10
                if self.caught >= self.TARGET:
                    self.score += int(self.time_left() * 2)
                    self.finish(True, "a full basket!")
                    return
            else:
                self.broken += 1
                if self.broken >= self.MAX_BROKEN:
                    self.finish(False, "too many cracked eggs")
                    return

    def _handle_key(self, key):
        if key == "left":
            self.basket = max(1, self.basket - 2)
        elif key == "right":
            self.basket = min(self.WIDTH - 2, self.basket + 2)

    def _on_timeout(self):
        self.finish(self.caught >= self.TARGET // 2 + 2, f"{self.caught} eggs gathered")

    def render(self):
        rows = [[" "] * self.WIDTH for _ in range(self.HEIGHT)]
        for col, row, _ in self.eggs:
            r = min(self.HEIGHT - 2, int(row))
            rows[r][col] = "o"
        rows[self.HEIGHT - 1][self.basket - 1:self.basket + 2] = list("\\_/")
        top = " " + "^" * self.WIDTH + " "
        return [top] + ["|" + "".join(r) + "|" for r in rows] + ["=" * (self.WIDTH + 2)]

    def status_line(self):
        return (
            f"time {self.time_left():4.1f}s  caught {self.caught}/{self.TARGET}"
            f"  broken {self.broken}/{self.MAX_BROKEN}"
        )
