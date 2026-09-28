import curses
import getpass
import json
import locale
import math
import os
import sys
import time
from collections import deque

from entities.aquarium import FishTank
from homestead import AREA_LABELS
from homestead_config import (
    ACHIEVEMENTS,
    CROPS,
    FARM_CROP_VARIANTS,
    FISH_COLOR_VARIANTS,
    HOMESTEAD_BACKDROPS,
    LIVESTOCK_COLOR_VARIANTS,
    MINIGAME_DAILY_REWARDS,
    SHOP_ITEMS,
    TANK_THEMES,
)
from minigames import GAMES

FRAME_TIMEOUT_MS = 250
GAME_TIMEOUT_MS = 60
MESSAGE_SECONDS = 3.0

SCREEN_TITLES = {
    "home": "choose an area to tend",
    "aquarium": "aquarium",
    "bonsai": "bonsai grove",
    "farm": "farm field",
    "livestock": "livestock barn",
    "games": "mini games — wins pay coins & help your friends grow",
    "tasks": "daily tasks — reset every day",
    "market": "market",
    "sell": "sell goods",
    "shop": "general store",
    "achievements": "achievements & stats",
    "environment": "environment & themes",
    "board": "homestead board (local sqlite)",
    "harvest_log": "harvest history",
}


class HomesteadMenu:
    def __init__(self, stdscr, homestead, data_manager):
        self.screen = stdscr
        self.homestead = homestead
        self.data = data_manager
        self.exit = False
        self.view = "home"
        self.selected = 0
        self.scroll = 0
        self.messages = deque()
        self.message = ""
        self.message_until = 0.0
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        self.screen.keypad(True)
        self.screen.timeout(FRAME_TIMEOUT_MS)
        self._init_colors()
        self.maxy, self.maxx = self.screen.getmaxyx()
        if self.homestead.pending_fish_setup:
            self._fish_setup_wizard()

    def _init_colors(self):
        self.normal = curses.A_NORMAL
        if curses.has_colors():
            curses.start_color()
            try:
                curses.use_default_colors()
                background = -1
            except curses.error:
                background = curses.COLOR_BLACK
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(2, curses.COLOR_CYAN, background)
            curses.init_pair(3, curses.COLOR_GREEN, background)
            curses.init_pair(4, curses.COLOR_YELLOW, background)
            curses.init_pair(5, curses.COLOR_RED, background)
            curses.init_pair(6, curses.COLOR_MAGENTA, background)
            self.highlighted = curses.color_pair(1)
            self.accent = curses.color_pair(2)
            self.ok = curses.color_pair(3)
            self.gold = curses.color_pair(4) | curses.A_BOLD
            self.warn = curses.color_pair(5)
            self.fancy = curses.color_pair(6)
        else:
            self.highlighted = curses.A_REVERSE
            self.accent = curses.A_BOLD
            self.ok = curses.A_BOLD
            self.gold = curses.A_BOLD
            self.warn = curses.A_BOLD
            self.fancy = curses.A_NORMAL

    # ------------------------------------------------------------------
    # low-level drawing
    # ------------------------------------------------------------------

    def _put(self, y, x, text, attr=None):
        if y < 0 or y >= self.maxy or x >= self.maxx - 1:
            return
        text = str(text)[: max(0, self.maxx - x - 1)]
        if not text:
            return
        try:
            self.screen.addstr(y, x, text, self.normal if attr is None else attr)
        except curses.error:
            pass

    def _wait_key(self):
        """Blocking key read for modal screens (main loop uses a timeout)."""
        while True:
            key = self.screen.getch()
            if key != -1:
                return key

    def _art_directory(self):
        local = os.path.join(os.path.dirname(os.path.realpath(__file__)), "art")
        if os.path.isdir(local):
            return local
        return os.path.join(sys.prefix, "share", "aquafarm-art")

    def _ascii_render(self, basename, ypos, xpos, entity=None):
        art_dir = self._art_directory()
        path = os.path.join(art_dir, basename + ".txt")
        if not os.path.isfile(path):
            path = os.path.join(art_dir, "homestead_idle.txt")
            if not os.path.isfile(path):
                return 0
        attr = self.normal
        variant = getattr(entity, "color_variant", "") if entity else ""
        if variant in ("golden", "heirloom"):
            attr = self.gold
        elif variant in ("shadow", "midnight"):
            attr = curses.A_DIM
        elif variant in ("speckled", "spotted", "striped"):
            attr = self.fancy
        elif variant == "cream":
            attr = curses.A_BOLD
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        for y, line in enumerate(lines[:10]):
            self._put(ypos + y, xpos, line, attr)
        return len(lines[:10])

    def _gauge(self, pct, width=10):
        filled = int(math.ceil(max(0, min(100, pct)) / 100.0 * width))
        return "(" + ")" * filled + "." * (width - filled) + ")"

    def _duration(self, seconds):
        seconds = int(max(0, seconds))
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        if days:
            return f"{days}d{hours}h"
        return f"{hours}h{rem // 60:02d}m"

    # ------------------------------------------------------------------
    # messages
    # ------------------------------------------------------------------

    def say(self, *msgs):
        for msg in msgs:
            if msg:
                self.messages.append(msg)
        for notice in self.homestead.pop_notices():
            self.messages.append(notice)

    def _current_message(self):
        now = time.time()
        if now >= self.message_until:
            if self.messages:
                self.message = self.messages.popleft()
                self.message_until = now + MESSAGE_SECONDS
            else:
                self.message = ""
        return self.message

    # ------------------------------------------------------------------
    # frame
    # ------------------------------------------------------------------

    def _art_x(self):
        return max(40, self.maxx - 28)

    def _has_side_panel(self):
        return self.view in AREA_LABELS or self.view in ("home", "market", "sell")

    def _left_width(self, x):
        """Columns available left of the side panel (or the whole row)."""
        edge = self._art_x() - 2 if self._has_side_panel() else self.maxx - 1
        return max(0, edge - x)

    def _draw_frame(self):
        self.maxy, self.maxx = self.screen.getmaxyx()
        self.screen.erase()
        hs = self.homestead
        theme = hs.tank_theme()
        self._put(0, 2, f"~ aquafarm ~ {theme['frame']} (◕‿◕)", curses.A_BOLD)
        self._put(1, 2, hs.environment_subtitle(), self.accent)
        progress = hs.progress
        progress.refresh_tasks()
        status = (
            f"gen {hs.generation} | score {hs.total_score()} | {progress.coins}c"
            f" | {hs.farm.season()['label']} | tasks {progress.tasks_done()}/{len(progress.tasks)}"
        )
        self._put(2, 2, status, curses.A_DIM)
        entity = hs.entity_for_area(self.view)
        if entity is not None and not entity.dead:
            pct = entity.care_pct(entity.primary_care)
            gauge = f"{self._gauge(pct)} {pct}% {entity.primary_care}"
            self._put(3, 2, gauge, self.ok if pct > 25 else self.warn)
        self._draw_side_panel()
        body = self._body_lines()
        options = self._options()
        y = 5
        self._put(y, 2, self._title(), curses.A_BOLD)
        y += 1
        # keep a few options on screen even when the body is long
        room = self.maxy - 3 - y - min(len(options), 3) - 1
        if len(body) > room:
            body = body[: max(0, room - 1)] + [("…", curses.A_DIM)]
        for line in body:
            text, attr = line if isinstance(line, tuple) else (line, None)
            self._put(y, 4, text[: self._left_width(4)], attr)
            y += 1
        self._draw_options(options, y + (1 if body else 0))
        msg = self._current_message()
        if msg:
            self._put(self.maxy - 2, 2, msg, self.ok)
        self._put(
            self.maxy - 1, 2,
            "j/k move · enter select · 1-9 quick pick · q back",
            curses.A_DIM,
        )

    def _draw_options(self, options, start_y):
        room = max(1, self.maxy - 3 - start_y)
        self.selected = max(0, min(self.selected, len(options) - 1))
        if self.selected < self.scroll:
            self.scroll = self.selected
        elif self.selected >= self.scroll + room:
            self.scroll = self.selected - room + 1
        self.scroll = max(0, min(self.scroll, max(0, len(options) - room)))
        for row, idx in enumerate(range(self.scroll, min(len(options), self.scroll + room))):
            label = options[idx][0]
            style = self.highlighted if idx == self.selected else self.normal
            key = f"{idx + 1}" if idx < 9 else " "
            self._put(start_y + row, 4, f"{key} - {label}"[: self._left_width(4)], style)
        if self.scroll > 0:
            self._put(start_y, 2, "↑", curses.A_DIM)
        if self.scroll + room < len(options):
            self._put(start_y + room - 1, 2, "↓", curses.A_DIM)

    def _draw_side_panel(self):
        hs = self.homestead
        x = self._art_x()
        if self.view in AREA_LABELS:
            entity = hs.entity_for_area(self.view)
            used = self._ascii_render(entity.art_basename(), 4, x, entity)
            lines = self._area_info(self.view)
        elif self.view == "home":
            used = self._ascii_render("homestead_idle", 4, x)
            lines = ["to do:"] + ([f"· {t}" for t in hs.attention_list()] or ["· all tended ✿"])
        elif self.view in ("market", "sell"):
            used = 0
            lines = self._inventory_lines()
        else:
            return
        y = 4 + used + 1
        for line in lines:
            if y >= self.maxy - 2:
                break
            self._put(y, x, line, curses.A_DIM if line.startswith("·") else None)
            y += 1

    def _area_info(self, area):
        hs = self.homestead
        entity = hs.entity_for_area(area)
        if entity.dead:
            return [entity.parse_description(), "choose 'new start'"]
        lines = [entity.parse_description()]
        if area == "farm":
            lines.append(f"{entity.season()['label']} · soil {entity.soil_quality}%")
            lines.append(f"compost {entity.compost} · seed {entity.species_name()}")
            lines += [entity.slot_line(i) for i in range(entity.NUM_SLOTS)]
            return lines
        pct = int(entity.stage_progress() * 100)
        lines.append(f"growth {self._gauge(pct, 8)} {pct}%")
        if area == "aquarium":
            feed, clean, water = entity.tank_summary()
            lines.append(f"feed {feed}% clean {clean}%")
            lines.append(f"water {water}% health {entity.tank_health}%")
            lines.append(f"algae {int(entity.algae_level)}%")
        elif area == "bonsai":
            lines.append(f"pruned {entity.prune_count}x")
            if entity.can_prune():
                lines.append("ready to prune ✂")
        elif area == "livestock":
            info = entity.produce_info()
            lines.append(f"groom {entity.care_pct('groom')}%")
            lines.append(f"{info['label']}: {entity.produce_status_short()}")
            lines.append(f"produce gathered {entity.produce_collected}")
        return lines

    def _inventory_lines(self):
        progress = self.homestead.progress
        lines = [f"coins: {progress.coins}c", "basket:"]
        if not progress.inventory:
            lines.append("· (empty)")
        for item, qty in sorted(progress.inventory.items()):
            lines.append(f"· {item} x{qty}")
        lines.append(f"worth ~{progress.inventory_value()}c")
        return lines

    # ------------------------------------------------------------------
    # per-screen content
    # ------------------------------------------------------------------

    def _title(self):
        title = SCREEN_TITLES.get(self.view, self.view)
        if self.view == "achievements":
            unlocked = len(self.homestead.progress.achievements)
            title += f" — {unlocked}/{len(ACHIEVEMENTS)} unlocked"
        return title

    def _body_lines(self):
        hs = self.homestead
        progress = hs.progress
        if self.view == "tasks":
            lines = []
            for task in progress.tasks:
                mark = "[x]" if task["done"] else "[ ]"
                attr = self.ok if task["done"] else None
                lines.append((
                    f"{mark} {task['label']} ({task['progress']}/{task['target']})"
                    f"  +{task['reward']}c", attr,
                ))
            bonus = "paid ✿" if progress.task_bonus_paid else "finish all for a bonus"
            lines.append((f"daily bonus: {bonus}", curses.A_DIM))
            return lines
        if self.view == "achievements":
            lines = []
            for ach in ACHIEVEMENTS:
                have = progress.stats.get(ach["stat"], 0)
                if ach["id"] in progress.achievements:
                    lines.append((f"★ {ach['label']} — {ach['desc']}", self.gold))
                else:
                    shown = min(have, ach["threshold"])
                    lines.append(f"☆ {ach['label']} — {ach['desc']} ({shown}/{ach['threshold']})")
            return lines
        if self.view == "games":
            lines = []
            for game_id, cls in GAMES.items():
                left = hs.minigame_rewards_left(game_id)
                best = progress.minigame_best.get(game_id, 0)
                lines.append((
                    f"{cls.title}: rewards left {left}/{MINIGAME_DAILY_REWARDS}  best {best}",
                    curses.A_DIM,
                ))
            return lines
        if self.view == "environment":
            theme = hs.tank_theme()
            back = hs.backdrop()
            return [f"tank: {theme['label']}", f"backdrop: {back['label']}"]
        if self.view == "board":
            board = self.data.retrieve_board_from_db()
            rows = [r for r in board.values() if not r.get("dead")]
            rows.sort(key=lambda r: r["total_score"], reverse=True)
            if not rows:
                return ["(empty — be the first caretaker!)"]
            return [
                f"{r['owner']}: {r['total_score']}p gen {r['generation']} age {r.get('age') or '?'}"
                for r in rows[:10]
            ]
        if self.view == "harvest_log":
            if not os.path.isfile(self.data.harvest_json_path):
                return ["(no harvests recorded yet)"]
            try:
                with open(self.data.harvest_json_path, "r") as handle:
                    harvest = json.load(handle)
            except (OSError, ValueError):
                return ["(harvest log unreadable)"]
            entries = sorted(harvest.values(), key=lambda e: e.get("recorded_at", 0))[-10:]
            return [
                f"{e.get('area')}: {e.get('description')} ({e.get('score')}p)"
                for e in entries
            ] or ["(no harvests recorded yet)"]
        if self.view == "farm":
            return [(f"last: {self.homestead.farm.last_action}", curses.A_DIM)]
        if self.view == "shop":
            return [(f"you have {progress.coins}c", curses.A_DIM)]
        return []

    def _options(self):
        view = self.view
        builder = getattr(self, f"_options_{view}", None)
        options = builder() if builder else []
        if view != "home":
            options.append(("back", self._go_back))
        return options

    def _options_home(self):
        hs = self.homestead

        def area_label(area):
            flag = " (!)" if hs.area_needs_attention(area) else ""
            return AREA_LABELS[area] + flag

        progress = hs.progress
        return [
            (area_label("aquarium"), lambda: self._enter("aquarium")),
            (area_label("bonsai"), lambda: self._enter("bonsai")),
            (area_label("farm"), lambda: self._enter("farm")),
            (area_label("livestock"), lambda: self._enter("livestock")),
            ("mini games", lambda: self._goto("games")),
            (f"daily tasks ({progress.tasks_done()}/{len(progress.tasks)})", lambda: self._goto("tasks")),
            (f"market ({progress.coins}c)", lambda: self._goto("market")),
            ("achievements & stats", lambda: self._goto("achievements")),
            ("environment & themes", lambda: self._goto("environment")),
            ("homestead board", lambda: self._goto("board")),
            ("visit a friend", self._visit_friend),
            ("harvest history", lambda: self._goto("harvest_log")),
            ("instructions", self._show_instructions),
            ("save & exit", self._quit),
        ]

    def _restart_option(self, area):
        hs = self.homestead
        entity = hs.entity_for_area(area)
        if not hs.can_restart(area):
            return []
        if entity.dead:
            label = "new start (replace lost friend)"
        elif area == "bonsai":
            label = "harvest bonsai (new generation)"
        elif area == "aquarium":
            label = "retire to the big pond (new gen)"
        else:
            label = "send to pasture (new generation)"
        return [(label, lambda: self._new_start(area))]

    def _options_aquarium(self):
        hs = self.homestead
        fish = hs.aquarium
        opts = [
            ("feed fish", lambda: self._do(hs.do_feed_fish)),
            ("clean tank", lambda: self._do(hs.do_clean_tank)),
            ("check water", lambda: self._do(hs.do_check_water)),
        ]
        if fish.is_mature():
            opts.append(("spawn cycle (breed)", lambda: self._do(hs.do_breed)))
        opts += self._restart_option("aquarium")
        opts += [
            ("fishing pond (mini game)", lambda: self._play("fishing")),
            ("fish profile", self._fish_setup_wizard),
            ("look", lambda: self._show_look("aquarium")),
        ]
        return opts

    def _options_bonsai(self):
        hs = self.homestead
        opts = [
            ("water", lambda: self._do(hs.do_water_bonsai)),
            ("prune", lambda: self._do(hs.do_prune)),
        ]
        opts += self._restart_option("bonsai")
        opts += [
            ("shape the bonsai (mini game)", lambda: self._play("pruning")),
            ("look", lambda: self._show_look("bonsai")),
        ]
        return opts

    def _options_farm(self):
        hs = self.homestead
        farm = hs.farm
        seed = farm.species_name()
        plot = farm.active_slot + 1
        slot = farm.active()
        opts = [
            ("water crops", lambda: self._do(hs.do_water_crops)),
            (f"next plot (now plot {plot})", lambda: self._do(hs.do_select_plot)),
        ]
        if slot.is_empty():
            opts.append((f"plant {seed} in plot {plot}", lambda: self._do(hs.do_plant)))
        elif slot.is_mature():
            opts.append((f"harvest plot {plot}", lambda: self._do(hs.do_harvest)))
        if len(farm.mature_slots()) > 1:
            opts.append(("harvest all ripe plots", lambda: self._do(hs.do_harvest_all)))
        opts += [
            (f"choose seed (now {seed})", self._crop_setup_wizard),
            (f"fertilize (compost {farm.compost})", lambda: self._do(hs.do_fertilize)),
        ]
        opts += self._restart_option("farm")
        opts += [
            ("shoo the crows (mini game)", lambda: self._play("crows")),
            ("look", lambda: self._show_look("farm")),
        ]
        return opts

    def _options_livestock(self):
        hs = self.homestead
        pen = hs.livestock
        name = pen.species_name()
        opts = [
            (f"feed the {name}", lambda: self._do(hs.do_feed_animal)),
            (f"groom the {name}", lambda: self._do(hs.do_groom)),
            (pen.produce_info()["label"], lambda: self._do(hs.do_gather_produce)),
        ]
        opts += self._restart_option("livestock")
        opts.append(("egg catch (mini game)", lambda: self._play("eggcatch")))
        if pen.stage == 0 and not pen.dead:
            opts.append(("barn profile (choose animal)", self._barn_setup_wizard))
        opts.append(("look", lambda: self._show_look("livestock")))
        return opts

    def _options_games(self):
        return [
            (f"{cls.title} ({AREA_LABELS.get(cls.area, cls.area)})",
             lambda gid=game_id: self._play(gid))
            for game_id, cls in GAMES.items()
        ]

    def _options_market(self):
        hs = self.homestead
        count = hs.progress.item_count()
        return [
            (f"sell goods ({count} items)", lambda: self._goto("sell")),
            ("sell everything", lambda: self._do(hs.do_sell_all)),
            ("general store", lambda: self._goto("shop")),
        ]

    def _options_sell(self):
        hs = self.homestead
        progress = hs.progress
        opts = []
        for item, qty in sorted(progress.inventory.items()):
            price = progress.price_of(item)
            opts.append((
                f"sell {item} x{qty} @ {price}c = {price * qty}c",
                lambda it=item: self._do(hs.do_sell, it),
            ))
        if not opts:
            opts.append(("(basket empty — harvest, gather or play!)", lambda: None))
        return opts

    def _options_shop(self):
        hs = self.homestead
        opts = []
        for item in SHOP_ITEMS:
            owned = item["kind"] == "decoration" and item["id"] in hs.progress.decorations
            tag = "owned" if owned else f"{item['price']}c"
            opts.append((
                f"{item['label']} [{tag}] — {item['desc']}",
                lambda iid=item["id"]: self._do(hs.do_buy, iid),
            ))
        return opts

    def _options_tasks(self):
        return []

    def _options_achievements(self):
        return [("view all stats", self._show_stats)]

    def _options_environment(self):
        return [
            ("cycle tank theme", self._cycle_theme),
            ("cycle homestead backdrop", self._cycle_backdrop),
        ]

    def _options_board(self):
        return [("refresh", self.data.update_board_json)]

    def _options_harvest_log(self):
        return []

    # ------------------------------------------------------------------
    # navigation & actions
    # ------------------------------------------------------------------

    def _goto(self, view):
        self.view = view
        self.selected = 0
        self.scroll = 0

    def _enter(self, area):
        self._goto(area)
        if area == "aquarium" and self.homestead.pending_fish_setup:
            self._fish_setup_wizard()
        elif area == "livestock" and self.homestead.pending_barn_setup:
            self._barn_setup_wizard()

    def _go_back(self):
        parent = {"sell": "market", "shop": "market"}.get(self.view, "home")
        self._goto(parent)

    def _quit(self):
        self.exit = True

    def _cycle_theme(self):
        hs = self.homestead
        hs.tank_theme_index = (hs.tank_theme_index + 1) % len(TANK_THEMES)
        self.say(f"tank theme: {hs.tank_theme()['label']}")

    def _cycle_backdrop(self):
        hs = self.homestead
        hs.backdrop_index = (hs.backdrop_index + 1) % len(HOMESTEAD_BACKDROPS)
        self.say(f"backdrop: {hs.backdrop()['label']}")

    def _new_start(self, area):
        entity = self.homestead.entity_for_area(area)
        if not entity.dead and not self._confirm(
            [
                f"Ready to begin a new generation in your {AREA_LABELS[area]}?",
                f"Next generation grows at ~{1.2 + self.homestead.generation_bonus():.1f}x speed.",
            ]
        ):
            return
        with self.homestead.lock:
            msg = self.homestead.do_new_start(area, self.data)
        self.say(msg)
        self._enter(area)

    def _do(self, action, *args):
        with self.homestead.lock:
            msg = action(*args)
        self.say(msg)

    def _persist(self):
        self.data.save_homestead(self.homestead)
        self.data.write_json_exports(self.homestead)

    def _activate(self, index=None):
        options = self._options()
        if index is not None:
            if index >= len(options):
                return
            self.selected = index
        if not options:
            return
        _, action = options[max(0, min(self.selected, len(options) - 1))]
        before_view = self.view
        action()
        self.say()
        if self.view == before_view and self.view != "home":
            self._persist()

    def run(self):
        while not self.exit:
            self._draw_frame()
            self.screen.refresh()
            key = self.screen.getch()
            if key == -1:
                continue
            count = len(self._options())
            if key in (curses.KEY_UP, ord("k")):
                self.selected = (self.selected - 1) % max(1, count)
            elif key in (curses.KEY_DOWN, ord("j")):
                self.selected = (self.selected + 1) % max(1, count)
            elif key in (curses.KEY_ENTER, 10, 13, ord(" ")):
                self._activate()
            elif ord("1") <= key <= ord("9"):
                self._activate(key - ord("1"))
            elif key in (ord("q"), ord("Q")) and self.view == "home":
                self.exit = True
            elif key in (ord("q"), ord("Q"), 27, curses.KEY_BACKSPACE, 127):
                if self.view != "home":
                    self._go_back()
            elif key == curses.KEY_RESIZE:
                self.maxy, self.maxx = self.screen.getmaxyx()

    # ------------------------------------------------------------------
    # modal screens
    # ------------------------------------------------------------------

    def _confirm(self, lines):
        self.screen.erase()
        for y, line in enumerate(lines + ["", "Continue? (y/N)"], 2):
            self._put(y, 2, line)
        self.screen.refresh()
        return self._wait_key() in (ord("Y"), ord("y"))

    def _show_look(self, area):
        entity = self.homestead.entity_for_area(area)
        self.screen.erase()
        self._put(1, 2, f"{AREA_LABELS[area]} — a closer look", curses.A_BOLD)
        used = self._ascii_render(entity.art_basename(), 3, 4, entity)
        y = 3 + used + 1
        lines = self._area_info(area)
        lines.append(f"score ticks: {int(entity.ticks)}  generation {entity.generation}")
        lines.append(f"age: {self.data.entity_age_formatted(entity)}")
        if area == "aquarium":
            lines.append(FishTank.fish_flavor(entity.species_name()))
            lines.append(f"spawn cycles: {entity.spawn_count}")
        elif area == "farm":
            crop = CROPS.get(entity.species_name(), {})
            lines.append(f"{entity.species_name()}: {crop.get('flavor', '')}, ~{crop.get('days', '?')} days")
            lines.append(f"harvests: {entity.total_harvests}  streak {entity.harvest_streak}")
        elif area == "livestock":
            lines.append(f"training sessions: {entity.training_sessions}")
        decor = self._decorations_for(area)
        if decor:
            lines.append("decor: " + ", ".join(decor))
        if not entity.dead and entity.stage < len(entity.stage_list) - 1 and area != "farm":
            remaining = entity.life_stages[entity.stage] - entity.growth_ticks
            lines.append(f"next stage in ~{self._duration(remaining / max(0.1, entity.growth_rate()))} of care")
        for line in lines:
            self._put(y, 4, line)
            y += 1
        self._put(self.maxy - 2, 2, "any key to return...", curses.A_DIM)
        self.screen.refresh()
        self._wait_key()

    def _decorations_for(self, area):
        where = {
            "aquarium": ("castle", "coral_arch"),
            "bonsai": ("stone_lantern",),
            "farm": ("scarecrow", "windmill"),
            "livestock": ("windmill",),
        }.get(area, ())
        owned = self.homestead.progress.decorations
        return [s["label"] for s in SHOP_ITEMS if s["id"] in where and s["id"] in owned]

    def _show_stats(self):
        progress = self.homestead.progress
        self.screen.erase()
        self._put(1, 2, "lifetime stats", curses.A_BOLD)
        y = 3
        col = 0
        for stat, value in sorted(progress.stats.items()):
            self._put(y, 4 + col * 38, f"{stat.replace('_', ' ')}: {value}")
            col = (col + 1) % 2
            if col == 0:
                y += 1
        if not progress.stats:
            self._put(y, 4, "(nothing yet — go tend your homestead!)")
        best = progress.minigame_best
        y += 2
        self._put(y, 2, "mini game bests: " + (", ".join(f"{k} {v}" for k, v in best.items()) or "none"))
        self._put(self.maxy - 2, 2, "any key to return...", curses.A_DIM)
        self.screen.refresh()
        self._wait_key()

    def _show_instructions(self):
        self.screen.erase()
        lines = [
            "Aquafarm: daily homestead care in 24h windows.",
            "",
            "Aquarium  feed fish daily; clean & check water to keep algae down.",
            "          Adult fish can spawn a new egg cycle for coins.",
            "Bonsai    water daily; prune once a day for clippings & growth.",
            "Farm      3 plots share one watering. Plant, water, harvest, sell.",
            "          Rotate crops for a head start; compost boosts soil.",
            "Barn      feed daily; groom for faster growth. Grown animals",
            "          give eggs, milk, wool, truffles or ride training.",
            "",
            "Mini games: fishing, bonsai shaping, crow shooing, egg catch.",
            "  Wins pay coins and growth (3 rewarded wins per game per day).",
            "Daily tasks: 4 new goals each day, plus a bonus for all four.",
            "Market: sell goods for coins; buy supplies and decorations.",
            "",
            "Neglect a friend's primary care for 5 days and it may pass on.",
            "Mature friends can start a new generation for a growth bonus.",
            "",
            "Press any key to return...",
        ]
        for y, line in enumerate(lines):
            self._put(y + 1, 2, line)
        self.screen.refresh()
        self._wait_key()

    def _get_user_string(self, ypos=15, xpos=2):
        user_string = ""
        while True:
            key = self._wait_key()
            if key in (curses.KEY_ENTER, 10, 13):
                return user_string.strip()
            if key == 27:
                return ""
            if key in (curses.KEY_BACKSPACE, 127, 8):
                user_string = user_string[:-1]
            elif 32 <= key <= 126 and len(user_string) < 24:
                user_string += chr(key)
            self._put(ypos, xpos, " " * (self.maxx - xpos - 2))
            self._put(ypos, xpos, user_string)
            self.screen.refresh()

    def _visit_friend(self):
        self.screen.erase()
        self._put(2, 2, "Whose homestead would you like to visit?", curses.A_BOLD)
        if self.homestead.visitors:
            recent = ", ".join(self.homestead.visitors[-5:])
            self._put(4, 2, f"Since last time: {recent}")
            self.homestead.visitors = []
        weekly = self.data.weekly_visitors_text(getpass.getuser())
        self._put(6, 2, f"This week: {weekly}")
        self._put(8, 2, "username (enter to confirm, esc to cancel):")
        self.screen.refresh()
        host = self._get_user_string(9, 4)
        if not host:
            return
        if host.lower() == getpass.getuser().lower():
            self.say("You're already home on the farm!")
            return
        json_path = self.data.guest_homestead_json_path(host)
        visitor_data = {}
        if json_path:
            try:
                with open(json_path, "r") as handle:
                    visitor_data = json.load(handle)
            except (OSError, ValueError):
                visitor_data = {}
        ok, status = self.data.append_guest_care_for_host(host)
        if ok:
            with self.homestead.lock:
                self.homestead.record("friend_visited")
            self._show_visit(host, visitor_data)
            self.say(f"you helped tend ~{host}'s homestead")
        elif status == "locked":
            self.say(f"{host}'s homestead is locked, but you peeked in...")
        else:
            self.say(f"Can't find directions to {host}'s homestead...")

    def _show_visit(self, host, data):
        self.screen.erase()
        self._put(1, 2, f"~{host}'s homestead", curses.A_BOLD)
        if data:
            fish = self._entity_from_visit_json(data)
            used = self._ascii_render(fish.art_basename(), 3, 4, fish)
        else:
            used = self._ascii_render("homestead_idle", 3, 4)
            self._put(3 + used + 1, 4, "(their homestead is still being set up)", curses.A_DIM)
            used += 2
        y = 3 + used + 1
        areas = data.get("areas") or {}
        for key in ("aquarium", "bonsai", "farm", "livestock"):
            info = areas.get(key) or {}
            if info:
                self._put(y, 4, f"{AREA_LABELS[key]}: {info.get('description', '?')}")
                y += 1
        if data:
            self._put(y + 1, 4, f"score {data.get('total_score', data.get('score', '?'))}"
                                f" · gen {data.get('generation', '?')}")
        self._put(self.maxy - 2, 2, "you left some care behind ♥  any key...", curses.A_DIM)
        self.screen.refresh()
        self._wait_key()

    def _entity_from_visit_json(self, data):
        entity = FishTank()
        entity.dead = bool(data.get("is_dead"))
        if entity.dead:
            return entity
        areas = data.get("areas") or {}
        fish = areas.get("aquarium") or data
        stage = fish.get("stage")
        species = fish.get("species")
        if stage in entity.stage_list:
            entity.stage = entity.stage_list.index(stage)
        if species in entity.species_list:
            entity.species = entity.species_list.index(species)
        entity.display_name = fish.get("display_name", "")
        entity.color_variant = fish.get("color_variant", "classic")
        return entity

    # ------------------------------------------------------------------
    # wizards
    # ------------------------------------------------------------------

    def _profile_wizard(self, title, entity, variants, variant_label, allow_species, flavor=None):
        """Shared species/variant/name picker. Returns True when saved."""
        species_idx = entity.species
        variant_idx = variants.index(entity.color_variant) if entity.color_variant in variants else 0
        name_buf = list(entity.display_name or "")
        orig = (entity.species, entity.color_variant)
        while True:
            self.screen.erase()
            self._put(1, 2, title, curses.A_BOLD)
            sp = entity.species_list[species_idx]
            entity.species = species_idx
            entity.color_variant = variants[variant_idx]
            lock_note = "" if allow_species else " (locked once grown)"
            self._put(4, 4, f"species [{species_idx + 1}/{len(entity.species_list)}]: {sp}{lock_note}")
            if flavor:
                self._put(5, 4, flavor(sp), curses.A_DIM)
            self._put(6, 4, f"{variant_label}: {variants[variant_idx]}")
            self._put(7, 4, f"name (optional): {''.join(name_buf) or '(none)'}")
            arrows = "←/→ species  " if allow_species else ""
            self._put(9, 4, f"{arrows}↑/↓ {variant_label}  type a name  Enter save  Esc cancel", curses.A_DIM)
            self._ascii_render(entity.art_basename(), 11, 6, entity)
            self.screen.refresh()
            key = self._wait_key()
            if key == curses.KEY_LEFT and allow_species:
                species_idx = (species_idx - 1) % len(entity.species_list)
            elif key == curses.KEY_RIGHT and allow_species:
                species_idx = (species_idx + 1) % len(entity.species_list)
            elif key == curses.KEY_UP:
                variant_idx = (variant_idx - 1) % len(variants)
            elif key == curses.KEY_DOWN:
                variant_idx = (variant_idx + 1) % len(variants)
            elif key in (curses.KEY_ENTER, 10, 13):
                with self.homestead.lock:
                    entity.apply_customization(
                        species_idx,
                        display_name="".join(name_buf).strip(),
                        color_variant=variants[variant_idx],
                    )
                self._persist()
                return True
            elif key == 27:
                entity.species, entity.color_variant = orig
                return False
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                if name_buf:
                    name_buf.pop()
            elif 32 <= key <= 126 and len(name_buf) < 24:
                name_buf.append(chr(key))

    def _fish_setup_wizard(self):
        fish = self.homestead.aquarium
        if fish.dead:
            return
        self._profile_wizard(
            "Fish profile — choose species & look", fish, FISH_COLOR_VARIANTS,
            "color", allow_species=fish.stage <= 1, flavor=FishTank.fish_flavor,
        )
        self.homestead.pending_fish_setup = False

    def _barn_setup_wizard(self):
        pen = self.homestead.livestock
        if pen.dead:
            return
        self._profile_wizard(
            "Barn profile — pick your farm friend", pen, LIVESTOCK_COLOR_VARIANTS,
            "coat", allow_species=pen.stage == 0,
            flavor=lambda sp: "gives: " + __import__("homestead_config").LIVESTOCK_PRODUCE[sp]["item"],
        )
        self.homestead.pending_barn_setup = False

    def _crop_setup_wizard(self):
        farm = self.homestead.farm
        idx = farm.species
        variant_idx = FARM_CROP_VARIANTS.index(farm.color_variant) if farm.color_variant in FARM_CROP_VARIANTS else 0
        while True:
            self.screen.erase()
            self._put(1, 2, "Seed shed — choose what to plant next", curses.A_BOLD)
            y = 3
            for i, name in enumerate(farm.species_list):
                info = CROPS.get(name, {})
                line = f"{name:<10} ~{info.get('days', '?')} days  sells {info.get('sell', '?')}c  {info.get('flavor', '')}"
                self._put(y + i, 4, line, self.highlighted if i == idx else None)
            self._put(y + len(farm.species_list) + 1, 4, f"variant: {FARM_CROP_VARIANTS[variant_idx]}")
            self._put(y + len(farm.species_list) + 3, 4, "↑/↓ crop  ←/→ variant  Enter choose  Esc cancel", curses.A_DIM)
            self.screen.refresh()
            key = self._wait_key()
            if key in (curses.KEY_UP, ord("k")):
                idx = (idx - 1) % len(farm.species_list)
            elif key in (curses.KEY_DOWN, ord("j")):
                idx = (idx + 1) % len(farm.species_list)
            elif key in (curses.KEY_LEFT, ord("h")):
                variant_idx = (variant_idx - 1) % len(FARM_CROP_VARIANTS)
            elif key in (curses.KEY_RIGHT, ord("l")):
                variant_idx = (variant_idx + 1) % len(FARM_CROP_VARIANTS)
            elif key in (curses.KEY_ENTER, 10, 13):
                with self.homestead.lock:
                    farm.species = idx
                    farm.color_variant = FARM_CROP_VARIANTS[variant_idx]
                self.homestead.pending_crop_setup = False
                self.say(f"seed choice: {farm.species_name()}")
                return
            elif key in (27, ord("q")):
                return

    # ------------------------------------------------------------------
    # mini games
    # ------------------------------------------------------------------

    KEY_NAMES = {
        curses.KEY_LEFT: "left", ord("h"): "left", ord("a"): "left",
        curses.KEY_RIGHT: "right", ord("l"): "right", ord("d"): "right",
        curses.KEY_UP: "up", ord("k"): "up", ord("w"): "up",
        curses.KEY_DOWN: "down", ord("j"): "down", ord("s"): "down",
        ord(" "): "action", 10: "action", 13: "action", curses.KEY_ENTER: "action",
    }

    def _play(self, game_id):
        cls = GAMES[game_id]
        if not self._game_intro(cls):
            return
        game = cls()
        self.screen.timeout(GAME_TIMEOUT_MS)
        last = time.time()
        try:
            while not game.finished:
                key = self.screen.getch()
                now = time.time()
                game.update(min(0.25, now - last))
                last = now
                if key in (27, ord("q")):
                    game.finish(False, "you walked away")
                    break
                if key != -1:
                    name = self.KEY_NAMES.get(key)
                    if name is None and ord("0") <= key <= ord("9"):
                        name = chr(key)
                    if name:
                        game.handle_key(name)
                self._draw_game(game)
        finally:
            self.screen.timeout(FRAME_TIMEOUT_MS)
        with self.homestead.lock:
            lines = self.homestead.finish_minigame(game)
        self._game_result(game, lines)
        self.say()

    def _game_intro(self, cls):
        self.screen.erase()
        self._put(2, 2, cls.title, curses.A_BOLD)
        self._put(4, 4, f"goal: {cls.goal}")
        self._put(5, 4, f"controls: {cls.controls}")
        self._put(6, 4, f"time limit: {int(cls.duration)}s   q/esc to quit")
        left = self.homestead.minigame_rewards_left(cls.game_id)
        self._put(8, 4, f"rewarded wins left today: {left}/{MINIGAME_DAILY_REWARDS}", curses.A_DIM)
        self._put(10, 4, "press enter to start, esc to go back", self.ok)
        self.screen.refresh()
        while True:
            key = self._wait_key()
            if key in (curses.KEY_ENTER, 10, 13, ord(" ")):
                return True
            if key in (27, ord("q")):
                return False

    def _draw_game(self, game):
        self.maxy, self.maxx = self.screen.getmaxyx()
        self.screen.erase()
        self._put(1, 2, f"~ {game.title} ~", curses.A_BOLD)
        self._put(2, 2, game.status_line(), self.accent)
        top, left = 4, 4
        lines = game.render()
        for i, line in enumerate(lines):
            self._put(top + i, left, line)
        for row, col, width in game.highlights():
            if 0 <= row < len(lines):
                cell = lines[row][col:col + width] or " "
                self._put(top + row, left + col, cell if cell.strip() else "+", self.highlighted)
        self._put(self.maxy - 1, 2, game.controls + " · q quits", curses.A_DIM)
        self.screen.refresh()

    def _game_result(self, game, lines):
        self._draw_game(game)
        y = min(self.maxy - 8, 4 + len(game.render()) + 1)
        headline = "you win! ✿" if game.won else "better luck next time"
        self._put(y, 4, f"{headline} — {game.outcome}", self.ok if game.won else self.warn)
        self._put(y + 1, 4, f"score {game.score}")
        for i, line in enumerate(lines):
            self._put(y + 2 + i, 6, line)
        self._put(self.maxy - 1, 2, "press any key...".ljust(self.maxx - 4), curses.A_DIM)
        self.screen.refresh()
        time.sleep(0.4)
        curses.flushinp()
        self._wait_key()


def main(homestead, data_manager):
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass
    os.environ.setdefault("ESCDELAY", "25")

    def _curses_main(stdscr):
        menu = HomesteadMenu(stdscr, homestead, data_manager)
        menu.run()

    curses.wrapper(_curses_main)
