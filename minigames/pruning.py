from minigames.base import MiniGame

# Canopy silhouette: '#' marks a leaf cell.
CANOPY = [
    "      ###      ",
    "    #######    ",
    "  ###########  ",
    " ############# ",
    "###############",
    "  ###########  ",
    "    #######    ",
]
TRUNK = [
    "      |||      ",
    "     /|||\\     ",
    "  [=========]  ",
]


class PruningGame(MiniGame):
    """Snip the overgrown shoots (*) without cutting healthy leaves (o)."""

    game_id = "pruning"
    title = "shape the bonsai"
    area = "bonsai"
    controls = "arrows / hjkl move, space snips"
    goal = "snip every * shoot; 3 wrong cuts and the shape is ruined"
    duration = 40.0

    OVERGROWN = 8
    MAX_MISTAKES = 3

    def __init__(self, rng=None):
        super().__init__(rng)
        self.grid = [list(row.replace("#", "o")) for row in CANOPY]
        leaves = [
            (r, c) for r, row in enumerate(self.grid) for c, ch in enumerate(row) if ch == "o"
        ]
        for r, c in self.rng.sample(leaves, self.OVERGROWN):
            self.grid[r][c] = "*"
        self.cursor = [len(CANOPY) // 2, len(CANOPY[0]) // 2]
        self.mistakes = 0
        self.snipped = 0

    def remaining(self):
        return sum(row.count("*") for row in self.grid)

    def _handle_key(self, key):
        moves = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}
        if key in moves:
            dr, dc = moves[key]
            self.cursor[0] = max(0, min(len(self.grid) - 1, self.cursor[0] + dr))
            self.cursor[1] = max(0, min(len(self.grid[0]) - 1, self.cursor[1] + dc))
            return
        if key != "action":
            return
        r, c = self.cursor
        cell = self.grid[r][c]
        if cell == "*":
            self.grid[r][c] = " "
            self.snipped += 1
            self.score += 15
            if self.remaining() == 0:
                self.score += int(self.time_left() * 3)
                self.finish(True, "a perfectly balanced silhouette")
        elif cell == "o":
            self.grid[r][c] = " "
            self.mistakes += 1
            self.score = max(0, self.score - 10)
            if self.mistakes >= self.MAX_MISTAKES:
                self.finish(False, "too many healthy leaves cut")

    def _on_timeout(self):
        self.finish(False, f"{self.remaining()} shoots left untrimmed")

    def render(self):
        return ["".join(row) for row in self.grid] + TRUNK

    def highlights(self):
        return [(self.cursor[0], self.cursor[1], 1)]

    def status_line(self):
        return (
            f"time {self.time_left():4.1f}s  shoots left {self.remaining()}"
            f"  wrong cuts {self.mistakes}/{self.MAX_MISTAKES}"
        )
