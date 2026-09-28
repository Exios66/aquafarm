# Aquafarm

A **stylized, Botany-inspired** terminal homestead: kawaii ASCII art, daily care windows, and a unified save spanning aquarium, bonsai grove, farm, and livestock.

This package lives beside [Botany](https://github.com/jifunks/botany) as its own game — it does **not** modify upstream Botany. Where Botany is one plant on one pot, Aquafarm is a **multi-area homestead** you hop between in a curses menu.

## Quick start

```bash
cd aquafarm
python3 aquafarm.py
```

Use a terminal around **80×24** (or larger). Navigate with number keys or `j`/`k`, confirm with Enter, go back with `q`.

## Daily care

| Area | Primary care (24h) | Extra actions |
|------|-------------------|---------------|
| Aquarium | **feed** fish | clean tank, check water, spawn cycle (breed), fish profile |
| Bonsai grove | **water** | prune |
| Farm plot | **water** crops | 3 plots, plant, fertilize (compost), harvest slots |
| Livestock barn | **feed** or **groom** (horse) | collect, ride, shear, cycle animal type |

If primary care lapses for **five days**, that creature, crop, or tree may die (same spirit as Botany's drought). While care is fresh, your homestead earns **ticks** (score); **generations** give a small growth bonus after harvest cycles.

### Aquarium — fish species (9)

| Species | Notes |
|---------|--------|
| goldfish | round pond classic |
| betta | flowing fins |
| neon tetra | tiny shimmer |
| clownfish | reef stripes |
| angelfish | tall fins |
| koi | pond jewel |
| guppy | peppy tail |
| catfish | whiskers |
| axolotl | honorary tank pal |

- **Tank health** blends feed, clean, and water care; **algae** rises when the tank is not cleaned (growth slows slightly, never harsh).
- **Spawn cycle**: adult fish with a healthy tank can restart the egg → adult lifecycle for bonus ticks.
- **Fish profile**: pick any species, optional name, and color variant (classic, golden, shadow, speckled).

### Farm — crops (6) & seasons

| Crop | Stages |
|------|--------|
| carrot, wheat, tomato, corn, pumpkin, sunflower | seed → sprout → growing → harvest |

- **Three field plots** run at once; choose active slot in the farm menu.
- **Soil quality** (0–100): watering helps; harvest and neglect lower it; **fertilize** spends compost.
- **Season cycle** (Spring / Summer / Autumn / Winter): advances when you harvest or every 3 login days. Growth multipliers: **1.15 / 1.25 / 1.0 / 0.85** respectively.
- **Crop rotation**: plant a different species in a slot after harvest for a small growth head-start.
- **Compost**: every 3 harvests in a streak, or livestock collect/shear.
- **Farm journal** line in the menu shows last action, soil %, and season.

### Livestock (4 types)

| Animal | Primary care | Bonus action |
|--------|--------------|--------------|
| chicken | feed | collect eggs |
| cow | feed | collect milk |
| horse | groom | ride / training |
| llama | feed | shear wool (+ compost) |

Cycle animal type from the barn menu. Collect, ride, and shear grant bonus ticks when the animal is **grown** and care is fresh.

### Environment

From **environment & themes**, cycle **tank themes** (freshwater, planted, coral reef, moonlit pond) and **homestead backdrops** (meadow, mountain, coastal). These change the header frame and subtitle text.

## Saves and sharing

- Personal data: `~/.aquafarm/` (`*_homestead.dat` pickle + per-area JSON exports + `*_homestead_full.json`)
- Shared board: `sqlite/homestead_board.sqlite` + `homestead_board.json` (multiplayer-style summary rows)

On first run from a checkout, the game creates the `sqlite/` directory and sets permissive permissions like Botany's garden DB (for shared hosts).

## Difference from Botany

| Botany | Aquafarm |
|--------|----------|
| Single plant | Aquarium + bonsai + farm + livestock |
| One care verb (water) | Domain-specific verbs |
| Plant species art | Original kawaii ASCII in `art/` |
| `~/.botany` | `~/.aquafarm` |

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## License

MIT — see [LICENSE](LICENSE).
