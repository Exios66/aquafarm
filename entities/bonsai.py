from entities.care_entity import CARE_WINDOW_SEC, CareEntity


class BonsaiTree(CareEntity):
    domain = "bonsai"
    species_list = ["maple", "pine", "juniper", "cherry"]
    stage_list = ["seed", "sprout", "sapling", "bonsai"]
    primary_care = "water"
    extra_care_verbs = ["prune"]

    life_stages = (
        3600 * 12,
        3600 * 24 * 2,
        3600 * 24 * 5,
    )

    PRUNE_BONUS_TICKS = 600

    def __init__(self, generation=1, species=None):
        super().__init__(generation=generation, species=species)
        self.prune_count = 0

    def migrate_properties(self):
        super().migrate_properties()
        if not hasattr(self, "prune_count"):
            self.prune_count = 0

    def growth_rate(self):
        # a freshly pruned tree puts its energy into shape: small bonus
        return 1.1 if self.care_fresh("prune") else 1.0

    def can_prune(self):
        """Pruning pays off once per care window; a seed has nothing to trim."""
        if self.dead or self.stage == 0:
            return False
        return self.seconds_since("prune") > CARE_WINDOW_SEC

    def prune(self):
        if not self.can_prune():
            return False
        self.perform_care("prune")
        self.prune_count += 1
        self.boost_growth(self.PRUNE_BONUS_TICKS)
        return True

    def to_json_dict(self):
        data = super().to_json_dict()
        data["prune_count"] = self.prune_count
        return data
