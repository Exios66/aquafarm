import json
import os
import pickle
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, ROOT)


class EntityPersistenceTest(unittest.TestCase):
    def test_fish_customization_json(self):
        from entities.aquarium import FishTank

        fish = FishTank(generation=2, species=1)
        fish.apply_customization(1, display_name="Bubbles", color_variant="golden")
        data = fish.to_json_dict()
        self.assertEqual(data["species"], "betta")
        self.assertEqual(data["display_name"], "Bubbles")
        self.assertEqual(data["color_variant"], "golden")
        self.assertIn("tank_health", data)

    def test_farm_harvest_flow(self):
        from entities.farm import FarmPlot
        from homestead import Homestead

        hs = Homestead()
        hs.farm.stage = len(hs.farm.stage_list) - 1
        self.assertTrue(hs.farm.try_harvest())
        self.assertTrue(hs.harvest_entity("farm"))
        self.assertEqual(hs.farm.stage, 0)
        self.assertGreater(hs.generation, 1)

    def test_livestock_collect(self):
        from entities.livestock import LivestockPen

        pen = LivestockPen(species=0)
        pen.stage = len(pen.stage_list) - 1
        pen.perform_care("feed")
        before = pen.ticks
        bonus = pen.collect_produce()
        self.assertGreater(bonus, 0)
        self.assertGreater(pen.ticks, before)

    def test_homestead_pickle_roundtrip(self):
        from data_manager import DataManager
        from homestead import Homestead

        hs = Homestead()
        hs.aquarium.apply_customization(2, "Neon", "speckled")
        hs.tank_theme_index = 2
        hs.backdrop_index = 1
        hs.pending_fish_setup = False
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "save.dat")
            with open(path, "wb") as handle:
                pickle.dump(hs, handle, protocol=2)
            with open(path, "rb") as handle:
                loaded = pickle.load(handle)
            loaded.migrate_properties()
            self.assertEqual(loaded.aquarium.display_name, "Neon")
            self.assertEqual(loaded.tank_theme()["id"], "coral_reef")
            self.assertEqual(loaded.backdrop()["id"], "mountain")

    def test_aquarium_breed_requires_adult(self):
        from entities.aquarium import FishTank

        fish = FishTank()
        self.assertFalse(fish.breed_spawn())
        fish.stage = len(fish.stage_list) - 1
        fish.perform_care("feed")
        fish.perform_care("clean")
        fish.perform_care("check_water")
        fish.tank_health = 90
        fish.algae_level = 0
        self.assertTrue(fish.breed_spawn())
        self.assertEqual(fish.stage, 0)


class ArtFilesTest(unittest.TestCase):
    def test_farm_livestock_art(self):
        art_dir = os.path.join(ROOT, "art")
        for name in (
            "farm_carrot_harvest.txt",
            "farm_wheat_growing.txt",
            "livestock_chicken_grown.txt",
            "livestock_cow_grown.txt",
        ):
            self.assertTrue(os.path.isfile(os.path.join(art_dir, name)))


if __name__ == "__main__":
    unittest.main()
