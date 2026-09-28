import threading
import time

from entities import BonsaiTree, FarmPlot, FishTank, LivestockPen
from homestead_config import HOMESTEAD_BACKDROPS, TANK_THEMES


class Homestead:
    """One save file holds every care domain on the player's homestead."""

    def __init__(self, generation=1):
        self.generation = generation
        self.aquarium = FishTank(generation=generation)
        self.bonsai = BonsaiTree(generation=generation)
        self.farm = FarmPlot(generation=generation)
        self.livestock = LivestockPen(generation=generation)
        self.active_area = "homestead"
        self.tank_theme_index = 0
        self.backdrop_index = 0
        self.pending_fish_setup = True
        self.pending_barn_setup = False
        self.pending_crop_setup = False
        self.visitors = []
        self._life_thread = None
        self._entity_was_dead = {}

    def migrate_properties(self):
        for entity in self.all_entities():
            entity.migrate_properties()
        if not hasattr(self, "active_area"):
            self.active_area = "homestead"
        if not hasattr(self, "tank_theme_index"):
            self.tank_theme_index = 0
        if not hasattr(self, "backdrop_index"):
            self.backdrop_index = 0
        if not hasattr(self, "pending_fish_setup"):
            self.pending_fish_setup = False
        if not hasattr(self, "pending_barn_setup"):
            self.pending_barn_setup = False
        if not hasattr(self, "pending_crop_setup"):
            self.pending_crop_setup = False
        if not hasattr(self, "visitors"):
            self.visitors = []
        if not hasattr(self, "_entity_was_dead"):
            self._entity_was_dead = {}
        self._life_thread = None
        self._sync_death_tracking()

    def tank_theme(self):
        idx = max(0, min(self.tank_theme_index, len(TANK_THEMES) - 1))
        return TANK_THEMES[idx]

    def backdrop(self):
        idx = max(0, min(self.backdrop_index, len(HOMESTEAD_BACKDROPS) - 1))
        return HOMESTEAD_BACKDROPS[idx]

    def environment_subtitle(self):
        theme = self.tank_theme()
        back = self.backdrop()
        return f"{theme['subtitle']} | {back['banner']}"

    def to_json_dict(self):
        return {
            "generation": self.generation,
            "total_score": self.total_score(),
            "tank_theme": self.tank_theme()["id"],
            "homestead_backdrop": self.backdrop()["id"],
            "areas": {
                key: self.entity_for_area(key).to_json_dict()
                for key in ("aquarium", "bonsai", "farm", "livestock")
            },
        }

    def all_entities(self):
        return [self.aquarium, self.bonsai, self.farm, self.livestock]

    def entity_for_area(self, area):
        mapping = {
            "aquarium": self.aquarium,
            "bonsai": self.bonsai,
            "farm": self.farm,
            "livestock": self.livestock,
        }
        return mapping.get(area)

    def total_score(self):
        return sum(int(e.ticks) for e in self.all_entities() if not e.dead)

    def area_keys(self):
        return ("aquarium", "bonsai", "farm", "livestock")

    def apply_guest_timestamps(self, timestamps):
        """Merge community care timestamps into each living entity (Botany-style)."""
        if not timestamps:
            return
        timestamps = sorted(t for t in timestamps if t <= int(time.time()))
        if not timestamps:
            return
        timestamp_diffs = [(j - i) / 86400.0 for i, j in zip(timestamps[:-1], timestamps[1:])]
        last_valid_element = next((x for x in timestamp_diffs if x > 5), None)
        if last_valid_element is None:
            effective = timestamps[-1]
        else:
            last_valid_index = timestamp_diffs.index(last_valid_element)
            effective = timestamps[: last_valid_index + 1][-1]
        for entity in self.all_entities():
            if entity.dead:
                continue
            verb = entity.primary_care
            if effective > entity.last_care(verb):
                entity.care_timestamps[verb] = effective

    def _sync_death_tracking(self):
        for key in self.area_keys():
            entity = self.entity_for_area(key)
            if entity:
                self._entity_was_dead[key] = entity.dead

    def refresh_offline_ticks(self):
        """Credit score for offline time while primary care was still valid."""
        now = int(time.time())
        bonus = round(0.2 * (self.generation - 1), 1)
        for entity in self.all_entities():
            if entity.dead:
                continue
            entity.dead_check()
            if entity.dead:
                continue
            last = entity.last_time
            cared_until = entity.last_care(entity.primary_care) + 24 * 3600
            start = max(last, entity.last_care(entity.primary_care))
            end = min(now, cared_until)
            gap = max(0, end - start)
            entity.ticks += gap * (1 + bonus) / 120.0
            entity.last_time = now

    def start_life(self, data_manager):
        if self._life_thread and self._life_thread.is_alive():
            return
        self._life_thread = threading.Thread(
            target=self._life_loop, args=(data_manager,), daemon=True
        )
        self._life_thread.start()

    def _life_loop(self, data_manager):
        counter = 0
        while True:
            bonus = round(0.2 * (self.generation - 1), 1)
            for key in self.area_keys():
                entity = self.entity_for_area(key)
                if not entity:
                    continue
                was_dead = self._entity_was_dead.get(key, entity.dead)
                entity.tick_life(bonus)
                if not was_dead and entity.dead:
                    data_manager.record_entity_harvest(self, key, entity)
                self._entity_was_dead[key] = entity.dead
            counter += 1
            if counter % 3 == 0:
                data_manager.save_homestead(self)
                data_manager.write_json_exports(self)
                data_manager.update_board_db(self)
            if counter % 30 == 0:
                data_manager.update_board_json()
                counter = 0
            time.sleep(2)

    def harvest_entity(self, area, data_manager=None):
        entity = self.entity_for_area(area)
        if not entity or entity.dead:
            return False
        if entity.stage < len(entity.stage_list) - 1:
            return False
        if data_manager is not None:
            data_manager.record_entity_harvest(self, area, entity)
        entity.dead = True
        self.generation += 1
        replacement = type(entity)(generation=self.generation)
        if area == "aquarium":
            self.aquarium = replacement
            self.pending_fish_setup = True
        elif area == "bonsai":
            self.bonsai = replacement
        elif area == "farm":
            self.farm = replacement
            self.pending_crop_setup = True
        elif area == "livestock":
            self.livestock = replacement
            self.pending_barn_setup = True
        self._sync_death_tracking()
        return True

    def is_mature(self, area):
        entity = self.entity_for_area(area)
        if not entity or entity.dead:
            return False
        return entity.stage >= len(entity.stage_list) - 1
