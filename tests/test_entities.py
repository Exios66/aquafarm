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
        self.assertIn("flavor", data)

    def test_fish_species_count(self):
        from entities.aquarium import FishTank

        self.assertGreaterEqual(len(FishTank.species_list), 9)

    def test_farm_harvest_flow(self):
        from homestead import Homestead

        hs = Homestead()
        slot = hs.farm.slots[0]
        slot.planted = True
        slot.species = 0
        slot.stage = len(hs.farm.stage_list) - 1
        gen_before = hs.generation
        self.assertTrue(hs.harvest_entity("farm"))
        # crop harvests fill the basket; generations come from retiring friends
        self.assertEqual(hs.generation, gen_before)
        self.assertGreater(hs.progress.inventory.get("carrot", 0), 0)
        self.assertFalse(slot.planted)

    def test_farm_rotation_bonus(self):
        from entities.farm import CropSlot

        slot = CropSlot()
        slot.last_harvested_species = 0
        self.assertGreater(slot.rotation_bonus_ticks(1), 0)
        self.assertEqual(slot.rotation_bonus_ticks(0), 0)

    def test_farm_soil_and_season(self):
        from entities.farm import FarmField

        field = FarmField()
        field.perform_care("water")
        self.assertGreater(field.soil_quality, 70)
        field.compost = 1
        self.assertTrue(field.try_fertilize())
        self.assertIn("journal", field.to_json_dict())

    def test_horse_species_art_basename(self):
        from entities.livestock import LivestockPen

        pen = LivestockPen(species=2)
        self.assertEqual(pen.species_list[pen.species], "horse")
        self.assertEqual(pen.art_basename(), "livestock_horse_baby")

    def test_guest_timestamps_apply(self):
        from homestead import Homestead

        hs = Homestead()
        now = int(__import__("time").time())
        hs.apply_guest_timestamps([now - 100])
        self.assertTrue(hs.aquarium.primary_care_fresh())

    def test_livestock_collect(self):
        from entities.livestock import LivestockPen

        pen = LivestockPen(species=0)
        pen.stage = len(pen.stage_list) - 1
        pen.perform_care("feed")
        before = pen.ticks
        bonus = pen.collect_produce()
        self.assertGreater(bonus, 0)
        self.assertGreater(pen.ticks, before)

    def test_horse_ride_and_llama_shear(self):
        from entities.livestock import LivestockPen

        horse = LivestockPen(species=2)
        horse.stage = 2
        horse.perform_care("groom")
        self.assertGreater(horse.ride_training(), 0)

        sheep = LivestockPen(species=3)
        sheep.stage = 2
        sheep.perform_care("feed")
        self.assertGreater(sheep.shear_wool(), 0)
        self.assertEqual(sheep.shear_wool(), 0, "shearing has a cooldown")

        llama = LivestockPen(species=5)
        self.assertEqual(llama.species_name(), "llama")
        llama.stage = 2
        llama.perform_care("feed")
        self.assertGreater(llama.shear_wool(), 0)

    def test_homestead_pickle_roundtrip(self):
        from data_manager import DataManager
        from homestead import Homestead

        hs = Homestead()
        hs.aquarium.apply_customization(2, "Neon", "speckled")
        hs.tank_theme_index = 2
        hs.backdrop_index = 1
        hs.pending_fish_setup = False
        hs.farm.slots[1].plant(2)
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
            self.assertEqual(len(loaded.farm.slots), 3)

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
        # score survives the reset, but growth must start over
        fish.tick_life(0.0, dt=10)
        self.assertEqual(fish.stage, 0)


class ArtFilesTest(unittest.TestCase):
    def test_farm_livestock_art(self):
        art_dir = os.path.join(ROOT, "art")
        for name in (
            "farm_carrot_harvest.txt",
            "farm_tomato_harvest.txt",
            "farm_pumpkin_growing.txt",
            "livestock_chicken_grown.txt",
            "livestock_cow_grown.txt",
            "livestock_horse_grown.txt",
            "livestock_llama_grown.txt",
        ):
            self.assertTrue(os.path.isfile(os.path.join(art_dir, name)))

    def test_new_fish_art(self):
        art_dir = os.path.join(ROOT, "art")
        for sp in ("clownfish", "koi", "axolotl"):
            for stage in ("egg", "fry", "juvenile", "adult"):
                name = f"aquarium_{sp}_{stage}.txt"
                self.assertTrue(os.path.isfile(os.path.join(art_dir, name)))


if __name__ == "__main__":
    unittest.main()
