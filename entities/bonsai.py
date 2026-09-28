from entities.care_entity import CareEntity


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
