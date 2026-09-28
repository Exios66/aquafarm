import time

from entities.care_entity import CareEntity
from homestead_config import CROPS, SEASONS

DAY = 24 * 3600


class CropSlot:
    """One plot in the field. Growth is measured in seconds of watered time."""

    stage_list = ["seed", "sprout", "growing", "harvest"]
    # fraction of a crop's total grow time needed to leave each stage
    stage_fractions = (0.2, 0.5, 1.0)
    # default grow time when a crop is missing from CROPS
    life_stages = (DAY, DAY * 2, DAY * 4)
    ROTATION_BONUS_SEC = 3600 * 2

    def __init__(self, species=0, stage=0, ticks=0, planted=False):
        self.species = species
        self.stage = stage
        self.ticks = ticks
        self.planted = planted
        self.last_harvested_species = None

    def migrate(self, species_list_len):
        self.species = max(0, min(int(self.species), species_list_len - 1))
        self.stage = max(0, min(int(self.stage), len(self.stage_list) - 1))
        if not hasattr(self, "last_harvested_species"):
            self.last_harvested_species = None
        if not hasattr(self, "planted"):
            self.planted = self.stage > 0 or self.ticks > 0

    @classmethod
    def thresholds_for(cls, crop_name):
        info = CROPS.get(crop_name)
        if not info:
            return cls.life_stages
        total = info["days"] * DAY
        return tuple(int(total * f) for f in cls.stage_fractions)

    def is_mature(self):
        return self.planted and self.stage == len(self.stage_list) - 1

    def is_empty(self):
        return not self.planted

    def plant(self, species_index, rotation_bonus_ticks=0):
        self.species = species_index
        self.stage = 0
        self.ticks = rotation_bonus_ticks
        self.planted = True

    def clear_after_harvest(self):
        harvested = self.species
        self.last_harvested_species = harvested
        self.planted = False
        self.stage = 0
        self.ticks = 0
        return harvested

    def rotation_bonus_ticks(self, new_species_index):
        if self.last_harvested_species is None:
            return 0
        if new_species_index != self.last_harvested_species:
            return self.ROTATION_BONUS_SEC
        return 0

    def growth_step(self, amount, thresholds=None):
        if not self.planted or self.stage >= len(self.stage_list) - 1:
            return
        thresholds = thresholds or self.life_stages
        self.ticks += amount
        while self.stage < len(self.stage_list) - 1 and self.ticks >= thresholds[self.stage]:
            self.stage += 1

    def progress(self, thresholds=None):
        thresholds = thresholds or self.life_stages
        if not self.planted:
            return 0.0
        return max(0.0, min(1.0, self.ticks / float(thresholds[-1])))

    def art_basename(self, domain, species_name):
        if not self.planted:
            return "homestead_idle"
        stage = self.stage_list[self.stage].replace(" ", "_")
        sp = species_name.replace(" ", "_")
        return f"{domain}_{sp}_{stage}"


# Legacy name: early saves pickled a single-plot ``FarmPlot``.
FarmPlot = CropSlot


