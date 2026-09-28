"""Shared daily-care lifecycle for homestead entities."""

import random
import time
import uuid

CARE_WINDOW_SEC = 24 * 3600
NEGLECT_DEATH_SEC = 5 * 24 * 3600


class CareEntity:
    """Base class: 24h care window, 5-day neglect death, tick-based growth."""

    domain = "base"
    species_list = ["generic"]
    stage_list = ["seed"]
    primary_care = "care"
    extra_care_verbs = []

    # tick thresholds per stage transition (seconds of active care time)
    life_stages = (3600 * 24, (3600 * 24) * 3, (3600 * 24) * 7)

    def __init__(self, generation=1, species=None):
        self.entity_id = str(uuid.uuid4())
        if species is None:
            self.species = random.randint(0, len(self.species_list) - 1)
        else:
            self.species = max(0, min(int(species), len(self.species_list) - 1))
        self.stage = 0
        self.ticks = 0
        self.dead = False
        self.generation = generation
        self.start_time = int(time.time())
        self.last_time = int(time.time())
        self.display_name = ""
        self.color_variant = "classic"
        now = int(time.time())
        # force first-day care like botany
        self.care_timestamps = {self.primary_care: now - CARE_WINDOW_SEC - 1}
        for verb in self.extra_care_verbs:
            self.care_timestamps[verb] = now - CARE_WINDOW_SEC - 1

    def migrate_properties(self):
        if not hasattr(self, "care_timestamps"):
            now = int(time.time())
            self.care_timestamps = {self.primary_care: now - CARE_WINDOW_SEC - 1}
        if not hasattr(self, "display_name"):
            self.display_name = ""
        if not hasattr(self, "color_variant"):
            self.color_variant = "classic"

    def last_care(self, verb=None):
        verb = verb or self.primary_care
        return self.care_timestamps.get(verb, 0)

    def perform_care(self, verb):
        if self.dead:
            return
        if verb not in ([self.primary_care] + self.extra_care_verbs):
            return
        self.care_timestamps[verb] = int(time.time())

    def primary_care_fresh(self):
        delta = int(time.time()) - self.last_care(self.primary_care)
        return delta <= CARE_WINDOW_SEC

    def care_fresh(self, verb):
        delta = int(time.time()) - self.last_care(verb)
        return delta <= CARE_WINDOW_SEC

    def dead_check(self):
        if self.dead:
            return True
        delta = int(time.time()) - self.last_care(self.primary_care)
        if delta > NEGLECT_DEATH_SEC:
            self.dead = True
        return self.dead

    def growth(self):
        if self.stage < len(self.stage_list) - 1:
            self.stage += 1

    def parse_description(self):
        species = self.species_list[self.species]
        stage = self.stage_list[self.stage]
        if self.dead:
            label = self.display_name or species
            return f"rest in peace, {label}"
        prefix = self.display_name or species
        variant = ""
        if self.color_variant and self.color_variant != "classic":
            variant = f" ({self.color_variant})"
        return f"{stage} {prefix}{variant}"

    def art_basename(self):
        if self.dead:
            return "rip"
        species = self.species_list[self.species].replace(" ", "_")
        stage = self.stage_list[self.stage].replace(" ", "_")
        return f"{self.domain}_{species}_{stage}"

    def tick_life(self, generation_bonus):
        if self.dead:
            return
        if self.primary_care_fresh():
            score_inc = 1 * (1 + generation_bonus)
            self.ticks += score_inc
            if self.stage < len(self.stage_list) - 1:
                threshold = self.life_stages[min(self.stage, len(self.life_stages) - 1)]
                if self.ticks >= threshold:
                    self.growth()
        self.dead_check()

    def to_json_dict(self):
        return {
            "domain": self.domain,
            "species": self.species_list[self.species],
            "species_index": self.species,
            "stage": self.stage_list[self.stage],
            "ticks": int(self.ticks),
            "dead": self.dead,
            "generation": self.generation,
            "description": self.parse_description(),
            "display_name": self.display_name,
            "color_variant": self.color_variant,
            "last_primary_care": self.last_care(self.primary_care),
        }
