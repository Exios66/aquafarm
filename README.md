# Aquafarm

A **stylized, Botany-inspired** terminal homestead: kawaii ASCII art, daily care windows, and a unified save spanning aquarium, bonsai grove, farm, and livestock.

This package lives beside [Botany](https://github.com/jifunks/botany) as its own game — it does **not** modify upstream Botany. Where Botany is one plant on one pot, Aquafarm is a **multi-area homestead** you hop between in a curses menu.

## Quick start

```bash
git clone https://github.com/Exios66/aquafarm.git
cd aquafarm
python3 aquafarm.py
```

Install as a command (optional):

```bash
pip install -e .
aquafarm
```

Use a terminal around **80×24** (or larger). Navigate with number keys or `j`/`k`, confirm with Enter, go back with `q`.

## Daily care

| Area | Primary care (24h) | Extra actions |
|------|-------------------|---------------|
| Aquarium | **feed** fish | clean tank, check water, spawn cycle (breed), fish profile |
| Bonsai grove | **water** | prune; harvest mature bonsai (maple, pine, juniper, **cherry**) |
| Farm plot | **water** crops | harvest when mature (new generation) |
| Livestock barn | **feed** animals | collect eggs/milk/wool (chicken, cow, **horse**, sheep, pig) |

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
- **Fish profile**: goldfish, betta, neon tetra, **guppy**, **koi** — optional name and color variant (classic, golden, shadow, speckled).
- **Barn & crop profiles**: choose livestock breeds and farm crops (carrot, wheat, **tomato**, **sunflower**) with coat/crop variants.
- **Visit a friend**: Botany-style guest care via shared `~/.aquafarm/visitors.json` on multi-user hosts.
- **Harvest history**: local log when a friend passes on or you start a new generation.

### Environment

From **environment & themes**, cycle **tank themes** (freshwater, planted, coral reef, moonlit pond) and **homestead backdrops** (meadow, mountain, coastal, **retro pixel farm**). These change the header frame and subtitle text.

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
