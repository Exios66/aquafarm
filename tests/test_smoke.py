import importlib
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, ROOT)


class SmokeTest(unittest.TestCase):
    def test_imports(self):
        importlib.import_module("aquafarm")
        importlib.import_module("data_manager")
        importlib.import_module("homestead")
        importlib.import_module("menu_screen")

    def test_homestead_care(self):
        from homestead import Homestead

        hs = Homestead()
        hs.aquarium.perform_care("feed")
        hs.bonsai.perform_care("water")
        self.assertTrue(hs.aquarium.primary_care_fresh())
        self.assertTrue(hs.bonsai.primary_care_fresh())
        self.assertGreaterEqual(hs.total_score(), 0)

    def test_art_files_exist(self):
        art_dir = os.path.join(ROOT, "art")
        required = [
            "aquarium_goldfish_egg.txt",
            "bonsai_maple_seed.txt",
            "homestead_idle.txt",
            "rip.txt",
        ]
        for name in required:
            self.assertTrue(os.path.isfile(os.path.join(art_dir, name)))


if __name__ == "__main__":
    unittest.main()
