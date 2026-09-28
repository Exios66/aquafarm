import curses
import os
import threading
import time

from homestead_config import FISH_COLOR_VARIANTS, HOMESTEAD_BACKDROPS, TANK_THEMES


class HomesteadMenu:
    def __init__(self, stdscr, homestead, data_manager):
        self.screen = stdscr
        self.homestead = homestead
        self.data = data_manager
        self.exit = False
        self.rendered_art = None
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
        self.screen.addstr(
            2,
            2,
            f"gen {self.homestead.generation} | score {self.homestead.total_score()}",
            curses.A_DIM,
        )
        self._draw_art(entity)
        if self.homestead.active_area == "homestead":
            self._draw_main_menu()
        elif self.homestead.active_area == "environment":
            self._draw_environment_menu()
        elif self.homestead.active_area == "board":
            self._draw_board()
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
        elif area == "bonsai":
            options = ["water", "prune", "look", "back"]
        elif area == "farm":
            options = ["water crops", "harvest (when mature)", "look", "back"]
        elif area == "livestock":
            options = ["feed animals", "collect eggs/milk", "look", "back"]
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
            for _, row in list(board.items())[:6]:
                line = f"{row['owner']}: score {row['total_score']} gen {row['generation']}"
                self.screen.addstr(y, 4, line[: max(0, self.maxx - 6)])
                y += 1
        self._draw_options(["refresh", "back"], max(y + 1, 9), "shared board")

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

    def _ascii_render(self, basename, ypos, xpos, entity=None):
        art_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "art")
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
                "instructions",
                "exit",
            ]
        if self.homestead.active_area == "environment":
            return ["cycle tank theme", "cycle homestead backdrop", "back"]
        if self.homestead.active_area == "board":
            return ["refresh", "back"]
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
            return ["water", "prune", "look", "back"]
        if self.homestead.active_area == "farm":
            return ["water crops", "harvest (when mature)", "look", "back"]
        if self.homestead.active_area == "livestock":
            return ["feed animals", "collect eggs/milk", "look", "back"]
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
        if choice == "spawn cycle (breed)" and area == "aquarium":
            if entity.breed_spawn():
                self._flash_message("A new egg cycle begins! (◕‿◕)")
            else:
                self._flash_message("Need adult fish + healthy tank to spawn.")
            self._persist()
            return
        if choice == "harvest (when mature)" and area == "farm":
            if entity.try_harvest():
                self.homestead.harvest_entity("farm")
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

    def _show_instructions(self):
        self.screen.erase()
        lines = [
            "Aquafarm: daily homestead care (24h windows).",
            "Feed fish, clean tank, check water — algae slows growth slightly.",
            "Water crops; harvest at maturity for a new generation.",
            "Feed livestock; collect when grown for bonus ticks.",
            "Environment menu: tank theme + homestead backdrop.",
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
