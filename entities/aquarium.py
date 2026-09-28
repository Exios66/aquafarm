import time

from entities.care_entity import CareEntity, CARE_WINDOW_SEC


class FishTank(CareEntity):
    domain = "aquarium"
    species_list = ["goldfish", "betta", "neon tetra"]
    stage_list = ["egg", "fry", "juvenile", "adult"]
    primary_care = "feed"
    extra_care_verbs = ["clean", "check_water"]

    life_stages = (
        3600 * 6,
        3600 * 24,
        3600 * 24 * 3,
    )

    def __init__(self, generation=1, species=None):
        super().__init__(generation=generation, species=species)
        self.algae_level = 0
        self.tank_health = 80
        self.bred_from_adult = False
        self._last_algae_tick = int(time.time())

    def migrate_properties(self):
        super().migrate_properties()
        if not hasattr(self, "algae_level"):
            self.algae_level = 0
        if not hasattr(self, "tank_health"):
            self.tank_health = 80
        if not hasattr(self, "bred_from_adult"):
            self.bred_from_adult = False
        if not hasattr(self, "_last_algae_tick"):
            self._last_algae_tick = int(time.time())

    def tank_summary(self):
        feed_pct = self._care_pct("feed")
        clean_pct = self._care_pct("clean")
        water_pct = self._care_pct("check_water")
        return feed_pct, clean_pct, water_pct

    def _care_pct(self, verb):
        delta = int(time.time()) - self.last_care(verb)
        left = max(0.0, 1.0 - (delta / CARE_WINDOW_SEC))
        return int(left * 100)

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

    def perform_care(self, verb):
        super().perform_care(verb)
        if verb == "clean":
            self.algae_level = max(0, self.algae_level - 35)
        elif verb == "check_water":
            self.tank_health = min(100, self.tank_health + 10)

    def tick_life(self, generation_bonus):
        if self.dead:
            return
        self._update_algae()
        if self.primary_care_fresh():
            mult = self.growth_multiplier()
            score_inc = 1 * (1 + generation_bonus) * mult
            self.ticks += score_inc
            if self.stage < len(self.stage_list) - 1:
                threshold = self.life_stages[min(self.stage, len(self.life_stages) - 1)]
                if self.ticks >= threshold:
                    self.growth()
        self.dead_check()

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
        self.bred_from_adult = True
        self.ticks = max(0, self.ticks - self.life_stages[0] * 0.1)
        bonus = 50 * (1 + 0.2 * (self.generation - 1))
        self.ticks += bonus
        self.algae_level = min(100, self.algae_level + 5)
        return True

    def apply_customization(self, species_index, display_name=None, color_variant=None):
        self.species = max(0, min(int(species_index), len(self.species_list) - 1))
        if display_name is not None:
            self.display_name = str(display_name)[:32]
        if color_variant is not None:
            self.color_variant = str(color_variant)

    def to_json_dict(self):
        data = super().to_json_dict()
        data.update(
            {
                "tank_health": self.tank_health,
                "algae_level": int(self.algae_level),
                "bred_from_adult": self.bred_from_adult,
                "growth_multiplier": round(self.growth_multiplier(), 2),
            }
        )
        return data
