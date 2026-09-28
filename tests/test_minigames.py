import os
import random
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, ROOT)

from minigames import GAMES, CrowGame, EggCatchGame, FishingGame, PruningGame

DT = 0.05


def run(game, bot, limit=2000):
    for _ in range(limit):
        if game.finished:
            break
        key = bot(game)
        if key:
            game.handle_key(key)
        game.update(DT)
    return game


class IdlePlayerLosesTest(unittest.TestCase):
    def test_idle_player_never_wins(self):
        for game_id, cls in GAMES.items():
            for seed in range(3):
                game = run(cls(random.Random(seed)), lambda g: None)
                self.assertTrue(game.finished, game_id)
                self.assertFalse(game.won, game_id)


class SkilledPlayerWinsTest(unittest.TestCase):
    def test_fishing_tracking_bot_wins(self):
        def bot(g):
            center = g.zone_pos + g.ZONE // 2
            if g.fish_pos < center - 1:
                return "left"
            if g.fish_pos > center + 1:
                return "right"
            return None

        for seed in range(5):
            self.assertTrue(run(FishingGame(random.Random(seed)), bot).won)

    def test_pruning_bot_wins(self):
        def bot(g):
            targets = [(r, c) for r, row in enumerate(g.grid) for c, ch in enumerate(row) if ch == "*"]
            r, c = min(targets, key=lambda t: abs(t[0] - g.cursor[0]) + abs(t[1] - g.cursor[1]))
            if r < g.cursor[0]:
                return "up"
            if r > g.cursor[0]:
                return "down"
            if c < g.cursor[1]:
                return "left"
            if c > g.cursor[1]:
                return "right"
            return "action"

        game = run(PruningGame(random.Random(3)), bot)
        self.assertTrue(game.won)
        self.assertEqual(game.mistakes, 0)

    def test_pruning_wrong_cuts_lose(self):
        game = PruningGame(random.Random(1))
        for _ in range(PruningGame.MAX_MISTAKES):
            leaf = next(
                (r, c) for r, row in enumerate(game.grid) for c, ch in enumerate(row) if ch == "o"
            )
            game.cursor = list(leaf)
            game.handle_key("action")
        self.assertTrue(game.finished)
        self.assertFalse(game.won)

    def test_crow_bot_defends_field(self):
        def bot(g):
            return str(next(iter(g.crows)) + 1) if g.crows else None

        game = run(CrowGame(random.Random(2)), bot)
        self.assertTrue(game.won)
        self.assertGreater(game.shooed, 10)

    def test_egg_catch_bot_wins(self):
        def bot(g):
            if not g.eggs:
                return None
            target = max(g.eggs, key=lambda e: e[1])[0]
            if target < g.basket - 1:
                return "left"
            if target > g.basket + 1:
                return "right"
            return None

        wins = sum(run(EggCatchGame(random.Random(s)), bot).won for s in range(5))
        self.assertGreaterEqual(wins, 4)


class RenderTest(unittest.TestCase):
    def test_render_fits_80_columns(self):
        for cls in GAMES.values():
            game = cls(random.Random(0))
            for _ in range(20):
                game.update(DT)
            lines = game.render()
            self.assertTrue(lines)
            self.assertLessEqual(max(len(line) for line in lines), 70)
            self.assertLessEqual(len(lines), 16)
            self.assertTrue(game.status_line())


if __name__ == "__main__":
    unittest.main()
