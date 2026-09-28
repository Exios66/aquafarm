# Aquafarm

A **stylized, Botany-inspired** terminal homestead: kawaii ASCII art, daily care windows, mini games, daily tasks, a market, and a unified save spanning aquarium, bonsai grove, farm, and livestock barn.

This package lives beside [Botany](https://github.com/jifunks/botany) as its own game. It does **not** modify upstream Botany. Botany gives you one plant in one pot. Aquafarm gives you a **multi-area homestead** that you move around in a curses menu.

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

Use a terminal of **80×24** or larger (60×20 works but is tight). Navigate with `j`/`k` or the arrow keys, press Enter to select, press `1`–`9` to pick an option directly, and press `q` to go back. The home screen's side panel lists everything that needs doing today, and areas marked `(!)` need attention.

## The daily loop

1. **Care**: each area has a primary care verb with a 24h window. While care is fresh, that friend grows and earns score ticks. If it lapses for **five days**, the friend may pass on (like Botany's drought).
2. **Gather**: harvest crops, collect produce, prune the bonsai, and win mini games. Goods go into your basket.
3. **Sell & shop**: sell goods at the market for coins, then buy supplies or decorations.
4. **Tasks & achievements**: four daily tasks rotate every day, with a bonus for finishing all four. Twelve achievements track long-term milestones.
5. **Generations**: retire a mature friend to start a new generation. Each generation grows 20% faster.

| Area | Primary care (24h) | Other actions | Mini game |
|------|-------------------|---------------|-----------|
| Aquarium | **feed** | clean tank, check water, spawn cycle (adult), retire to the pond | **fishing pond**: keep the fish in your catch zone |
| Bonsai grove | **water** | prune once a day (clipping + growth), harvest a finished bonsai | **shape the bonsai**: snip overgrown shoots, spare healthy leaves |
| Farm field | **water** | 3 plots: plant, harvest, harvest all, choose seed, fertilize | **shoo the crows**: whack-a-mole on a 3×3 field |
| Livestock barn | **feed** | groom (faster growth), species produce, send to pasture | **egg catch**: slide the basket under falling eggs |

Each mini game pays coins, a little growth for its area, and a themed item for up to **3 wins per game per day**. After that you can keep playing for fun and personal bests.

### Aquarium: 9 species

goldfish · betta · neon tetra · guppy · koi · clownfish · angelfish · catfish · axolotl

- **Tank health** blends feed, clean, and water care. **Algae** builds up when the tank isn't cleaned and slows growth a little.
- **Spawn cycle**: an adult fish in a healthy tank (all care above 40%) restarts the egg → adult cycle. You keep your score, and the pet shop pays for the extra fry.
- **Fish profile**: choose species (while egg/fry), color variant (classic, golden, shadow, speckled), and a name.

### Farm: 3 plots, 6 crops

| Crop | Grow time | Sells for |
|------|-----------|-----------|
| carrot | ~1.5 days | 8c |
| wheat | ~2 days | 6c |
| sunflower | ~2.5 days | 10c |
| tomato | ~3 days | 12c |
| corn | ~3 days | 11c |
| pumpkin | ~5 days | 25c |

- One watering covers all three plots. **Soil quality** and the **season** (spring → summer → autumn → winter, advancing every 3 days you play) scale growth.
- Each harvest yields 2 crops, +1 with soil at 80% or more, and +1 in summer.
- **Crop rotation**: planting a different crop than the plot's last harvest gives a 2h head start.
- **Compost** comes from every third harvest, from barn produce, and from the shop. Fertilizing adds +12 soil.

### Livestock: 6 species

| Animal | Produce | Cooldown | Needs fresh |
|--------|---------|----------|-------------|
| chicken | 3 eggs | 8h | feed |
| cow | 2 milk | 12h | feed |
| horse | ribbon (ride & train) | 12h | **groom** |
| sheep | wool | 24h | feed |
| pig | truffle | 24h | feed |
| llama | llama fiber | 24h | feed |

Produce needs a **grown** animal and also gives +1 compost to the farm. Pick your animal in the barn profile while it's a baby.

### Market & general store

Sell goods one type at a time, or all at once. The store sells:

- **Supplies**: compost bag, algae scrubber, water conditioner, bonsai growth tonic, premium feed.
- **Decorations**: tiny castle, coral arch, stone lantern, scarecrow, windmill. They show up when you **look** at an area and count toward the Decorator achievement.

### Social

- **Visit a friend**: Botany-style guest care via a shared `~/.aquafarm/visitors.json` on multi-user hosts. A friend's care counts for your homestead too.
- **Homestead board**: a shared scoreboard in sqlite.
- **Harvest history**: a local log of retired and departed friends.

### Environment

From **environment & themes**, cycle through **tank themes** (freshwater, planted, coral reef, moonlit pond) and **homestead backdrops** (meadow, mountain, coastal, retro pixel farm).

## Saves and sharing

- Personal data: `~/.aquafarm/` (`*_homestead.dat` pickle, per-area JSON exports, and `*_homestead_full.json` including coins, inventory, tasks and stats)
- Shared board: `sqlite/homestead_board.sqlite` + `homestead_board.json`

Older saves migrate automatically. Missing fields get defaults, and the old single-plot farm becomes plot 1 of the new field.

## Code map

| Path | What lives there |
|------|------------------|
| `aquafarm.py` | entry point: load/create save, start life thread, run UI |
| `homestead.py` | `Homestead`: all player actions (`do_*`), generations, rewards, life loop |
| `entities/` | `FishTank`, `BonsaiTree`, `FarmField` + `CropSlot`, `LivestockPen` on a shared `CareEntity` |
| `progression.py` | coins, inventory, daily tasks, achievements, mini game payouts |
| `minigames/` | headless mini game logic (`update(dt)`, `handle_key`, `render`) |
| `menu_screen.py` | curses UI: screens, wizards, mini game runner |
| `homestead_config.py` | catalogs: crops, produce, prices, shop, tasks, achievements, themes |
| `data_manager.py` | pickle save, JSON exports, sqlite board, guest visits |

Growth is measured in seconds of cared-for time. `ticks` is the score and never resets. `growth_ticks` drives the life stage, so a spawn cycle can restart growth without losing score. Offline time counts only while the last primary care was still fresh.

## Differences from Botany

| Botany | Aquafarm |
|--------|----------|
| Single plant | Aquarium + bonsai + farm + livestock |
| One care verb (water) | Domain-specific verbs |
| Score only | Coins, market, shop, daily tasks, achievements |
| — | Four real-time mini games |
| Plant species art | Original kawaii ASCII in `art/` |
| `~/.botany` | `~/.aquafarm` |

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The suite covers the entities, the progression system, every `Homestead` action, and the mini games (including auto-play bots that prove each game is winnable and that idling loses). It also runs a full curses walkthrough in a pseudo-terminal.

## License

MIT — see [LICENSE](LICENSE).
