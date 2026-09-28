import threading
import time

from entities import BonsaiTree, FarmField, FishTank, LivestockPen
from homestead_config import SEASON_ADVANCE_EVERY_LOGIN_DAYS, SHOP_ITEMS
from progression import Progress

AREAS = ("aquarium", "bonsai", "farm", "livestock")
AREA_LABELS = {
    "aquarium": "aquarium",
    "bonsai": "bonsai grove",
    "farm": "farm field",
    "livestock": "livestock barn",
}
# How much a successful action is worth logging again (stops stat farming by
# mashing the same care key; the care itself still refreshes every time).
CARE_EVENT_COOLDOWN = 3600
MINIGAME_GROWTH_REWARD = 900


class Homestead:
    """One save file holds every care domain on the player's homestead.

    All player actions go through the ``do_*`` methods, which return a short
    message for the UI and log events for tasks and achievements. Extra
    notices (task completions, achievements) queue up in ``notices``.
    """

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
        self.pending_barn_setup = True
        self.pending_crop_setup = False
        self.visitors = []
        self.progress = Progress()
        self.notices = []
        self._entity_was_dead = {}
        self.login_day_stamp = self._today_stamp()
        self.login_days_logged = 1
        self._init_runtime()

    def _init_runtime(self):
        self.lock = threading.RLock()
        self._life_thread = None

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop("lock", None)
        state.pop("_life_thread", None)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._init_runtime()

    @staticmethod
    def _today_stamp():
        return int(time.time()) // 86400

    def migrate_properties(self):
        if not isinstance(self.farm, FarmField):
            old = self.farm
            self.farm = FarmField(generation=getattr(old, "generation", self.generation))
            self.farm.ticks = getattr(old, "ticks", 0)
            self.farm.dead = getattr(old, "dead", False)
            if getattr(old, "stage", 0) > 0 or getattr(old, "ticks", 0) > 0:
                slot = self.farm.slots[0]
                slot.planted = True
                slot.species = getattr(old, "species", 0)
                slot.stage = min(getattr(old, "stage", 0), len(slot.stage_list) - 1)
        for entity in self.all_entities():
            entity.migrate_properties()
        defaults = {
            "active_area": "homestead",
            "tank_theme_index": 0,
            "backdrop_index": 0,
            "pending_fish_setup": False,
            "pending_barn_setup": False,
            "pending_crop_setup": False,
            "visitors": [],
            "notices": [],
            "_entity_was_dead": {},
            "login_day_stamp": self._today_stamp(),
            "login_days_logged": 1,
        }
        for key, value in defaults.items():
            if not hasattr(self, key):
                setattr(self, key, value)
        if not hasattr(self, "progress"):
            self.progress = Progress()
        self.progress.migrate()
        if not hasattr(self, "lock"):
            self._init_runtime()
        self._sync_death_tracking()

    # -- events -------------------------------------------------------------

    def record(self, event, amount=1):
        notices = self.progress.record(event, amount)
        self.notices.extend(notices)
        return notices

    def _earn(self, coins):
        self.notices.extend(self.progress.earn(coins))

    def pop_notices(self):
        notices, self.notices = self.notices, []
        return notices

    def _care_counts(self, entity, verb):
        return entity.seconds_since(verb) >= CARE_EVENT_COOLDOWN

    def _care(self, entity, verb, event, done_msg):
        if entity.dead:
            return f"{AREA_LABELS[entity.domain]} needs a new start first"
        counts = self._care_counts(entity, verb)
        entity.perform_care(verb)
        if counts:
            self.record(event)
        return done_msg

    # -- seasons / environment ----------------------------------------------

    def note_login_day(self):
        today = self._today_stamp()
        if today > self.login_day_stamp:
            self.login_days_logged += 1
            self.login_day_stamp = today
            if self.login_days_logged % SEASON_ADVANCE_EVERY_LOGIN_DAYS == 0:
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

    # -- aggregate state ----------------------------------------------------

    def to_json_dict(self):
        return {
            "generation": self.generation,
            "total_score": self.total_score(),
            "tank_theme": self.tank_theme()["id"],
            "homestead_backdrop": self.backdrop()["id"],
            "login_days_logged": self.login_days_logged,
            "progress": self.progress.to_json_dict(),
            "areas": {key: self.entity_for_area(key).to_json_dict() for key in AREAS},
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
        return AREAS

    def generation_bonus(self):
        return round(0.2 * (self.generation - 1), 1)

    def attention_list(self):
        """Human-readable reminders for anything that needs doing."""
        todo = []
        if self.aquarium.dead:
            todo.append("aquarium: start a new tank")
        elif self.aquarium.needs_care():
            todo.append("aquarium: feed the fish")
        elif not self.aquarium.care_fresh("clean"):
            todo.append("aquarium: clean the tank")
        if self.bonsai.dead:
            todo.append("bonsai: plant a new seed")
        elif self.bonsai.needs_care():
            todo.append("bonsai: water the tree")
        elif self.bonsai.can_prune():
            todo.append("bonsai: ready to prune")
        if self.farm.needs_care():
            todo.append("farm: water the crops")
        if self.farm.mature_slots():
            todo.append("farm: crops ready to harvest")
        elif not self.farm.dead and self.farm.planted_count() < self.farm.NUM_SLOTS:
            todo.append("farm: empty plot to plant")
        if self.livestock.dead:
            todo.append("barn: welcome a new animal")
        elif self.livestock.needs_care():
            todo.append(f"barn: feed the {self.livestock.species_name()}")
        elif self.livestock.can_produce():
            todo.append(f"barn: {self.livestock.produce_info()['label']}")
        return todo

    def area_needs_attention(self, area):
        prefix = {"aquarium": "aquarium", "bonsai": "bonsai", "farm": "farm", "livestock": "barn"}[area]
        return any(item.startswith(prefix + ":") for item in self.attention_list())

    # -- guest care / offline -----------------------------------------------

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
        for key in AREAS:
            entity = self.entity_for_area(key)
            if entity:
                self._entity_was_dead[key] = entity.dead

    def refresh_offline_ticks(self, now=None):
        """Credit growth for offline time that fell inside a fresh care window."""
        self.note_login_day()
        now = int(now if now is not None else time.time())
        bonus = self.generation_bonus()
        for entity in self.all_entities():
            if entity.dead:
                continue
            cared_from = entity.last_care(entity.primary_care)
            start = max(entity.last_time, cared_from)
            end = min(now, cared_from + 24 * 3600)
            entity.advance(max(0, end - start), bonus)
            entity.last_time = now
            entity.dead_check()

    # -- life loop ----------------------------------------------------------

    def start_life(self, data_manager):
        if self._life_thread and self._life_thread.is_alive():
            return
        self._life_thread = threading.Thread(
            target=self._life_loop, args=(data_manager,), daemon=True
        )
        self._life_thread.start()

    def life_step(self, data_manager=None, dt=1.0):
        with self.lock:
            bonus = self.generation_bonus()
            for key in AREAS:
                entity = self.entity_for_area(key)
                was_dead = self._entity_was_dead.get(key, entity.dead)
                entity.tick_life(bonus, dt)
                if not was_dead and entity.dead:
                    self.notices.append(f"Your {AREA_LABELS[key]} friend has passed on...")
                    if data_manager is not None:
                        data_manager.record_entity_harvest(self, key, entity)
                self._entity_was_dead[key] = entity.dead

    def _life_loop(self, data_manager):
        counter = 0
        step = 2
        while True:
            self.life_step(data_manager, dt=step)
            counter += 1
            if counter % 3 == 0:
                data_manager.save_homestead(self)
                data_manager.write_json_exports(self)
                data_manager.update_board_db(self)
            if counter % 30 == 0:
                data_manager.update_board_json()
                counter = 0
            time.sleep(step)

    # -- generations --------------------------------------------------------

    def is_mature(self, area):
        entity = self.entity_for_area(area)
        return bool(entity) and entity.is_mature()

    def can_restart(self, area):
        """Mature friends can be retired for a new generation; dead ones replaced."""
        entity = self.entity_for_area(area)
        if area == "farm":
            return entity.dead
        return entity.dead or entity.is_mature()

    def harvest_entity(self, area, data_manager=None):
        """Farm: harvest the active plot. Others: retire a mature friend (new gen)."""
        entity = self.entity_for_area(area)
        if not entity or entity.dead:
            return False
        if area == "farm":
            return self.harvest_crop() is not None
        if not entity.is_mature():
            return False
        return self._restart_area(area, data_manager, retired=True)

    def _restart_area(self, area, data_manager=None, retired=False):
        entity = self.entity_for_area(area)
        if data_manager is not None and not entity.dead:
            data_manager.record_entity_harvest(self, area, entity)
        if retired:
            self.generation += 1
            self.record("generation_up")
        replacement = type(entity)(generation=self.generation)
        if area == "farm":
            replacement.season_phase = entity.season_phase
            replacement.compost = entity.compost
        setattr(self, area, replacement)
        if area == "aquarium":
            self.pending_fish_setup = True
        elif area == "livestock":
            self.pending_barn_setup = True
        self._sync_death_tracking()
        return True

    def do_new_start(self, area, data_manager=None):
        """Retire a mature friend or replace a lost one."""
        if not self.can_restart(area):
            return "not ready for a new generation yet"
        entity = self.entity_for_area(area)
        if entity.dead:
            self._restart_area(area, data_manager, retired=False)
            return f"a fresh start for your {AREA_LABELS[area]}"
        if area == "bonsai":
            self.progress.add_item("bonsai")
            self.record("bonsai_harvested")
            self._restart_area(area, data_manager, retired=True)
            return "bonsai finished & boxed for market — a new seed awaits"
        self._restart_area(area, data_manager, retired=True)
        if area == "aquarium":
            self._earn(60)
            return "your fish retired to the big pond (+60c) — new eggs arrive"
        self._earn(80)
        return "sent to a sunny pasture (+80c) — a new baby arrives"

    # -- aquarium -----------------------------------------------------------

    def do_feed_fish(self):
        return self._care(self.aquarium, "feed", "fish_fed", "sprinkled some flakes (◕‿◕)")

    def do_clean_tank(self):
        return self._care(self.aquarium, "clean", "tank_cleaned", "scrubbed the glass — sparkly!")

    def do_check_water(self):
        return self._care(self.aquarium, "check_water", "water_checked", "water tested & balanced")

    def do_breed(self):
        if not self.aquarium.breed_spawn():
            return "need an adult fish and a healthy tank (all care >40%)"
        self.record("fish_spawned")
        self._earn(30)
        return "a new egg cycle begins! pet shop paid 30c for the extra fry"

    # -- bonsai -------------------------------------------------------------

    def do_water_bonsai(self):
        return self._care(self.bonsai, "water", "bonsai_watered", "the soil drinks it up")

    def do_prune(self):
        tree = self.bonsai
        if tree.dead:
            return "bonsai grove needs a new seed first"
        if tree.stage == 0:
            return "nothing to prune on a seed yet"
        if not tree.prune():
            return "already neatly pruned today"
        self.progress.add_item("clipping")
        self.record("bonsai_pruned")
        return "snip snip — kept a clipping for market"

    # -- farm ---------------------------------------------------------------

    def do_water_crops(self):
        return self._care(self.farm, "water", "crops_watered", "all three plots watered")

    def do_select_plot(self, index=None):
        farm = self.farm
        index = (farm.active_slot + 1) % farm.NUM_SLOTS if index is None else index
        farm.select_slot(index)
        return f"now tending plot {farm.active_slot + 1}"

    def do_cycle_seed(self, step=1):
        farm = self.farm
        farm.species = (farm.species + step) % len(farm.species_list)
        return f"seed choice: {farm.species_list[farm.species]}"

    def do_plant(self):
        farm = self.farm
        if farm.dead:
            return "the field needs a new start first"
        if not farm.plant_crop(farm.species):
            return f"plot {farm.active_slot + 1} is already growing something"
        self.record("crop_planted")
        return farm.last_action

    def do_fertilize(self):
        if not self.farm.try_fertilize():
            return "no compost — harvest streaks, barn produce or the shop give some"
        self.record("fertilized")
        return "soil nourished with compost (+12 soil)"

    def harvest_crop(self, slot_index=None):
        result = self.farm.try_harvest(slot_index)
        if result is None:
            return None
        crop, qty = result
        self.progress.add_item(crop, qty)
        self.record("crop_harvested")
        return crop, qty

    def do_harvest(self, slot_index=None):
        result = self.harvest_crop(slot_index)
        if result is None:
            return "this plot isn't ready to harvest"
        crop, qty = result
        return f"harvested {qty} {crop} — replant for a rotation bonus"

    def do_harvest_all(self):
        got = [self.harvest_crop(i) for i in self.farm.mature_slots()]
        got = [g for g in got if g]
        if not got:
            return "nothing is ripe yet"
        return "harvested " + ", ".join(f"{qty} {crop}" for crop, qty in got)

    # -- livestock ----------------------------------------------------------

    def do_feed_animal(self):
        return self._care(
            self.livestock, "feed", "animal_fed",
            f"the {self.livestock.species_name()} munches happily",
        )

    def do_groom(self):
        pen = self.livestock
        if pen.dead:
            return "the barn needs a new friend first"
        counts = self._care_counts(pen, "groom")
        pen.perform_care("groom")
        if counts:
            self.record("animal_groomed")
        return f"brushed the {pen.species_name()} — shiny coat!"

    def do_gather_produce(self):
        pen = self.livestock
        blocker = pen.produce_blocker()
        if blocker:
            return blocker
        item, qty, _ = pen.gather_produce()
        self.progress.add_item(item, qty)
        self.farm.compost += 1
        self.record("produce_collected")
        return f"{pen.produce_info()['label']}: +{qty} {item}, +1 compost"

    # -- market -------------------------------------------------------------

    def do_sell(self, item, qty=None):
        have = self.progress.inventory.get(item, 0)
        qty = have if qty is None else min(qty, have)
        if qty <= 0:
            return f"no {item} to sell"
        self.progress.remove_item(item, qty)
        coins = self.progress.price_of(item) * qty
        self._earn(coins)
        self.record("item_sold", qty)
        return f"sold {qty} {item} for {coins}c"

    def do_sell_all(self):
        items = sorted(self.progress.inventory.items())
        if not items:
            return "nothing to sell — go gather some goods"
        total_qty = sum(q for _, q in items)
        coins = sum(self.progress.price_of(k) * q for k, q in items)
        self.progress.inventory.clear()
        self._earn(coins)
        self.record("item_sold", total_qty)
        return f"sold {total_qty} goods for {coins}c"

    @staticmethod
    def shop_item(item_id):
        return next((s for s in SHOP_ITEMS if s["id"] == item_id), None)

    def do_buy(self, item_id):
        item = self.shop_item(item_id)
        if item is None:
            return "the shopkeeper looks puzzled"
        if item["kind"] == "decoration" and item_id in self.progress.decorations:
            return f"you already own the {item['label']}"
        blocked = self._shop_blocker(item_id)
        if blocked:
            return blocked
        if not self.progress.spend(item["price"]):
            return f"need {item['price']}c (you have {self.progress.coins}c)"
        self._apply_shop_item(item_id)
        if item["kind"] == "decoration":
            self.progress.decorations.append(item_id)
            self.record("decoration_bought")
        self.record("item_bought")
        return f"bought {item['label']} for {item['price']}c"

    def _shop_blocker(self, item_id):
        targets = {
            "algae_scrubber": self.aquarium,
            "conditioner": self.aquarium,
            "growth_tonic": self.bonsai,
            "premium_feed": self.livestock,
        }
        entity = targets.get(item_id)
        if entity is not None and entity.dead:
            return f"your {AREA_LABELS[entity.domain]} needs a new start first"
        return None

    def _apply_shop_item(self, item_id):
        if item_id == "compost":
            self.farm.compost += 1
        elif item_id == "algae_scrubber":
            self.aquarium.scrub_algae(50)
        elif item_id == "conditioner":
            self.aquarium.condition_water(20)
        elif item_id == "growth_tonic":
            self.bonsai.boost_growth(7200)
        elif item_id == "premium_feed":
            self.livestock.boost_growth(7200)

    # -- mini games ---------------------------------------------------------

    def finish_minigame(self, game):
        """Apply rewards for a finished mini game; returns summary lines."""
        progress = self.progress
        lines = []
        self.record("minigame_played")
        if progress.note_best(game.game_id, game.score) and game.score:
            lines.append(f"new personal best: {game.score}!")
        if not game.won:
            lines.append("no reward this time — try again!")
            return lines
        self.record("minigame_won")
        if not progress.use_minigame_reward(game.game_id):
            lines.append("played for fun (daily rewards used up)")
            return lines
        coins = 15 + game.score // 20
        self._earn(coins)
        lines.append(f"+{coins} coins")
        entity = self.entity_for_area(game.area)
        if entity is not None and not entity.dead:
            entity.boost_growth(MINIGAME_GROWTH_REWARD)
            lines.append(f"your {AREA_LABELS[game.area]} grew a little (+15m)")
        if game.game_id == "fishing":
            progress.add_item("river fish")
            self.record("fish_caught")
            lines.append("+1 river fish")
        elif game.game_id == "pruning":
            progress.add_item("clipping", 2)
            lines.append("+2 clippings")
        elif game.game_id == "crows":
            self.farm.soil_quality = min(100, self.farm.soil_quality + 5)
            lines.append("+5 soil (no pecked sprouts)")
        elif game.game_id == "eggcatch":
            eggs = max(1, getattr(game, "caught", 0) // 3)
            progress.add_item("egg", eggs)
            lines.append(f"+{eggs} eggs")
        return lines

    def minigame_rewards_left(self, game_id):
        return self.progress.minigame_rewards_left(game_id)

    # -- compatibility -------------------------------------------------------

    def grant_farm_compost(self, amount=1):
        self.farm.compost += amount
