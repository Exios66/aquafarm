import os
import pickle
import sys
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, ROOT)

from homestead import Homestead
from homestead_config import ACHIEVEMENTS, DAILY_TASK_COUNT, TASK_POOL
from progression import Progress


def grown(hs, area):
    entity = hs.entity_for_area(area)
    entity.stage = len(entity.stage_list) - 1
    entity.growth_ticks = entity.life_stages[-1]
    return entity


class ProgressTest(unittest.TestCase):
    def test_daily_tasks_rotate_by_day(self):
        progress = Progress()
        progress.refresh_tasks(now=0)
        self.assertEqual(len(progress.tasks), DAILY_TASK_COUNT)
        progress.tasks[0]["progress"] = 1
        self.assertFalse(progress.refresh_tasks(now=3600), "same day keeps tasks")
        self.assertEqual(progress.tasks[0]["progress"], 1)
        self.assertTrue(progress.refresh_tasks(now=86400 * 5))
        self.assertEqual(len({t["id"] for t in progress.tasks}), DAILY_TASK_COUNT)
        self.assertTrue(all(t["progress"] == 0 for t in progress.tasks))

    def test_task_completion_pays_and_bonus(self):
        progress = Progress()
        progress.refresh_tasks()
        for task in list(progress.tasks):
            progress.record(task["event"], task["target"])
        self.assertTrue(all(t["done"] for t in progress.tasks))
        self.assertTrue(progress.task_bonus_paid)
        self.assertGreater(progress.coins, 0)
        self.assertEqual(progress.stats["task_completed"], DAILY_TASK_COUNT)

    def test_every_task_event_is_recorded_by_the_game(self):
        # guard against tasks nobody can finish
        sources = ""
        for name in ("homestead.py", "menu_screen.py"):
            with open(os.path.join(ROOT, name)) as handle:
                sources += handle.read()
        for task in TASK_POOL:
            self.assertIn(f'"{task["event"]}"', sources, task["id"])
        for ach in ACHIEVEMENTS:
            if ach["stat"] in ("coins_earned", "task_completed"):
                continue
            self.assertIn(f'"{ach["stat"]}"', sources, ach["id"])

    def test_achievement_unlocks_once(self):
        progress = Progress()
        notices = progress.record("fish_fed")
        self.assertTrue(any("First Nibble" in n for n in notices))
        self.assertFalse(any("First Nibble" in n for n in progress.record("fish_fed")))
        self.assertEqual(list(progress.achievements), ["first_nibble"])

    def test_inventory(self):
        progress = Progress()
        progress.add_item("egg", 3)
        self.assertTrue(progress.remove_item("egg", 2))
        self.assertFalse(progress.remove_item("egg", 2))
        self.assertTrue(progress.remove_item("egg"))
        self.assertNotIn("egg", progress.inventory)

    def test_migrate_fills_new_fields(self):
        progress = Progress()
        del progress.minigame_best
        progress.migrate()
        self.assertEqual(progress.minigame_best, {})


