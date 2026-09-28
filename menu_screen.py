import curses
import getpass
import json
import math
import os
import sys
import threading
import time

from homestead_config import (
    FARM_CROP_VARIANTS,
    FISH_COLOR_VARIANTS,
    HOMESTEAD_BACKDROPS,
    LIVESTOCK_COLOR_VARIANTS,
    TANK_THEMES,
)


class HomesteadMenu:
    def __init__(self, stdscr, homestead, data_manager):
        self.screen = stdscr
        self.homestead = homestead
        self.data = data_manager
        self.exit = False
        self.rendered_art = None
        self.visited_entity = None
        self.screen_lock = threading.RLock()
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        self.screen.keypad(True)
        if curses.has_colors():
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
            self.highlighted = curses.color_pair(1)
            self.accent = curses.color_pair(2)
            self.ok = curses.color_pair(3)
        else:
            self.highlighted = curses.A_REVERSE
            self.accent = curses.A_BOLD
            self.ok = curses.A_BOLD
        self.normal = curses.A_NORMAL
        self.maxy, self.maxx = self.screen.getmaxyx()
        thread = threading.Thread(target=self._live_refresh, daemon=True)
        thread.start()
        if self.homestead.pending_fish_setup:
            self._fish_setup_wizard()

    def _live_refresh(self):
        while not self.exit:
            with self.screen_lock:
                try:
                    self._draw_frame()
                    self.screen.refresh()
                except curses.error:
                    pass
            time.sleep(1)

    def _draw_frame(self):
        self.maxy, self.maxx = self.screen.getmaxyx()
        self.screen.erase()
        theme = self.homestead.tank_theme()
        title = f"~ aquafarm ~ {theme['frame']} (◕‿◕)"
        self.screen.addstr(0, 2, title[: max(0, self.maxx - 4)], curses.A_BOLD)
        env_line = self.homestead.environment_subtitle()
        self.screen.addstr(
            1,
            2,
            env_line[: max(0, self.maxx - 4)],
            self.accent,
        )
        entity = self._focused_entity()
        if self.visited_entity:
            entity = self.visited_entity
        self.screen.addstr(
            2,
            2,
            f"gen {self.homestead.generation} | score {self.homestead.total_score()}",
            curses.A_DIM,
        )
        if entity and not entity.dead and self.homestead.active_area not in (
            "homestead",
            "environment",
            "board",
            "visit",
            "harvest_log",
        ):
            gauge = self._care_gauge(entity)
            self.screen.addstr(3, 14, gauge[: max(0, self.maxx - 16)], curses.A_NORMAL)
        self._draw_art(entity)
        if self.homestead.active_area == "homestead":
            self._draw_main_menu()
        elif self.homestead.active_area == "environment":
            self._draw_environment_menu()
        elif self.homestead.active_area == "board":
            self._draw_board()
        elif self.homestead.active_area == "harvest_log":
            self._draw_harvest_log()
        else:
            self._draw_area_menu()

    def _focused_entity(self):
        if self.homestead.active_area == "homestead":
            return self.homestead.aquarium
        entity = self.homestead.entity_for_area(self.homestead.active_area)
        return entity or self.homestead.aquarium

    def _draw_main_menu(self):
        options = [
            "aquarium",
            "bonsai grove",
            "farm plot",
            "livestock barn",
            "environment & themes",
            "homestead board",
            "visit a friend",
            "harvest history",
            "instructions",
            "exit",
        ]
        self._draw_options(options, 4, "choose an area to tend")

    def _draw_environment_menu(self):
        theme = self.homestead.tank_theme()
        back = self.homestead.backdrop()
        subtitle = f"tank: {theme['label']} | backdrop: {back['label']}"
        options = [
            "cycle tank theme",
            "cycle homestead backdrop",
            "back",
        ]
        self._draw_options(options, 4, subtitle)

    def _draw_area_menu(self):
        area = self.homestead.active_area
        entity = self.homestead.entity_for_area(area)
        subtitle = entity.parse_description()
        if area == "aquarium":
            feed, clean, water = entity.tank_summary()
            subtitle += (
                f" | feed {feed}% clean {clean}% water {water}%"
                f" | health {entity.tank_health}% algae {int(entity.algae_level)}%"
            )
            options = [
                "feed",
                "clean tank",
                "check water",
                "spawn cycle (breed)",
                "fish profile",
                "look",
                "back",
            ]
        elif area == "farm":
            options = ["water crops", "harvest (when mature)", "crop profile", "look", "back"]
        elif area == "livestock":
            options = [
                "feed animals",
                "collect eggs/milk",
                "barn profile",
                "look",
                "back",
            ]
        elif area == "bonsai":
            if self.homestead.is_mature("bonsai"):
                options = ["water", "prune", "harvest bonsai (new gen)", "look", "back"]
            else:
                options = ["water", "prune", "look", "back"]
        else:
            options = ["back"]
        self._draw_options(options, 4, subtitle)

    def _draw_board(self):
        board = self.data.retrieve_board_from_db()
        self.screen.addstr(4, 2, "homestead board (local sqlite)", curses.A_BOLD)
        y = 6
        if not board:
            self.screen.addstr(y, 4, "(empty — be the first caretaker!)")
            y += 1
        else:
            for _, row in list(board.items())[:8]:
                if row.get("dead"):
                    continue
                age = row.get("age") or "?"
                line = (
                    f"{row['owner']}: {row['total_score']}p gen {row['generation']} age {age}"
                )
                self.screen.addstr(y, 4, line[: max(0, self.maxx - 6)])
                y += 1
        self._draw_options(["refresh", "back"], max(y + 1, 9), "shared board · q back")

    def _draw_harvest_log(self):
        self.screen.addstr(4, 2, "harvest history", curses.A_BOLD)
        y = 6
        if not os.path.isfile(self.data.harvest_json_path):
            self.screen.addstr(y, 4, "(no harvests recorded yet)")
            y += 1
        else:
            with open(self.data.harvest_json_path, "r") as handle:
                harvest = json.load(handle)
            for entry in list(harvest.values())[-8:]:
                line = f"{entry.get('area')}: {entry.get('description')} ({entry.get('score')}p)"
                self.screen.addstr(y, 4, line[: max(0, self.maxx - 6)])
                y += 1
        self._draw_options(["back"], max(y + 1, 9), "past harvests")

    def _draw_options(self, options, start_y, subtitle):
        self.screen.addstr(start_y, 2, subtitle[: max(0, self.maxx - 4)], curses.A_BOLD)
        for idx, label in enumerate(options):
            style = self.highlighted if idx == getattr(self, "selected", 0) else self.normal
            line = f"{idx + 1} - {label}"
            self.screen.addstr(start_y + 2 + idx, 4, line[: max(0, self.maxx - 6)], style)

    def _draw_art(self, entity):
        if not entity:
            return
        basename = entity.art_basename()
        xpos = min(max(28, self.maxx // 2), self.maxx - 20)
        if self.rendered_art != basename:
            self.rendered_art = basename
        self._ascii_render(basename, 0, xpos, entity)

    def _art_directory(self):
        local = os.path.join(os.path.dirname(os.path.realpath(__file__)), "art")
        if os.path.isdir(local):
            return local
        return os.path.join(sys.prefix, "share", "aquafarm-art")

    def _ascii_render(self, basename, ypos, xpos, entity=None):
        art_dir = self._art_directory()
        path = os.path.join(art_dir, basename + ".txt")
        if not os.path.isfile(path):
            fallback = os.path.join(art_dir, "homestead_idle.txt")
            path = fallback if os.path.isfile(fallback) else None
        if not path:
            return
        variant_attr = self.normal
        if entity and getattr(entity, "color_variant", "") == "golden" and curses.has_colors():
            variant_attr = curses.color_pair(3) if curses.has_colors() else self.ok
        elif entity and getattr(entity, "color_variant", "") == "shadow" and curses.has_colors():
            variant_attr = curses.A_DIM
        with open(path, "r") as handle:
            lines = handle.readlines()
        for y, line in enumerate(lines[:12]):
            if ypos + y >= self.maxy:
                break
            text = line.rstrip("\n")[: max(0, self.maxx - xpos - 1)]
            if text:
                self.screen.addstr(ypos + y, xpos, text, variant_attr)

    def _info_block(self, entity):
        lines = [
            entity.parse_description(),
            f"ticks: {int(entity.ticks)}",
            f"stage: {entity.stage_list[entity.stage]}",
        ]
        if hasattr(entity, "tank_health"):
            lines.append(f"tank health: {entity.tank_health}%")
        if hasattr(entity, "produce_collected"):
            lines.append(f"produce collected: {entity.produce_collected}")
        y = 14
        for line in lines:
            if y >= self.maxy - 1:
                break
            self.screen.addstr(y, 2, line[: max(0, self.maxx - 4)], curses.A_NORMAL)
            y += 1

    def run(self):
        self.selected = 0
        while not self.exit:
            self._draw_frame()
            self.screen.refresh()
            key = self.screen.getch()
            if key in (curses.KEY_UP, ord("k")):
                self.selected = max(0, self.selected - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                self.selected = min(
                    self.selected + 1, len(self._options_for_state()) - 1
                )
            elif key in (curses.KEY_ENTER, 10, 13):
                self._activate_selection()
            elif key in (ord("q"), ord("Q")):
                if self.homestead.active_area != "homestead":
                    self.homestead.active_area = "homestead"
                    self.selected = 0
                else:
                    self.exit = True

    def _options_for_state(self):
        if self.homestead.active_area == "homestead":
            return [
                "aquarium",
                "bonsai grove",
                "farm plot",
                "livestock barn",
                "environment & themes",
                "homestead board",
                "visit a friend",
                "harvest history",
                "instructions",
                "exit",
            ]
        if self.homestead.active_area == "environment":
            return ["cycle tank theme", "cycle homestead backdrop", "back"]
        if self.homestead.active_area == "board":
            return ["refresh", "back"]
        if self.homestead.active_area == "visit":
            return ["back"]
        if self.homestead.active_area == "harvest_log":
            return ["back"]
        if self.homestead.active_area == "aquarium":
            return [
                "feed",
                "clean tank",
                "check water",
                "spawn cycle (breed)",
                "fish profile",
                "look",
                "back",
            ]
        if self.homestead.active_area == "bonsai":
            if self.homestead.is_mature("bonsai"):
                return ["water", "prune", "harvest bonsai (new gen)", "look", "back"]
            return ["water", "prune", "look", "back"]
        if self.homestead.active_area == "farm":
            return ["water crops", "harvest (when mature)", "crop profile", "look", "back"]
        if self.homestead.active_area == "livestock":
            return [
                "feed animals",
                "collect eggs/milk",
                "barn profile",
                "look",
                "back",
            ]
        return ["back"]

    def _activate_selection(self):
        options = self._options_for_state()
        if self.selected >= len(options):
            self.selected = len(options) - 1
        choice = options[self.selected]
        area = self.homestead.active_area

        if area == "homestead":
            if choice == "aquarium":
                self.homestead.active_area = "aquarium"
            elif choice == "bonsai grove":
                self.homestead.active_area = "bonsai"
            elif choice == "farm plot":
                self.homestead.active_area = "farm"
            elif choice == "livestock barn":
                self.homestead.active_area = "livestock"
            elif choice == "environment & themes":
                self.homestead.active_area = "environment"
            elif choice == "homestead board":
                self.homestead.active_area = "board"
            elif choice == "visit a friend":
                self._visit_friend()
            elif choice == "harvest history":
                self._show_harvest_history()
            elif choice == "instructions":
                self._show_instructions()
            elif choice == "exit":
                self.exit = True
            self.selected = 0
            return

        if area == "environment":
            if choice == "cycle tank theme":
                self.homestead.tank_theme_index = (
                    self.homestead.tank_theme_index + 1
                ) % len(TANK_THEMES)
                self._persist()
            elif choice == "cycle homestead backdrop":
                self.homestead.backdrop_index = (
                    self.homestead.backdrop_index + 1
                ) % len(HOMESTEAD_BACKDROPS)
                self._persist()
            elif choice == "back":
                self.homestead.active_area = "homestead"
                self.selected = 0
            return

        entity = self.homestead.entity_for_area(area)
        if choice == "back":
            self.homestead.active_area = "homestead"
            self.selected = 0
            return
        if choice == "refresh" and area == "board":
            self.data.update_board_json()
            return
        if choice == "look":
            self._show_look(entity)
            return
        if choice == "fish profile" and area == "aquarium":
            self._fish_setup_wizard()
            return
        if choice == "barn profile" and area == "livestock":
            self._barn_setup_wizard()
            return
        if choice == "crop profile" and area == "farm":
            self._crop_setup_wizard()
            return
        if choice == "harvest bonsai (new gen)" and area == "bonsai":
            if self._confirm_harvest("bonsai"):
                self.homestead.harvest_entity("bonsai", self.data)
                self._flash_message("Bonsai harvested — new seed awaits.")
                self._persist()
            return
        if choice == "spawn cycle (breed)" and area == "aquarium":
            if entity.breed_spawn():
                self._flash_message("A new egg cycle begins! (◕‿◕)")
            else:
                self._flash_message("Need adult fish + healthy tank to spawn.")
            self._persist()
            return
        if choice == "harvest (when mature)" and area == "farm":
            if entity.try_harvest() and self._confirm_harvest("farm"):
                self.homestead.harvest_entity("farm", self.data)
                self._flash_message("Harvested! Next generation planted.")
            else:
                self._flash_message("Crops must reach harvest stage first.")
            self._persist()
            return
        if choice == "collect eggs/milk" and area == "livestock":
            bonus = entity.collect_produce()
            if bonus:
                self._flash_message(f"Collected produce (+{bonus} ticks)!")
            else:
                self._flash_message("Feed fresh + grown animals to collect.")
            self._persist()
            return

        verb_map = {
            "feed": "feed",
            "feed animals": "feed",
            "clean tank": "clean",
            "check water": "check_water",
            "water": "water",
            "water crops": "water",
            "prune": "prune",
        }
        verb = verb_map.get(choice)
        if verb and entity:
            entity.perform_care(verb)
            self._persist()

    def _persist(self):
        self.data.save_homestead(self.homestead)
        self.data.write_json_exports(self.homestead)

    def _flash_message(self, msg):
        y = min(self.maxy - 2, 22)
        self.screen.addstr(y, 2, msg[: max(0, self.maxx - 4)], self.ok)
        self.screen.refresh()
        time.sleep(0.8)

    def _care_gauge(self, entity):
        left_pct = max(
            0.0,
            1.0 - ((time.time() - entity.last_care(entity.primary_care)) / 86400),
        )
        filled = int(math.ceil(left_pct * 10))
        return (
            f"({')' * filled}{'.' * (10 - filled)}) {int(left_pct * 100)}% care"
        )

    def _confirm_harvest(self, area):
        entity = self.homestead.entity_for_area(area)
        if not entity or not self.homestead.is_mature(area):
            return False
        bonus = round(0.2 * (self.homestead.generation - 1), 1)
        self.screen.erase()
        lines = [
            f"Ready to harvest your {area} friend?",
            f"Next generation grows at ~{1 + bonus:.1f}x speed.",
            "Continue? (Y/n)",
        ]
        for y, line in enumerate(lines, 2):
            self.screen.addstr(y, 2, line[: max(0, self.maxx - 4)])
        self.screen.refresh()
        key = self.screen.getch()
        return key in (ord("Y"), ord("y"), 10, 13)

    def _get_user_string(self, ypos=15, xpos=2):
        user_string = ""
        while True:
            key = self.screen.getch()
            if key in (curses.KEY_ENTER, 10, 13):
                return user_string.strip()
            if key in (27, ord("q")):
                return ""
            if key in (curses.KEY_BACKSPACE, 127, 8):
                user_string = user_string[:-1]
            elif 32 <= key <= 126 and len(user_string) < 24:
                user_string += chr(key)
            self.screen.addstr(ypos, xpos, " " * (self.maxx - xpos - 1))
            self.screen.addstr(ypos, xpos, user_string[: max(0, self.maxx - xpos - 1)])
            self.screen.refresh()

    def _visit_friend(self):
        self.screen.erase()
        self.screen.addstr(2, 2, "Whose homestead would you like to visit?", curses.A_BOLD)
        if self.homestead.visitors:
            recent = ", ".join(self.homestead.visitors[-5:])
            self.screen.addstr(4, 2, f"Since last time: {recent[: self.maxx - 4]}")
            self.homestead.visitors = []
        weekly = self.data.weekly_visitors_text(getpass.getuser())
        self.screen.addstr(6, 2, f"This week: {weekly[: self.maxx - 4]}")
        self.screen.addstr(8, 2, "username:")
        host = self._get_user_string(8, 12)
        if not host:
            return
        if host.lower() == getpass.getuser().lower():
            self._flash_message("You're already home on the farm!")
            return
        json_path = self.data.guest_homestead_json_path(host)
        description = ""
        if json_path:
            with open(json_path, "r") as handle:
                visitor_data = json.load(handle)
            description = visitor_data.get("description", "")
            self.visited_entity = self._entity_from_visit_json(visitor_data)
        ok, status = self.data.append_guest_care_for_host(host)
        if ok:
            msg = f"...you helped tend ~{host}'s {description}..."
        elif status == "locked":
            msg = f"{host}'s homestead is locked, but you peeked in..."
        else:
            msg = f"Can't find directions to {host}'s homestead..."
        self._flash_message(msg)
        self.visited_entity = None

    def _entity_from_visit_json(self, data):
        from entities.aquarium import FishTank

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

    def _show_harvest_history(self):
        self.homestead.active_area = "harvest_log"
        self.selected = 0

    def _fish_setup_wizard(self):
        fish = self.homestead.aquarium
        species_idx = fish.species
        variant_idx = 0
        if fish.color_variant in FISH_COLOR_VARIANTS:
            variant_idx = FISH_COLOR_VARIANTS.index(fish.color_variant)
        name_buf = list(fish.display_name or "")

        while True:
            self.screen.erase()
            self.screen.addstr(2, 2, "Fish profile — choose species & look", curses.A_BOLD)
            sp = fish.species_list[species_idx]
            var = FISH_COLOR_VARIANTS[variant_idx]
            self.screen.addstr(4, 4, f"species [{species_idx + 1}/{len(fish.species_list)}]: {sp}")
            self.screen.addstr(5, 4, f"color variant: {var}")
            self.screen.addstr(6, 4, f"name (optional): {''.join(name_buf) or '(none)'}")
            self.screen.addstr(
                8,
                4,
                "←/→ species  ↑/↓ variant  type name  Enter save  q cancel",
                curses.A_DIM,
            )
            fish.species = species_idx
            fish.color_variant = var
            self._ascii_render(fish.art_basename(), 0, min(40, self.maxx - 22), fish)
            self.screen.refresh()
            key = self.screen.getch()
            if key in (curses.KEY_LEFT, ord("h")):
                species_idx = (species_idx - 1) % len(fish.species_list)
            elif key in (curses.KEY_RIGHT, ord("l")):
                species_idx = (species_idx + 1) % len(fish.species_list)
            elif key in (curses.KEY_UP, ord("k")):
                variant_idx = (variant_idx - 1) % len(FISH_COLOR_VARIANTS)
            elif key in (curses.KEY_DOWN, ord("j")):
                variant_idx = (variant_idx + 1) % len(FISH_COLOR_VARIANTS)
            elif key in (curses.KEY_ENTER, 10, 13):
                fish.apply_customization(
                    species_idx,
                    display_name="".join(name_buf).strip(),
                    color_variant=FISH_COLOR_VARIANTS[variant_idx],
                )
                self.homestead.pending_fish_setup = False
                self._persist()
                return
            elif key in (ord("q"), ord("Q"), 27):
                self.homestead.pending_fish_setup = False
                return
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                if name_buf:
                    name_buf.pop()
            elif 32 <= key <= 126 and len(name_buf) < 24:
                name_buf.append(chr(key))

    def _barn_setup_wizard(self):
        pen = self.homestead.livestock
        species_idx = pen.species
        variant_idx = 0
        if pen.color_variant in LIVESTOCK_COLOR_VARIANTS:
            variant_idx = LIVESTOCK_COLOR_VARIANTS.index(pen.color_variant)
        name_buf = list(pen.display_name or "")

        while True:
            self.screen.erase()
            self.screen.addstr(2, 2, "Barn profile — pick your farm friend", curses.A_BOLD)
            sp = pen.species_list[species_idx]
            var = LIVESTOCK_COLOR_VARIANTS[variant_idx]
            self.screen.addstr(4, 4, f"species [{species_idx + 1}/{len(pen.species_list)}]: {sp}")
            self.screen.addstr(5, 4, f"coat: {var}")
            self.screen.addstr(6, 4, f"name: {''.join(name_buf) or '(none)'}")
            self.screen.addstr(
                8,
                4,
                "←/→ species  ↑/↓ coat  type name  Enter save  q cancel",
                curses.A_DIM,
            )
            pen.species = species_idx
            pen.color_variant = var
            self._ascii_render(pen.art_basename(), 0, min(40, self.maxx - 22), pen)
            self.screen.refresh()
            key = self.screen.getch()
            if key in (curses.KEY_LEFT, ord("h")):
                species_idx = (species_idx - 1) % len(pen.species_list)
            elif key in (curses.KEY_RIGHT, ord("l")):
                species_idx = (species_idx + 1) % len(pen.species_list)
            elif key in (curses.KEY_UP, ord("k")):
                variant_idx = (variant_idx - 1) % len(LIVESTOCK_COLOR_VARIANTS)
            elif key in (curses.KEY_DOWN, ord("j")):
                variant_idx = (variant_idx + 1) % len(LIVESTOCK_COLOR_VARIANTS)
            elif key in (curses.KEY_ENTER, 10, 13):
                pen.apply_customization(
                    species_idx,
                    display_name="".join(name_buf).strip(),
                    color_variant=LIVESTOCK_COLOR_VARIANTS[variant_idx],
                )
                self.homestead.pending_barn_setup = False
                self._persist()
                return
            elif key in (ord("q"), ord("Q"), 27):
                self.homestead.pending_barn_setup = False
                return
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                if name_buf:
                    name_buf.pop()
            elif 32 <= key <= 126 and len(name_buf) < 24:
                name_buf.append(chr(key))

    def _crop_setup_wizard(self):
        plot = self.homestead.farm
        species_idx = plot.species
        variant_idx = 0
        if plot.color_variant in FARM_CROP_VARIANTS:
            variant_idx = FARM_CROP_VARIANTS.index(plot.color_variant)

        while True:
            self.screen.erase()
            self.screen.addstr(2, 2, "Crop profile — choose seeds", curses.A_BOLD)
            sp = plot.species_list[species_idx]
            var = FARM_CROP_VARIANTS[variant_idx]
            self.screen.addstr(4, 4, f"crop [{species_idx + 1}/{len(plot.species_list)}]: {sp}")
            self.screen.addstr(5, 4, f"variant: {var}")
            self.screen.addstr(
                7,
                4,
                "←/→ crop  ↑/↓ variant  Enter plant  q cancel",
                curses.A_DIM,
            )
            plot.species = species_idx
            plot.color_variant = var
            self._ascii_render(plot.art_basename(), 0, min(40, self.maxx - 22), plot)
            self.screen.refresh()
            key = self.screen.getch()
            if key in (curses.KEY_LEFT, ord("h")):
                species_idx = (species_idx - 1) % len(plot.species_list)
            elif key in (curses.KEY_RIGHT, ord("l")):
                species_idx = (species_idx + 1) % len(plot.species_list)
            elif key in (curses.KEY_UP, ord("k")):
                variant_idx = (variant_idx - 1) % len(FARM_CROP_VARIANTS)
            elif key in (curses.KEY_DOWN, ord("j")):
                variant_idx = (variant_idx + 1) % len(FARM_CROP_VARIANTS)
            elif key in (curses.KEY_ENTER, 10, 13):
                plot.apply_customization(
                    species_idx,
                    color_variant=FARM_CROP_VARIANTS[variant_idx],
                )
                self.homestead.pending_crop_setup = False
                self._persist()
                return
            elif key in (ord("q"), ord("Q"), 27):
                self.homestead.pending_crop_setup = False
                return

    def _show_instructions(self):
        self.screen.erase()
        lines = [
            "Aquafarm: daily homestead care (24h windows).",
            "Feed fish, clean tank, check water — algae slows growth slightly.",
            "Water crops; harvest at maturity for a new generation.",
            "Feed livestock (horses, sheep, pigs & more); collect when grown.",
            "Crop & barn profiles: pick species before you tend.",
            "Visit friends to help their homestead (shared hosts).",
            "Environment menu: tank theme + retro farm backdrop.",
            "Neglect primary care 5 days and a friend may pass on.",
            "Press any key to return...",
        ]
        for y, line in enumerate(lines):
            self.screen.addstr(y + 2, 2, line[: max(0, self.maxx - 4)])
        self.screen.refresh()
        self.screen.getch()

    def _show_look(self, entity):
        self.screen.erase()
        self._draw_art(entity)
        self._info_block(entity)
        self.screen.addstr(self.maxy - 2, 2, "any key to return...", curses.A_DIM)
        self.screen.refresh()
        self.screen.getch()


def main(homestead, data_manager):
    def _curses_main(stdscr):
        menu = HomesteadMenu(stdscr, homestead, data_manager)
        menu.run()

    curses.wrapper(_curses_main)
