from entities.care_entity import CareEntity


class LivestockPen(CareEntity):
    domain = "livestock"
    species_list = ["chicken", "cow", "horse", "sheep", "pig", "llama"]
    stage_list = ["baby", "young", "grown"]
    primary_care = "feed"
    extra_care_verbs = ["collect"]

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

    def migrate_properties(self):
        super().migrate_properties()
        if not hasattr(self, "produce_collected"):
            self.produce_collected = 0

    def can_collect(self):
        if self.dead or self.stage < len(self.stage_list) - 1:
            return False
        return self.primary_care_fresh()

    def collect_produce(self):
        if not self.can_collect():
            return 0
        species = self.species_list[self.species]
        bonus = self.PRODUCE_BONUS.get(species, 10)
        bonus *= 1 + 0.2 * (self.generation - 1)
        self.ticks += bonus
        self.produce_collected += 1
        self.perform_care("collect")
        return int(bonus)

    def to_json_dict(self):
        data = super().to_json_dict()
        data["produce_collected"] = self.produce_collected
        return data