class HomesteadActionTest(unittest.TestCase):
    def test_care_actions_log_events_once_per_window(self):
        hs = Homestead()
        hs.do_feed_fish()
        hs.do_feed_fish()
        self.assertEqual(hs.progress.stats["fish_fed"], 1)
        self.assertTrue(hs.aquarium.primary_care_fresh())

    def test_farm_loop_plant_grow_harvest_sell(self):
        hs = Homestead()
        hs.do_water_crops()
        hs.farm.species = 0  # carrot
        self.assertIn("planted", hs.do_plant())
        self.assertIn("already", hs.do_plant())
        hs.farm.advance(86400 * 3)
        self.assertTrue(hs.farm.slots[0].is_mature())
        self.assertIn("harvested", hs.do_harvest())
        carrots = hs.progress.inventory["carrot"]
        self.assertGreaterEqual(carrots, 2)
        before = hs.progress.coins
        self.assertIn("sold", hs.do_sell("carrot"))
        self.assertGreater(hs.progress.coins, before)
        self.assertNotIn("carrot", hs.progress.inventory)

    def test_crop_rotation_head_start(self):
        hs = Homestead()
        slot = hs.farm.slots[0]
        slot.last_harvested_species = 0
        hs.farm.species = 1
        hs.do_plant()
        self.assertGreater(slot.ticks, 0)

    def test_growth_needs_fresh_care(self):
        hs = Homestead()
        hs.farm.species = 0
        hs.do_plant()
        hs.life_step(dt=3600)
        self.assertEqual(hs.farm.slots[0].ticks, 0, "unwatered crops don't grow")
        hs.do_water_crops()
        hs.life_step(dt=3600)
        self.assertGreater(hs.farm.slots[0].ticks, 0)

    def test_livestock_produce_and_cooldown(self):
        hs = Homestead()
        hs.livestock.apply_customization(1)  # cow
        grown(hs, "livestock")
        self.assertIn("feed", hs.do_gather_produce())
        hs.do_feed_animal()
        compost = hs.farm.compost
        self.assertIn("milk", hs.do_gather_produce())
        self.assertEqual(hs.progress.inventory["milk"], 2)
        self.assertEqual(hs.farm.compost, compost + 1)
        self.assertIn("ready again", hs.do_gather_produce())

    def test_horse_needs_grooming(self):
        hs = Homestead()
        hs.livestock.apply_customization(2)
        grown(hs, "livestock")
        hs.do_feed_animal()
        self.assertIn("groom", hs.do_gather_produce())
        hs.do_groom()
        self.assertIn("ribbon", hs.do_gather_produce())

    def test_prune_once_per_day(self):
        hs = Homestead()
        self.assertIn("seed", hs.do_prune())
        hs.bonsai.stage = 1
        self.assertIn("clipping", hs.do_prune())
        self.assertIn("already", hs.do_prune())

    def test_bonsai_harvest_new_generation(self):
        hs = Homestead()
        grown(hs, "bonsai")
        gen = hs.generation
        self.assertIn("new seed", hs.do_new_start("bonsai"))
        self.assertEqual(hs.generation, gen + 1)
        self.assertEqual(hs.progress.inventory["bonsai"], 1)
        self.assertEqual(hs.bonsai.stage, 0)
        self.assertEqual(hs.progress.stats["generation_up"], 1)

    def test_dead_friend_can_be_replaced(self):
        hs = Homestead()
        hs.livestock.dead = True
        gen = hs.generation
        self.assertTrue(hs.can_restart("livestock"))
        hs.do_new_start("livestock")
        self.assertFalse(hs.livestock.dead)
        self.assertEqual(hs.generation, gen)
        self.assertTrue(hs.pending_barn_setup)

    def test_shop_supply_and_decoration(self):
        hs = Homestead()
        self.assertIn("need", hs.do_buy("compost"))
        hs.progress.coins = 500
        compost = hs.farm.compost
        self.assertIn("bought", hs.do_buy("compost"))
        self.assertEqual(hs.farm.compost, compost + 1)
        self.assertIn("bought", hs.do_buy("castle"))
        self.assertIn("already own", hs.do_buy("castle"))
        self.assertIn("castle", hs.progress.decorations)

    def test_sell_all(self):
        hs = Homestead()
        hs.progress.add_item("egg", 4)
        hs.progress.add_item("wool", 1)
        hs.do_sell_all()
        self.assertEqual(hs.progress.inventory, {})
        self.assertGreaterEqual(hs.progress.coins, 4 * 5 + 14)

    def test_minigame_rewards_capped_per_day(self):
        from minigames import FishingGame

        hs = Homestead()
        game = FishingGame()
        game.finish(True, "test")
        for _ in range(3):
            lines = hs.finish_minigame(game)
            self.assertTrue(any("coins" in line for line in lines))
        lines = hs.finish_minigame(game)
        self.assertTrue(any("for fun" in line for line in lines))
        self.assertEqual(hs.progress.inventory["river fish"], 3)
        self.assertEqual(hs.progress.stats["minigame_won"], 4)

    def test_offline_growth_limited_to_care_window(self):
        hs = Homestead()
        hs.do_feed_fish()
        fish = hs.aquarium
        fish.last_time = int(time.time())
        hs.refresh_offline_ticks(now=int(time.time()) + 3 * 86400)
        # only the first 24h after feeding count
        self.assertLessEqual(fish.growth_ticks, 86400 * 1.3)
        self.assertGreater(fish.growth_ticks, 86400 * 0.5)
        self.assertGreaterEqual(fish.stage, 1)

    def test_attention_list(self):
        hs = Homestead()
        todo = hs.attention_list()
        self.assertIn("aquarium: feed the fish", todo)
        self.assertTrue(hs.area_needs_attention("farm"))

    def test_pickle_drops_runtime_state(self):
        hs = Homestead()
        hs.progress.coins = 42
        loaded = pickle.loads(pickle.dumps(hs, protocol=2))
        self.assertEqual(loaded.progress.coins, 42)
        with loaded.lock:
            pass
        self.assertIsNone(loaded._life_thread)

    def test_migrate_old_save_without_progress(self):
        hs = Homestead()
        del hs.progress
        del hs.aquarium.growth_ticks
        hs.migrate_properties()
        self.assertEqual(hs.progress.coins, 0)
        self.assertEqual(hs.aquarium.growth_ticks, hs.aquarium.ticks)


if __name__ == "__main__":
    unittest.main()
