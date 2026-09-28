import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, ROOT)

from entities import BonsaiTree, CropSlot, FarmField, FishTank, LivestockPen


class AllArtPresentTest(unittest.TestCase):
    def _missing_for(self, entity):
        missing = []
        art_dir = os.path.join(ROOT, "art")
        for species_index in range(len(entity.species_list)):
            sample = type(entity)(species=species_index)
            for stage_index in range(len(sample.stage_list)):
                sample.stage = stage_index
                path = os.path.join(art_dir, sample.art_basename() + ".txt")
                if not os.path.isfile(path):
                    missing.append(path)
        return missing

    def test_all_domain_art(self):
        for entity in (FishTank(), LivestockPen(), BonsaiTree()):
            missing = self._missing_for(entity)
            self.assertEqual(missing, [], msg=f"missing art: {missing[:5]}")

    def test_all_crop_art(self):
        art_dir = os.path.join(ROOT, "art")
        missing = []
        for name in FarmField.species_list:
            for stage in range(len(CropSlot.stage_list)):
                slot = CropSlot(species=0, stage=stage, planted=True)
                path = os.path.join(art_dir, slot.art_basename("farm", name) + ".txt")
                if not os.path.isfile(path):
                    missing.append(path)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
