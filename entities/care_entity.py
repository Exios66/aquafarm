"""Shared daily-care lifecycle for homestead entities."""

import random
import time
import uuid

CARE_WINDOW_SEC = 24 * 3600
NEGLECT_DEATH_SEC = 5 * 24 * 3600


class CareEntity:
    """Base class: 24h care window, 5-day neglect death, tick-based growth.

    ``ticks`` is the score (never reset); ``growth_ticks`` drives the stage and
    can be reset (e.g. a fish spawn cycle) without losing score. One tick is
    one second of cared-for time, scaled by generation bonus and growth rate.
    """

    domain = "base"
    species_list = ["generic"]
    stage_list = ["seed"]
    primary_care = "care"
    extra_care_verbs = []

    # cumulative growth_ticks needed to leave each stage
    life_stages = (3600 * 24, (3600 * 24) * 3, (3600 * 24) * 7)

    def __init__(self, generation=1, species=None):
        self.entity_id = str(uuid.uuid4())
        if species is None:
            self.species = random.randint(0, len(self.species_list) - 1)
        else:
            self.species = max(0, min(int(species), len(self.species_list) - 1))
        self.stage = 0
        self.ticks = 0
        self.growth_ticks = 0
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
        now = int(time.time())
        if not hasattr(self, "care_timestamps"):
            self.care_timestamps = {self.primary_care: now - CARE_WINDOW_SEC - 1}
        for verb in [self.primary_care] + list(self.extra_care_verbs):
            self.care_timestamps.setdefault(verb, now - CARE_WINDOW_SEC - 1)
        if not hasattr(self, "display_name"):
            self.display_name = ""
        if not hasattr(self, "color_variant"):
            self.color_variant = "classic"
        if not hasattr(self, "growth_ticks"):
            self.growth_ticks = self.ticks
        self.species = max(0, min(int(self.species), len(self.species_list) - 1))
        self.stage = max(0, min(int(self.stage), len(self.stage_list) - 1))

    # -- care ---------------------------------------------------------------

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
        return self.care_fresh(self.primary_care)

    def care_fresh(self, verb):
        delta = int(time.time()) - self.last_care(verb)
        return delta <= CARE_WINDOW_SEC

    def care_pct(self, verb=None):
        delta = int(time.time()) - self.last_care(verb)
        return int(max(0.0, 1.0 - delta / CARE_WINDOW_SEC) * 100)

    def seconds_since(self, verb):
        return int(time.time()) - self.last_care(verb)

    def needs_care(self):
        return not self.dead and not self.primary_care_fresh()

    def dead_check(self):
        if self.dead:
            return True
        delta = int(time.time()) - self.last_care(self.primary_care)
        if delta > NEGLECT_DEATH_SEC:
            self.dead = True
        return self.dead

    # -- growth -------------------------------------------------------------

    def is_mature(self):
        return not self.dead and self.stage >= len(self.stage_list) - 1

    def growth_rate(self):
        """Multiplier on growth; subclasses fold in tank health, soil, etc."""
        return 1.0

    def growth(self):
        if self.stage < len(self.stage_list) - 1:
            self.stage += 1

    def _grow_to_threshold(self):
        while self.stage < len(self.stage_list) - 1:
            threshold = self.life_stages[min(self.stage, len(self.life_stages) - 1)]
            if self.growth_ticks < threshold:
                break
            self.growth()

    def advance(self, seconds, generation_bonus=0.0):
        """Credit ``seconds`` of cared-for time: score and growth."""
        if self.dead or seconds <= 0:
            return
        amount = seconds * (1 + generation_bonus) * self.growth_rate()
        self.ticks += amount
        self.growth_ticks += amount
        self._grow_to_threshold()

    def boost_growth(self, seconds):
        """Shop/minigame reward: extra growth time plus the matching score."""
        if self.dead:
            return
        self.ticks += seconds
        self.growth_ticks += seconds
        self._grow_to_threshold()

    def tick_life(self, generation_bonus, dt=1.0):
        if self.dead:
            return
        if self.primary_care_fresh():
            self.advance(dt, generation_bonus)
        self.dead_check()

    def stage_progress(self):
        """0..1 progress through the current stage (1.0 when mature)."""
        if self.stage >= len(self.stage_list) - 1:
            return 1.0
        lo = self.life_stages[self.stage - 1] if self.stage > 0 else 0
        hi = self.life_stages[min(self.stage, len(self.life_stages) - 1)]
        if hi <= lo:
            return 1.0
        return max(0.0, min(1.0, (self.growth_ticks - lo) / float(hi - lo)))

    # -- presentation -------------------------------------------------------

    def species_name(self):
        return self.species_list[self.species]

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
        if self.display_name:
            return f"{stage} {species} {prefix}{variant}"
        return f"{stage} {prefix}{variant}"

    def art_basename(self):
        if self.dead:
            return "rip"
        species = self.species_list[self.species].replace(" ", "_")
        stage = self.stage_list[self.stage].replace(" ", "_")
        return f"{self.domain}_{species}_{stage}"

    def entity_age_seconds(self):
        return max(0, int(time.time()) - self.start_time)

    def apply_customization(self, species_index, display_name=None, color_variant=None):
        self.species = max(0, min(int(species_index), len(self.species_list) - 1))
        if display_name is not None:
            self.display_name = str(display_name)[:32]
        if color_variant is not None:
            self.color_variant = str(color_variant)

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
            "age_seconds": self.entity_age_seconds(),
        }
