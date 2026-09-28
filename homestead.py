import threading
import time

from entities import BonsaiTree, FarmField, FishTank, LivestockPen
from homestead_config import SEASON_ADVANCE_EVERY_LOGIN_DAYS


class Homestead:
    """One save file holds every care domain on the player's homestead."""

    def __init__(self, generation=1):
        self.generation = generation
        self.aquarium = FishTank(generation=generation)
        self.bonsai = BonsaiTree(generation=generation)
        self.farm = FarmField(generation=generation)
        self.livestock = LivestockPen(generation=generation)
        self.active_area = "homestead"
        self.tank_theme_index = 0
        self.backdrop_index = 0
        self.pending_fish_setup = True
        self._life_thread = None
        self.login_day_stamp = self._today_stamp()
        self.login_days_logged = 1

    @staticmethod
    def _today_stamp():
        return int(time.time()) // 86400

    def migrate_properties(self):
        from entities.farm import FarmField as FF

        if type(self.farm).__name__ == "FarmPlot" and not hasattr(self.farm, "slots"):
            old = self.farm
            self.farm = FF(generation=old.generation, species=old.species)
            self.farm.stage = getattr(old, "stage", 0)
            self.farm.ticks = getattr(old, "ticks", 0)
            self.farm.dead = getattr(old, "dead", False)
            if self.farm.stage > 0 or self.farm.ticks > 0:
                self.farm.slots[0].stage = min(
                    self.farm.stage, len(self.farm.stage_list) - 1
                )
                self.farm.slots[0].ticks = self.farm.ticks
                self.farm.slots[0].planted = True
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
        if not hasattr(self, "login_day_stamp"):
            self.login_day_stamp = self._today_stamp()
        if not hasattr(self, "login_days_logged"):
            self.login_days_logged = 1
        self._life_thread = None

    def note_login_day(self):
        today = self._today_stamp()
        if today > self.login_day_stamp:
            self.login_days_logged += 1
            self.login_day_stamp = today
            if self.login_days_logged % SEASON_ADVANCE_EVERY_LOGIN_DAYS == 0:
                if hasattr(self.farm, "advance_season"):
                    self.farm.advance_season()

    def tank_theme(self):
        from homestead_config import TANK_THEMES

        idx = max(0, min(self.tank_theme_index, len(TANK_THEMES) - 1))
        return TANK_THEMES[idx]

    def backdrop(self):
        from homestead_config import HOMESTEAD_BACKDROPS

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
            "login_days_logged": self.login_days_logged,
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

    def refresh_offline_ticks(self):
        """Credit score for offline time while primary care was still valid."""
        self.note_login_day()
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
            for entity in self.all_entities():
                entity.tick_life(bonus)
            counter += 1
            if counter % 3 == 0:
                data_manager.save_homestead(self)
                data_manager.write_json_exports(self)
                data_manager.update_board_db(self)
            if counter % 30 == 0:
                data_manager.update_board_json()
                counter = 0
            time.sleep(2)

    def harvest_entity(self, area):
        entity = self.entity_for_area(area)
        if not entity or entity.dead:
            return False
        if area == "farm" and hasattr(entity, "try_harvest"):
            if entity.try_harvest():
                self.generation += 1
                entity.generation = self.generation
                return True
            return False
        if entity.stage < len(entity.stage_list) - 1:
            return False
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
        elif area == "livestock":
            self.livestock = replacement
        return True

    def grant_farm_compost(self, amount=1):
        if hasattr(self.farm, "compost"):
            self.farm.compost += amount
