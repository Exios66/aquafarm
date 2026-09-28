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
    {
        "id": "retro_farm",
        "label": "retro pixel farm",
        "banner": "barn · fence · hay",
    },
]

LIVESTOCK_COLOR_VARIANTS = ["classic", "spotted", "midnight", "cream"]
FARM_CROP_VARIANTS = ["classic", "heirloom", "golden", "striped"]

FISH_COLOR_VARIANTS = ["classic", "golden", "shadow", "speckled"]

# Short flavor lines for fish profile wizard
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

# Four seasons; the farm advances one every SEASON_ADVANCE_EVERY_LOGIN_DAYS days played
SEASONS = [
    {"id": "spring", "label": "Spring", "growth": 1.15},
    {"id": "summer", "label": "Summer", "growth": 1.25},
    {"id": "autumn", "label": "Autumn", "growth": 1.0},
    {"id": "winter", "label": "Winter", "growth": 0.85},
]

SEASON_ADVANCE_EVERY_LOGIN_DAYS = 3

# ---------------------------------------------------------------------------
# Crops: days of watered growth to reach harvest, and market value per unit.
# ---------------------------------------------------------------------------
CROPS = {
    "carrot": {"days": 1.5, "sell": 8, "flavor": "quick and crunchy"},
    "wheat": {"days": 2.0, "sell": 6, "flavor": "golden sheaves"},
    "tomato": {"days": 3.0, "sell": 12, "flavor": "sun-ripened and juicy"},
    "corn": {"days": 3.0, "sell": 11, "flavor": "tall rustling stalks"},
    "pumpkin": {"days": 5.0, "sell": 25, "flavor": "slow but prize-worthy"},
    "sunflower": {"days": 2.5, "sell": 10, "flavor": "follows the sun"},
}

# ---------------------------------------------------------------------------
# Livestock produce: one special action per species, with a cooldown.
# `needs` is the care verb that must be fresh (within 24h) to use it.
# `bonus` is score ticks awarded on top of the item.
# ---------------------------------------------------------------------------
LIVESTOCK_PRODUCE = {
    "chicken": {"verb": "collect", "label": "collect eggs", "item": "egg", "qty": 3,
                "bonus": 600, "cooldown_h": 8, "needs": "feed"},
    "cow": {"verb": "collect", "label": "milk the cow", "item": "milk", "qty": 2,
            "bonus": 900, "cooldown_h": 12, "needs": "feed"},
    "horse": {"verb": "ride", "label": "ride & train", "item": "ribbon", "qty": 1,
              "bonus": 1000, "cooldown_h": 12, "needs": "groom"},
    "sheep": {"verb": "shear", "label": "shear wool", "item": "wool", "qty": 1,
              "bonus": 800, "cooldown_h": 24, "needs": "feed"},
    "pig": {"verb": "forage", "label": "truffle hunt", "item": "truffle", "qty": 1,
            "bonus": 850, "cooldown_h": 24, "needs": "feed"},
    "llama": {"verb": "shear", "label": "shear fiber", "item": "llama fiber", "qty": 1,
              "bonus": 900, "cooldown_h": 24, "needs": "feed"},
}

# ---------------------------------------------------------------------------
# Market: sell price per item (coins). Crops are merged in from CROPS.
# ---------------------------------------------------------------------------
ITEM_PRICES = {
    "egg": 5,
    "milk": 9,
    "ribbon": 14,
    "wool": 14,
    "truffle": 22,
    "llama fiber": 16,
    "clipping": 4,
    "bonsai": 120,
    "river fish": 12,
}
ITEM_PRICES.update({name: info["sell"] for name, info in CROPS.items()})

# Shop: consumables apply an effect immediately; decorations are cosmetic keepsakes.
SHOP_ITEMS = [
    {"id": "compost", "label": "compost bag", "price": 20, "kind": "supply",
     "desc": "+1 compost for fertilizing"},
    {"id": "algae_scrubber", "label": "algae scrubber", "price": 25, "kind": "supply",
     "desc": "scrub away 50% algae"},
    {"id": "conditioner", "label": "water conditioner", "price": 20, "kind": "supply",
     "desc": "+20 tank health"},
    {"id": "growth_tonic", "label": "bonsai growth tonic", "price": 40, "kind": "supply",
     "desc": "+2h of bonsai growth"},
    {"id": "premium_feed", "label": "premium feed", "price": 35, "kind": "supply",
     "desc": "+2h of livestock growth"},
    {"id": "castle", "label": "tiny castle", "price": 60, "kind": "decoration",
     "desc": "aquarium decoration"},
    {"id": "coral_arch", "label": "coral arch", "price": 80, "kind": "decoration",
     "desc": "aquarium decoration"},
    {"id": "stone_lantern", "label": "stone lantern", "price": 90, "kind": "decoration",
     "desc": "bonsai grove decoration"},
    {"id": "scarecrow", "label": "scarecrow", "price": 70, "kind": "decoration",
     "desc": "farm decoration"},
    {"id": "windmill", "label": "windmill", "price": 150, "kind": "decoration",
     "desc": "homestead landmark"},
]

