import time

from entities.care_entity import CareEntity
from homestead_config import FISH_FLAVOR


class FishTank(CareEntity):
    domain = "aquarium"
    species_list = [
        "goldfish",
        "betta",
        "neon tetra",
        "guppy",
        "koi",
        "clownfish",
        "angelfish",
        "catfish",
        "axolotl",
    ]
    stage_list = ["egg", "fry", "juvenile", "adult"]
    primary_care = "feed"
    extra_care_verbs = ["clean", "check_water"]

    life_stages = (
        3600 * 6,
        3600 * 24,
        3600 * 24 * 3,
    )

    SPAWN_BONUS_TICKS = 3000

    def __init__(self, generation=1, species=None):
        super().__init__(generation=generation, species=species)
        self.algae_level = 0
        self.tank_health = 80
        self.bred_from_adult = False
        self.spawn_count = 0
        self._last_algae_tick = int(time.time())

    def migrate_properties(self):
        super().migrate_properties()
        if not hasattr(self, "algae_level"):
            self.algae_level = 0
        if not hasattr(self, "tank_health"):
            self.tank_health = 80
        if not hasattr(self, "bred_from_adult"):
            self.bred_from_adult = False
        if not hasattr(self, "spawn_count"):
            self.spawn_count = 0
        if not hasattr(self, "_last_algae_tick"):
            self._last_algae_tick = int(time.time())

    @classmethod
    def fish_flavor(cls, species_name):
        return FISH_FLAVOR.get(species_name, "a beloved tank friend")

    def tank_summary(self):
        return self.care_pct("feed"), self.care_pct("clean"), self.care_pct("check_water")

    def _care_pct(self, verb):
        return self.care_pct(verb)

    def _update_algae(self):
        now = int(time.time())
        elapsed = max(0, now - self._last_algae_tick)
        self._last_algae_tick = now
        if self.dead:
            return
        if not self.care_fresh("clean"):
            self.algae_level = min(100, self.algae_level + elapsed / 3600.0 * 3)
        else:
            self.algae_level = max(0, self.algae_level - elapsed / 3600.0 * 2)
        feed, clean, water = self.tank_summary()
        self.tank_health = int((feed + clean + water) / 3.0)
        self.tank_health = max(0, min(100, self.tank_health - int(self.algae_level / 5)))

    def growth_multiplier(self):
        """Algae and low tank health slow growth slightly — never punishing."""
        self._update_algae()
        algae_penalty = self.algae_level / 200.0
        health_bonus = self.tank_health / 200.0
        return max(0.55, min(1.25, 1.0 - algae_penalty + health_bonus * 0.15))

    def growth_rate(self):
        return self.growth_multiplier()

    def perform_care(self, verb):
        super().perform_care(verb)
        if self.dead:
            return
        if verb == "clean":
            self.algae_level = max(0, self.algae_level - 35)
        elif verb == "check_water":
            self.tank_health = min(100, self.tank_health + 10)

    def scrub_algae(self, amount):
        self.algae_level = max(0, self.algae_level - amount)

    def condition_water(self, amount):
        self.tank_health = min(100, self.tank_health + amount)

    def can_breed(self):
        if self.dead or self.stage != len(self.stage_list) - 1:
            return False
        feed, clean, water = self.tank_summary()
        return feed > 40 and clean > 40 and water > 40 and self.tank_health >= 55

    def breed_spawn(self):
        """Adult milestone: spawn a new egg cycle (same fish lineage)."""
        if not self.can_breed():
            return False
        self.stage = 0
        self.growth_ticks = 0
        self.bred_from_adult = True
        self.spawn_count += 1
        self.ticks += self.SPAWN_BONUS_TICKS * (1 + 0.2 * (self.generation - 1))
        self.algae_level = min(100, self.algae_level + 5)
        return True

    def to_json_dict(self):
        data = super().to_json_dict()
        sp = self.species_list[self.species]
        data.update(
            {
                "tank_health": self.tank_health,
                "algae_level": int(self.algae_level),
                "bred_from_adult": self.bred_from_adult,
                "spawn_count": self.spawn_count,
                "growth_multiplier": round(self.growth_multiplier(), 2),
                "flavor": self.fish_flavor(sp),
            }
        )
        return data
