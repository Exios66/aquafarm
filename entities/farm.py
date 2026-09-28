import time

from entities.care_entity import CareEntity
from homestead_config import SEASONS


class CropSlot:
    """One of three simultaneous field plots."""

    stage_list = ["seed", "sprout", "growing", "harvest"]
    life_stages = (
        3600 * 24,
        3600 * 24 * 2,
        3600 * 24 * 4,
    )

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
            return 3600 * 2
        return 0

    def growth_step(self, mult):
        if not self.planted or self.stage >= len(self.stage_list) - 1:
            return
        self.ticks += mult
        threshold = self.life_stages[min(self.stage, len(self.life_stages) - 1)]
        if self.ticks >= threshold:
            self.stage += 1

    def art_basename(self, domain, species_name):
        if not self.planted:
            return "homestead_idle"
        stage = self.stage_list[self.stage].replace(" ", "_")
        sp = species_name.replace(" ", "_")
        return f"{domain}_{sp}_{stage}"


class FarmField(CareEntity):
    domain = "farm"
    species_list = ["carrot", "wheat", "tomato", "corn", "pumpkin", "sunflower"]
    stage_list = CropSlot.stage_list
    primary_care = "water"
    extra_care_verbs = ["harvest", "fertilize"]

    life_stages = CropSlot.life_stages
    NUM_SLOTS = 3

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
            self.slots[0].plant(max(0, min(int(species), len(self.species_list) - 1)))

    def migrate_properties(self):
        super().migrate_properties()
        if not hasattr(self, "slots") or not self.slots:
            sp = self.species
            self.slots = [CropSlot() for _ in range(self.NUM_SLOTS)]
            self.slots[0].plant(sp)
            for i in range(1, self.NUM_SLOTS):
                self.slots[i] = CropSlot()
        else:
            for slot in self.slots:
                slot.migrate(len(self.species_list))
        if not hasattr(self, "active_slot"):
            self.active_slot = 0
        if not hasattr(self, "soil_quality"):
            self.soil_quality = 70
        if not hasattr(self, "season_phase"):
            self.season_phase = 0
        if not hasattr(self, "compost"):
            self.compost = 0
        if not hasattr(self, "harvest_streak"):
            self.harvest_streak = 0
        if not hasattr(self, "last_action"):
            self.last_action = "field ready"
        if not hasattr(self, "total_harvests"):
            self.total_harvests = 0
        self.active_slot = max(0, min(self.active_slot, self.NUM_SLOTS - 1))

    def season(self):
        idx = self.season_phase % len(SEASONS)
        return SEASONS[idx]

    def season_growth_mult(self):
        return self.season()["growth"]

    def soil_growth_mult(self):
        return 0.75 + (self.soil_quality / 100.0) * 0.35

    def _slot(self):
        return self.slots[self.active_slot]

    def advance_season(self):
        self.season_phase = (self.season_phase + 1) % len(SEASONS)
        self.last_action = f"season → {self.season()['label']}"

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
        if self.compost < 1:
            return False
        self.perform_care("fertilize")
        return True

    def select_slot(self, index):
        if 0 <= index < self.NUM_SLOTS:
            self.active_slot = index
            return True
        return False

    def plant_crop(self, species_index=None):
        slot = self._slot()
        if not slot.is_empty():
            return False
        if species_index is None:
            species_index = self.species
        species_index = max(0, min(int(species_index), len(self.species_list) - 1))
        bonus = slot.rotation_bonus_ticks(species_index)
        slot.plant(species_index, rotation_bonus_ticks=bonus)
        name = self.species_list[species_index]
        if bonus:
            self.last_action = f"planted {name} (rotation +)"
        else:
            self.last_action = f"planted {name}"
        return True

    def try_harvest(self, slot_index=None):
        idx = self.active_slot if slot_index is None else slot_index
        if idx < 0 or idx >= self.NUM_SLOTS:
            return False
        slot = self.slots[idx]
        if not slot.is_mature():
            return False
        self.perform_care("harvest")
        slot.clear_after_harvest()
        self.soil_quality = max(0, self.soil_quality - 5)
        self.harvest_streak += 1
        self.total_harvests += 1
        if self.harvest_streak % 3 == 0:
            self.compost += 1
        self.advance_season()
        self.last_action = f"harvested slot {idx + 1}"
        bonus = 25 * (1 + 0.2 * (self.generation - 1))
        self.ticks += bonus
        return True

    def is_mature(self):
        return self._slot().is_mature()

    def tick_life(self, generation_bonus):
        if self.dead:
            return
        neglected = not self.primary_care_fresh()
        if neglected:
            self.soil_quality = max(0, self.soil_quality - 0.02)
        if self.primary_care_fresh():
            score_inc = 0.3 * (1 + generation_bonus)
            self.ticks += score_inc
            mult = self.season_growth_mult() * self.soil_growth_mult()
            for slot in self.slots:
                if slot.planted:
                    slot.growth_step(mult * (1 + generation_bonus * 0.1))
        self.dead_check()

    def journal_line(self):
        season = self.season()["label"]
        return (
            f"journal: {self.last_action} | soil {int(self.soil_quality)}%"
            f" | {season} | compost {self.compost}"
        )

    def parse_description(self):
        if self.dead:
            return "rest in peace, field"
        slot = self._slot()
        if slot.is_empty():
            sp = "(empty plot)"
        else:
            sp = self.species_list[slot.species]
        stage = self.stage_list[slot.stage] if slot.planted else "fallow"
        return f"slot {self.active_slot + 1}: {stage} {sp}"

    def art_basename(self):
        if self.dead:
            return "rip"
        slot = self._slot()
        if slot.is_empty():
            return "homestead_idle"
        name = self.species_list[slot.species]
        return slot.art_basename(self.domain, name)

    def to_json_dict(self):
        data = super().to_json_dict()
        data.update(
            {
                "soil_quality": int(self.soil_quality),
                "season": self.season()["id"],
                "season_phase": self.season_phase,
                "compost": self.compost,
                "harvest_streak": self.harvest_streak,
                "active_slot": self.active_slot,
                "last_action": self.last_action,
                "journal": self.journal_line(),
                "slots": [
                    {
                        "species": self.species_list[s.species] if s.planted else None,
                        "stage": self.stage_list[s.stage] if s.planted else "empty",
                        "ticks": int(s.ticks),
                        "planted": s.planted,
                    }
                    for s in self.slots
                ],
            }
        )
        return data


# Backward-compatible alias
FarmPlot = FarmField
