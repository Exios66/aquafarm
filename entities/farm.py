from entities.care_entity import CareEntity


class FarmPlot(CareEntity):
    domain = "farm"
    species_list = ["carrot", "wheat", "tomato", "sunflower", "corn", "pumpkin"]
    stage_list = ["seed", "sprout", "growing", "harvest"]
    primary_care = "water"
    extra_care_verbs = ["harvest"]

    life_stages = (
        3600 * 24,
        3600 * 24 * 2,
        3600 * 24 * 4,
    )

    def is_mature(self):
        return (
            not self.dead
            and self.stage == len(self.stage_list) - 1
        )

    def try_harvest(self):
        """Mark ready crop as harvested (caller replaces plot via Homestead)."""
        if not self.is_mature():
            return False
        self.perform_care("harvest")
        return True


# Multi-plot farm wrapper (main catalog); single-plot saves still use FarmPlot.
class FarmField:
    """Container for one or more plots — currently a thin alias for FarmPlot."""

    Plot = FarmPlot

    def __init__(self, generation=1):
        self.plots = [FarmPlot(generation=generation)]

    @property
    def primary_plot(self):
        return self.plots[0]
