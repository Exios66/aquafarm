"""Coins, inventory, daily tasks, achievements and stats for one homestead."""

import random
import time

from homestead_config import (
    ACHIEVEMENTS,
    DAILY_TASK_BONUS,
    DAILY_TASK_COUNT,
    ITEM_PRICES,
    MINIGAME_DAILY_REWARDS,
    TASK_POOL,
)


def today_stamp(now=None):
    return int(now if now is not None else time.time()) // 86400


class Progress:
    def __init__(self):
        self.coins = 0
        self.inventory = {}
        self.stats = {}
        self.achievements = {}
        self.decorations = []
        self.task_day = None
        self.tasks = []
        self.task_bonus_paid = False
        self.minigame_day = None
        self.minigame_rewards = {}
        self.minigame_best = {}

    def migrate(self):
        defaults = Progress()
        for key, value in vars(defaults).items():
            if not hasattr(self, key):
                setattr(self, key, value)

    # -- coins & inventory --------------------------------------------------

    def earn(self, amount):
        amount = int(amount)
        if amount <= 0:
            return []
        self.coins += amount
        return self.bump("coins_earned", amount)

    def spend(self, amount):
        if amount > self.coins:
            return False
        self.coins -= amount
        return True

    def add_item(self, item, qty=1):
        if qty > 0:
            self.inventory[item] = self.inventory.get(item, 0) + int(qty)

    def remove_item(self, item, qty=1):
        have = self.inventory.get(item, 0)
        if qty <= 0 or have < qty:
            return False
        if have == qty:
            del self.inventory[item]
        else:
            self.inventory[item] = have - qty
        return True

    def item_count(self):
        return sum(self.inventory.values())

    @staticmethod
    def price_of(item):
        return ITEM_PRICES.get(item, 1)

    def inventory_value(self):
        return sum(self.price_of(k) * v for k, v in self.inventory.items())

    # -- stats, tasks, achievements -----------------------------------------

    def bump(self, stat, amount=1):
        """Increment a stat and return notices for anything it unlocked.

        Only ``record`` feeds daily tasks; ``bump`` is also used for totals
        like coins earned that shouldn't count as task activity.
        """
        self.stats[stat] = self.stats.get(stat, 0) + amount
        return self._check_achievements()

    def record(self, event, amount=1, now=None):
        self.refresh_tasks(now)
        notices = []
        for task in self.tasks:
            if task["event"] != event or task["done"]:
                continue
            task["progress"] = min(task["target"], task["progress"] + amount)
            if task["progress"] >= task["target"]:
                task["done"] = True
                notices.append(f"Task done: {task['label']} (+{task['reward']}c)")
                notices.extend(self.earn(task["reward"]))
                notices.extend(self.bump("task_completed"))
        if self.tasks and not self.task_bonus_paid and all(t["done"] for t in self.tasks):
            self.task_bonus_paid = True
            notices.append(f"All daily tasks done! Bonus +{DAILY_TASK_BONUS}c")
            notices.extend(self.earn(DAILY_TASK_BONUS))
        notices.extend(self.bump(event, amount))
        return notices

    def refresh_tasks(self, now=None, rng=None):
        day = today_stamp(now)
        if self.task_day == day and self.tasks:
            return False
        rng = rng or random.Random(day)
        picks = rng.sample(TASK_POOL, min(DAILY_TASK_COUNT, len(TASK_POOL)))
        self.tasks = [dict(t, progress=0, done=False) for t in picks]
        self.task_day = day
        self.task_bonus_paid = False
        return True

    def tasks_done(self):
        return sum(1 for t in self.tasks if t["done"])

    def _check_achievements(self):
        notices = []
        for ach in ACHIEVEMENTS:
            if ach["id"] in self.achievements:
                continue
            if self.stats.get(ach["stat"], 0) >= ach["threshold"]:
                self.achievements[ach["id"]] = int(time.time())
                self.coins += ach["reward"]
                notices.append(f"Achievement: {ach['label']}! (+{ach['reward']}c)")
        return notices

    # -- mini game payouts --------------------------------------------------

    def minigame_rewards_left(self, game_id, now=None):
        day = today_stamp(now)
        if self.minigame_day != day:
            self.minigame_day = day
            self.minigame_rewards = {}
        return max(0, MINIGAME_DAILY_REWARDS - self.minigame_rewards.get(game_id, 0))

    def use_minigame_reward(self, game_id, now=None):
        if self.minigame_rewards_left(game_id, now) <= 0:
            return False
        self.minigame_rewards[game_id] = self.minigame_rewards.get(game_id, 0) + 1
        return True

    def note_best(self, game_id, score):
        if score > self.minigame_best.get(game_id, 0):
            self.minigame_best[game_id] = score
            return True
        return False

    def to_json_dict(self):
        return {
            "coins": self.coins,
            "inventory": dict(self.inventory),
            "stats": dict(self.stats),
            "achievements": sorted(self.achievements),
            "decorations": list(self.decorations),
            "tasks": [
                {"label": t["label"], "progress": t["progress"], "target": t["target"], "done": t["done"]}
                for t in self.tasks
            ],
            "minigame_best": dict(self.minigame_best),
        }
