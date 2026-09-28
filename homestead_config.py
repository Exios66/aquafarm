"""Environment presets for tank theme and homestead backdrop."""

TANK_THEMES = [
    {
        "id": "freshwater",
        "label": "freshwater stream",
        "frame": "~ ~~~ freshwater ~~~ ~",
        "subtitle": "cool clear water",
    },
    {
        "id": "planted",
        "label": "planted aquascape",
        "frame": "~ (( planted tank )) ~",
        "subtitle": "lush greens & bubbles",
    },
    {
        "id": "coral_reef",
        "label": "coral reef",
        "frame": "~ *** coral reef *** ~",
        "subtitle": "warm reef sparkle",
    },
    {
        "id": "moonlit",
        "label": "moonlit pond",
        "frame": "~ ... moonlit pond ... ~",
        "subtitle": "gentle night shimmer",
    },
]

HOMESTEAD_BACKDROPS = [
    {
        "id": "meadow",
        "label": "sunlit meadow",
        "banner": "meadow breeze",
    },
    {
        "id": "mountain",
        "label": "mountain ridge",
        "banner": "pine & stone",
    },
    {
        "id": "coastal",
        "label": "coastal homestead",
        "banner": "salt & wind",
    },
]

FISH_COLOR_VARIANTS = ["classic", "golden", "shadow", "speckled"]

FISH_FLAVOR = {
    "goldfish": "round and cheerful pond classic",
    "betta": "flowing fins, fierce sparkle",
    "neon tetra": "tiny shimmer in a school",
    "clownfish": "reef buddy with bold stripes",
    "angelfish": "tall fins, calm grace",
    "koi": "living jewel of the pond",
    "guppy": "peppy tail, endless energy",
    "catfish": "whiskers and gentle wiggles",
    "axolotl": "smiling amphibian pal (fish tank honorary)",
}

SEASONS = [
    {"id": "spring", "label": "Spring", "growth": 1.15},
    {"id": "summer", "label": "Summer", "growth": 1.25},
    {"id": "autumn", "label": "Autumn", "growth": 1.0},
    {"id": "winter", "label": "Winter", "growth": 0.85},
]

SEASON_ADVANCE_EVERY_LOGIN_DAYS = 3
