from minigames.base import MiniGame


class CrowGame(MiniGame):
    """Whack-a-mole: press a plot's number to shoo the crow off it."""

    game_id = "crows"
    title = "shoo the crows"
    area = "farm"
    controls = "number keys 1-9 shoo the crow on that plot"
    goal = "survive 30s with fewer than 6 sprouts eaten"
    duration = 30.0

    CROW_STAY = 1.8
    MAX_EATEN = 6

    def __init__(self, rng=None):
        super().__init__(rng)
        self.crows = {}  # plot index 0..8 -> seconds remaining
        self.eaten_plots = set()
        self.shooed = 0
        self.eaten = 0
        self._spawn_in = 0.8

    def spawn_interval(self):
        # speeds up from 1.1s to 0.55s over the round
        return max(0.55, 1.1 - self.elapsed / self.duration * 0.55)

    def _update(self, dt):
        for plot in list(self.crows):
            self.crows[plot] -= dt
            if self.crows[plot] <= 0:
                del self.crows[plot]
                self.eaten += 1
                self.eaten_plots.add(plot)
                if self.eaten >= self.MAX_EATEN:
                    self.finish(False, "the crows had a feast")
                    return
        self._spawn_in -= dt
        if self._spawn_in <= 0:
            self._spawn_in = self.spawn_interval()
            free = [p for p in range(9) if p not in self.crows]
            if free:
                self.crows[self.rng.choice(free)] = self.CROW_STAY

    def _handle_key(self, key):
        if key.isdigit() and key != "0":
            plot = int(key) - 1
            if plot in self.crows:
                del self.crows[plot]
                self.shooed += 1
                self.score += 10

    def _on_timeout(self):
        self.score += (self.MAX_EATEN - self.eaten) * 5
        self.finish(True, f"field defended! {self.shooed} crows shooed")

    def render(self):
        lines = ["+-----+-----+-----+"]
        for row in range(3):
            labels, cells = "|", "|"
            for col in range(3):
                plot = row * 3 + col
                labels += f"  {plot + 1}  |"
                if plot in self.crows:
                    cells += " (v) |"
                elif plot in self.eaten_plots:
                    cells += " ... |"
                else:
                    cells += " \\|/ |"
            lines += [labels, cells, "+-----+-----+-----+"]
        return lines

    def status_line(self):
        return (
            f"time {self.time_left():4.1f}s  shooed {self.shooed}"
            f"  eaten {self.eaten}/{self.MAX_EATEN}"
        )
