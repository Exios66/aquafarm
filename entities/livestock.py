from entities.care_entity import CareEntity


class LivestockPen(CareEntity):
    domain = "livestock"
    species_list = ["chicken", "cow", "horse", "sheep", "pig", "llama"]
    stage_list = ["baby", "young", "grown"]
    primary_care = "feed"
    extra_care_verbs = ["collect", "groom", "ride", "shear"]

    life_stages = (
        3600 * 24,
        3600 * 24 * 4,
    )

    PRODUCE_BONUS = {
        "chicken": 12,
        "cow": 20,
        "horse": 18,
        "sheep": 15,
        "pig": 16,
        "llama": 17,
    }

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
        self.species = max(0, min(self.species, len(self.species_list) - 1))

    def species_name(self):
        return self.species_list[self.species]

    def primary_care_for_species(self):
        return self.PRIMARY_BY_SPECIES.get(self.species_name(), "feed")

    def primary_care_fresh(self):
        verb = self.primary_care_for_species()
        delta = int(__import__("time").time()) - self.last_care(verb)
        from entities.care_entity import CARE_WINDOW_SEC

        return delta <= CARE_WINDOW_SEC

    def dead_check(self):
        if self.dead:
            return True
        from entities.care_entity import NEGLECT_DEATH_SEC

        verb = self.primary_care_for_species()
        delta = int(__import__("time").time()) - self.last_care(verb)
        if delta > NEGLECT_DEATH_SEC:
            self.dead = True
        return self.dead

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

    def perform_care(self, verb):
        if self.dead:
            return
        allowed = [self.primary_care_for_species(), "feed", "groom"] + self.extra_care_verbs
        if verb not in allowed:
            return
        self.care_timestamps[verb] = int(__import__("time").time())

    def can_collect(self):
        if self.dead or self.stage < len(self.stage_list) - 1:
            return False
        name = self.species_name()
        if name not in ("chicken", "cow"):
            return False
        return self.primary_care_fresh()

    def collect_produce(self):
        if not self.can_collect():
            return 0
        species = self.species_name()
        bonus = self.PRODUCE_BONUS.get(species, 10)
        bonus *= 1 + 0.2 * (self.generation - 1)
        self.ticks += bonus
        self.produce_collected += 1
        self.perform_care("collect")
        return int(bonus)

    def can_shear(self):
        if self.dead or self.species_name() != "llama":
            return False
        if self.stage < len(self.stage_list) - 1:
            return False
        return self.primary_care_fresh()

    def shear_wool(self):
        if not self.can_shear():
            return 0
        bonus = self.PRODUCE_BONUS["llama"] * (1 + 0.2 * (self.generation - 1))
        self.ticks += bonus
        self.produce_collected += 1
        self.compost_grant = getattr(self, "compost_grant", 0)
        self.perform_care("shear")
        return int(bonus)

    def can_ride(self):
        if self.dead or self.species_name() != "horse":
            return False
        if self.stage < len(self.stage_list) - 1:
            return False
        return self.care_fresh("groom") or self.care_fresh("feed")

    def ride_training(self):
        if not self.can_ride():
            return 0
        bonus = self.PRODUCE_BONUS["horse"] * (1 + 0.2 * (self.generation - 1))
        self.ticks += bonus
        self.training_sessions += 1
        self.perform_care("ride")
        return int(bonus)

    def parse_description(self):
        base = super().parse_description()
        name = self.species_name()
        if name == "horse":
            return base + " | groom daily"
        if name == "llama":
            return base + " | shear when grown"
        return base

    def to_json_dict(self):
        data = super().to_json_dict()
        data["produce_collected"] = self.produce_collected
        data["training_sessions"] = self.training_sessions
        data["primary_care_verb"] = self.primary_care_for_species()
        return data
