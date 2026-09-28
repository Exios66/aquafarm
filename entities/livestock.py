import time

from entities.care_entity import CareEntity
from homestead_config import LIVESTOCK_PRODUCE


class LivestockPen(CareEntity):
    domain = "livestock"
    species_list = ["chicken", "cow", "horse", "sheep", "pig", "llama"]
    stage_list = ["baby", "young", "grown"]
    primary_care = "feed"
    extra_care_verbs = ["collect", "groom", "ride", "shear", "forage"]

    life_stages = (
        3600 * 24,
        3600 * 24 * 4,
    )

    def __init__(self, generation=1, species=None):
        super().__init__(generation=generation, species=species)
        self.produce_collected = 0
        self.training_sessions = 0

    def migrate_properties(self):
        super().migrate_properties()
        if not hasattr(self, "produce_collected"):
            self.produce_collected = 0
        if not hasattr(self, "training_sessions"):
            self.training_sessions = 0

    # -- produce ------------------------------------------------------------

    def produce_info(self):
        return LIVESTOCK_PRODUCE[self.species_name()]

    def primary_care_for_species(self):
        return self.primary_care

    def growth_rate(self):
        # a groomed animal is a happy animal
        return 1.1 if self.care_fresh("groom") else 1.0

    def produce_cooldown_left(self):
        info = self.produce_info()
        return max(0, info["cooldown_h"] * 3600 - self.seconds_since(info["verb"]))

    def produce_blocker(self):
        """Why produce can't be gathered right now, or None if it can."""
        info = self.produce_info()
        if self.dead:
            return "gone to rest"
        if self.stage < len(self.stage_list) - 1:
            return f"{self.species_name()} must be grown first"
        if not self.care_fresh(info["needs"]):
            return f"{info['needs']} your {self.species_name()} first"
        left = self.produce_cooldown_left()
        if left > 0:
            hours, rem = divmod(left, 3600)
            return f"ready again in {hours}h{rem // 60:02d}m"
        return None

    def produce_status_short(self):
        info = self.produce_info()
        if self.dead:
            return "-"
        if self.stage < len(self.stage_list) - 1:
            return "when grown"
        if not self.care_fresh(info["needs"]):
            return f"needs {info['needs']}"
        left = self.produce_cooldown_left()
        if left > 0:
            return f"in {left // 3600}h{left % 3600 // 60:02d}m"
        return "ready!"

    def can_produce(self):
        return self.produce_blocker() is None

    def gather_produce(self):
        """Species action (eggs, milk, wool, ride...). Returns (item, qty, bonus) or None."""
        if not self.can_produce():
            return None
        info = self.produce_info()
        bonus = info["bonus"] * (1 + 0.2 * (self.generation - 1))
        self.ticks += bonus
        self.produce_collected += 1
        if info["verb"] == "ride":
            self.training_sessions += 1
        self.care_timestamps[info["verb"]] = int(time.time())
        return info["item"], info["qty"], int(bonus)

    # Species-specific wrappers kept for older callers and tests.
    def _gather_if(self, verbs):
        if self.produce_info()["verb"] not in verbs:
            return 0
        result = self.gather_produce()
        return result[2] if result else 0

    def can_collect(self):
        return self.produce_info()["verb"] == "collect" and self.can_produce()

    def collect_produce(self):
        return self._gather_if(("collect",))

    def can_shear(self):
        return self.produce_info()["verb"] == "shear" and self.can_produce()

    def shear_wool(self):
        return self._gather_if(("shear",))

    def can_ride(self):
        return self.produce_info()["verb"] == "ride" and self.can_produce()

    def ride_training(self):
        return self._gather_if(("ride",))

    # -- presentation -------------------------------------------------------

    def parse_description(self):
        base = super().parse_description()
        name = self.species_name()
        if self.dead:
            return base
        if name == "horse":
            return base + " | groom daily"
        return base

    def to_json_dict(self):
        data = super().to_json_dict()
        data["produce_collected"] = self.produce_collected
        data["training_sessions"] = self.training_sessions
        data["primary_care_verb"] = self.primary_care
        data["produce_item"] = self.produce_info()["item"]
        return data
