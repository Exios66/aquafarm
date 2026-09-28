from minigames.base import MiniGame


class FishingGame(MiniGame):
    """Keep the catch zone under a darting fish until the line reels in."""

    game_id = "fishing"
    title = "fishing pond"
    area = "aquarium"
    controls = "←/→ (h/l) move the catch zone"
    goal = "keep the fish inside [===] until the reel fills"
    duration = 25.0

    WIDTH = 32
    ZONE = 7
    FILL_RATE = 22.0
    DRAIN_RATE = 16.0
    SHY_CHANCE = 0.75  # how often the fish darts somewhere away from the lure

    def __init__(self, rng=None):
        super().__init__(rng)
        self.fish_pos = float(self.WIDTH // 2)
        self.fish_target = self.fish_pos
        self.fish_speed = 6.0
        self.zone_pos = (self.WIDTH - self.ZONE) // 2
        self.reel = 25.0
        self._retarget_in = 0.0

    def fish_in_zone(self):
        return self.zone_pos <= int(round(self.fish_pos)) < self.zone_pos + self.ZONE

    def _update(self, dt):
        self._retarget_in -= dt
        if self._retarget_in <= 0 or abs(self.fish_target - self.fish_pos) < 0.5:
            self.fish_target = float(self._pick_target())
            self.fish_speed = self.rng.uniform(4.0, 12.0)
            self._retarget_in = self.rng.uniform(0.6, 1.8)
        step = self.fish_speed * dt
        if self.fish_target > self.fish_pos:
            self.fish_pos = min(self.fish_target, self.fish_pos + step)
        else:
            self.fish_pos = max(self.fish_target, self.fish_pos - step)
        if self.fish_in_zone():
            self.reel += self.FILL_RATE * dt
        else:
            self.reel -= self.DRAIN_RATE * dt
        if self.reel >= 100:
            self.reel = 100.0
            self.score = 100 + int(self.time_left() * 8)
            self.finish(True, "you landed it!")
        elif self.reel <= 0:
            self.reel = 0.0
            self.finish(False, "the fish slipped away")

    def _pick_target(self):
        spots = list(range(self.WIDTH))
        if self.rng.random() < self.SHY_CHANCE:
            away = [x for x in spots if not self.zone_pos - 2 <= x < self.zone_pos + self.ZONE + 2]
            spots = away or spots
        return self.rng.choice(spots)

    def _handle_key(self, key):
        if key == "left":
            self.zone_pos = max(0, self.zone_pos - 2)
        elif key == "right":
            self.zone_pos = min(self.WIDTH - self.ZONE, self.zone_pos + 2)

    def _on_timeout(self):
        self.finish(False, "the fish lost interest")

    def render(self):
        water = "~" * (self.WIDTH + 2)
        fish_row = [" "] * self.WIDTH
        fish_row[int(round(self.fish_pos))] = "@"
        zone_row = [" "] * self.WIDTH
        zone_row[self.zone_pos] = "["
        zone_row[self.zone_pos + self.ZONE - 1] = "]"
        for i in range(self.zone_pos + 1, self.zone_pos + self.ZONE - 1):
            zone_row[i] = "="
        filled = int(self.reel / 5)
        return [
            water,
            "|" + "".join(fish_row) + "|",
            "|" + "".join(zone_row) + "|",
            water,
            "",
            "reel [" + "#" * filled + "." * (20 - filled) + f"] {int(self.reel)}%",
        ]