# ---------------------------------------------------------------------------
# Daily tasks: DAILY_TASK_COUNT drawn each day. `event` matches Homestead.record().
# ---------------------------------------------------------------------------
DAILY_TASK_COUNT = 4
DAILY_TASK_BONUS = 30
TASK_POOL = [
    {"id": "feed_fish", "label": "Feed your fish", "event": "fish_fed", "target": 1, "reward": 10},
    {"id": "clean_tank", "label": "Clean the tank", "event": "tank_cleaned", "target": 1, "reward": 10},
    {"id": "check_water", "label": "Check the water", "event": "water_checked", "target": 1, "reward": 8},
    {"id": "water_bonsai", "label": "Water the bonsai", "event": "bonsai_watered", "target": 1, "reward": 10},
    {"id": "prune_bonsai", "label": "Prune the bonsai", "event": "bonsai_pruned", "target": 1, "reward": 10},
    {"id": "water_crops", "label": "Water the crops", "event": "crops_watered", "target": 1, "reward": 10},
    {"id": "plant_crop", "label": "Plant a crop", "event": "crop_planted", "target": 1, "reward": 12},
    {"id": "harvest_crop", "label": "Harvest a crop", "event": "crop_harvested", "target": 1, "reward": 20},
    {"id": "feed_animal", "label": "Feed your animal", "event": "animal_fed", "target": 1, "reward": 10},
    {"id": "collect_produce", "label": "Gather animal produce", "event": "produce_collected", "target": 1, "reward": 15},
    {"id": "play_games", "label": "Play 2 mini games", "event": "minigame_played", "target": 2, "reward": 15},
    {"id": "win_game", "label": "Win a mini game", "event": "minigame_won", "target": 1, "reward": 20},
    {"id": "sell_goods", "label": "Sell 3 goods at market", "event": "item_sold", "target": 3, "reward": 15},
]

# ---------------------------------------------------------------------------
# Achievements: unlocked when stats[stat] >= threshold. Reward in coins.
# ---------------------------------------------------------------------------
ACHIEVEMENTS = [
    {"id": "first_nibble", "label": "First Nibble", "desc": "feed your fish", "stat": "fish_fed", "threshold": 1, "reward": 10},
    {"id": "spawner", "label": "Circle of Life", "desc": "complete a spawn cycle", "stat": "fish_spawned", "threshold": 1, "reward": 40},
    {"id": "green_thumb", "label": "Green Thumb", "desc": "harvest 10 crops", "stat": "crop_harvested", "threshold": 10, "reward": 60},
    {"id": "barn_hand", "label": "Barn Hand", "desc": "gather produce 10 times", "stat": "produce_collected", "threshold": 10, "reward": 60},
    {"id": "bonsai_master", "label": "Bonsai Master", "desc": "harvest a finished bonsai", "stat": "bonsai_harvested", "threshold": 1, "reward": 80},
    {"id": "angler", "label": "Angler", "desc": "land 5 fish at the pond", "stat": "fish_caught", "threshold": 5, "reward": 50},
    {"id": "arcade", "label": "Arcade Regular", "desc": "win 10 mini games", "stat": "minigame_won", "threshold": 10, "reward": 60},
    {"id": "merchant", "label": "Merchant", "desc": "earn 500 coins", "stat": "coins_earned", "threshold": 500, "reward": 50},
    {"id": "diligent", "label": "Diligent", "desc": "finish 10 daily tasks", "stat": "task_completed", "threshold": 10, "reward": 50},
    {"id": "decorator", "label": "Decorator", "desc": "buy 3 decorations", "stat": "decoration_bought", "threshold": 3, "reward": 40},
    {"id": "good_neighbor", "label": "Good Neighbor", "desc": "visit friends 3 times", "stat": "friend_visited", "threshold": 3, "reward": 30},
    {"id": "legacy", "label": "Legacy", "desc": "start 3 new generations", "stat": "generation_up", "threshold": 3, "reward": 75},
]

# Mini games: how many wins per game per day pay out rewards.
MINIGAME_DAILY_REWARDS = 3