class FarmField(CareEntity):
    """Three-plot field sharing one water schedule, soil and season."""

    domain = "farm"
    species_list = ["carrot", "wheat", "tomato", "corn", "pumpkin", "sunflower"]
    stage_list = CropSlot.stage_list
    primary_care = "water"
    extra_care_verbs = ["harvest", "fertilize"]

    life_stages = CropSlot.life_stages
    NUM_SLOTS = 3
    HARVEST_BONUS_TICKS = 1500

    def __init__(self, generation=1, species=None):
        super().__init__(generation=generation, species=species)
        self.slots = [CropSlot() for _ in range(self.NUM_SLOTS)]
        self.active_slot = 0
        self.soil_quality = 70
        self.season_phase = 0
        self.compost = 0
        self.harvest_streak = 0
        self.last_action = "field ready"
        self.total_harvests = 0
        if species is not None:
            self.slots[0].plant(self.species)

    def migrate_properties(self):
        super().migrate_properties()
        if not hasattr(self, "slots") or not self.slots:
            self.slots = [CropSlot() for _ in range(self.NUM_SLOTS)]
        for slot in self.slots:
            slot.migrate(len(self.species_list))
        while len(self.slots) < self.NUM_SLOTS:
            self.slots.append(CropSlot())
        defaults = {
            "active_slot": 0,
            "soil_quality": 70,
            "season_phase": 0,
            "compost": 0,
            "harvest_streak": 0,
            "last_action": "field ready",
            "total_harvests": 0,
        }
        for key, value in defaults.items():
            if not hasattr(self, key):
                setattr(self, key, value)
        self.active_slot = max(0, min(self.active_slot, self.NUM_SLOTS - 1))
        self._sync_stage()

    # -- field state --------------------------------------------------------

    def season(self):
        return SEASONS[self.season_phase % len(SEASONS)]

    def season_growth_mult(self):
        return self.season()["growth"]

    def soil_growth_mult(self):
        return 0.75 + (self.soil_quality / 100.0) * 0.35

    def growth_rate(self):
        return self.season_growth_mult() * self.soil_growth_mult()

    def _slot(self):
        return self.slots[self.active_slot]

    def active(self):
        return self._slot()

    def crop_name(self, slot):
        return self.species_list[slot.species]

    def thresholds(self, slot):
        return CropSlot.thresholds_for(self.crop_name(slot))

    def _sync_stage(self):
        """Mirror the active slot so generic UI (stage, art) stays meaningful."""
        slot = self._slot()
        self.stage = slot.stage if slot.planted else 0

    def planted_count(self):
        return sum(1 for s in self.slots if s.planted)

    def mature_slots(self):
        return [i for i, s in enumerate(self.slots) if s.is_mature()]

    def is_mature(self):
        return not self.dead and bool(self.mature_slots())

    def advance_season(self):
        self.season_phase = (self.season_phase + 1) % len(SEASONS)
        self.last_action = f"season → {self.season()['label']}"

    # -- growth -------------------------------------------------------------

    def advance(self, seconds, generation_bonus=0.0):
        if self.dead or seconds <= 0:
            return
        amount = seconds * (1 + generation_bonus) * self.growth_rate()
        for slot in self.slots:
            slot.growth_step(amount, self.thresholds(slot))
        # the field only scores while something is growing
        if self.planted_count():
            self.ticks += amount
            self.growth_ticks += amount
        self._sync_stage()

    def boost_growth(self, seconds):
        if self.dead:
            return
        for slot in self.slots:
            slot.growth_step(seconds, self.thresholds(slot))
        self.ticks += seconds
        self._sync_stage()

    # -- actions ------------------------------------------------------------

    def perform_care(self, verb):
        if self.dead:
            return
        if verb == "water":
            super().perform_care("water")
            self.soil_quality = min(100, self.soil_quality + 2)
            self.last_action = "watered field"
        elif verb == "fertilize":
            if self.compost < 1:
                return
            self.compost -= 1
            self.soil_quality = min(100, self.soil_quality + 12)
            self.care_timestamps["fertilize"] = int(time.time())
            self.last_action = "fertilized (+soil)"
        elif verb in self.extra_care_verbs:
            self.care_timestamps[verb] = int(time.time())

    def water_all_slots(self):
        self.perform_care("water")

    def try_fertilize(self):
        if self.dead or self.compost < 1:
            return False
        self.perform_care("fertilize")
        return True

    def select_slot(self, index):
        if 0 <= index < self.NUM_SLOTS:
            self.active_slot = index
            self._sync_stage()
            return True
        return False

    def plant_crop(self, species_index=None):
        if self.dead:
            return False
        slot = self._slot()
        if not slot.is_empty():
            return False
        if species_index is None:
            species_index = self.species
        species_index = max(0, min(int(species_index), len(self.species_list) - 1))
        bonus = slot.rotation_bonus_ticks(species_index)
        slot.plant(species_index, rotation_bonus_ticks=bonus)
        name = self.species_list[species_index]
        self.last_action = f"planted {name}" + (" (rotation +)" if bonus else "")
        self._sync_stage()
        return True

    def harvest_yield(self):
        qty = 2
        if self.soil_quality >= 80:
            qty += 1
        if self.season()["id"] == "summer":
            qty += 1
        return qty

    def try_harvest(self, slot_index=None):
        """Harvest one mature slot. Returns (crop_name, qty) or None."""
        idx = self.active_slot if slot_index is None else slot_index
        if self.dead or idx < 0 or idx >= self.NUM_SLOTS:
            return None
        slot = self.slots[idx]
        if not slot.is_mature():
            return None
        qty = self.harvest_yield()
        self.perform_care("harvest")
        crop = self.species_list[slot.clear_after_harvest()]
        self.soil_quality = max(0, self.soil_quality - 5)
        self.harvest_streak += 1
        self.total_harvests += 1
        if self.harvest_streak % 3 == 0:
            self.compost += 1
        self.last_action = f"harvested {qty} {crop} from plot {idx + 1}"
        self.ticks += self.HARVEST_BONUS_TICKS * (1 + 0.2 * (self.generation - 1))
        self._sync_stage()
        return crop, qty

    # -- presentation -------------------------------------------------------

    def journal_line(self):
        season = self.season()["label"]
        return (
            f"{season} | soil {self.soil_quality}% | compost {self.compost}"
            f" | plot {self.active_slot + 1} | {self.last_action}"
        )

    def slot_line(self, index):
        slot = self.slots[index]
        marker = ">" if index == self.active_slot else " "
        if not slot.planted:
            return f"{marker}plot {index + 1}: empty"
        pct = int(slot.progress(self.thresholds(slot)) * 100)
        stage = self.stage_list[slot.stage]
        return f"{marker}plot {index + 1}: {self.crop_name(slot)} {stage} {pct}%"

    def parse_description(self):
        if self.dead:
            return "rest in peace, field"
        planted = [s for s in self.slots if s.planted]
        if not planted:
            return "empty field"
        names = ", ".join(
            f"{self.stage_list[s.stage]} {self.crop_name(s)}" for s in planted
        )
        return names

    def art_basename(self):
        if self.dead:
            return "rip"
        slot = self._slot()
        return slot.art_basename(self.domain, self.crop_name(slot))

    def to_json_dict(self):
        data = super().to_json_dict()
        data.update(
            {
                "soil_quality": self.soil_quality,
                "season": self.season()["id"],
                "compost": self.compost,
                "harvest_streak": self.harvest_streak,
                "total_harvests": self.total_harvests,
                "active_slot": self.active_slot,
                "journal": self.journal_line(),
                "slots": [
                    {
                        "planted": s.planted,
                        "crop": self.crop_name(s) if s.planted else None,
                        "stage": self.stage_list[s.stage] if s.planted else None,
                        "progress": round(s.progress(self.thresholds(s)), 3),
                    }
                    for s in self.slots
                ],
            }
        )
        return data
