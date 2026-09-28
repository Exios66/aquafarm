import errno
import getpass
import json
import os
import pickle
import sqlite3
import time

from homestead import Homestead


class DataManager:
    user_dir = os.path.expanduser("~")
    aquafarm_dir = os.path.join(user_dir, ".aquafarm")
    game_dir = os.path.dirname(os.path.realpath(__file__))
    board_db_path = os.path.join(game_dir, "sqlite", "homestead_board.sqlite")
    board_json_path = os.path.join(game_dir, "homestead_board.json")

    def __init__(self):
        self.this_user = getpass.getuser()
        try:
            os.makedirs(self.aquafarm_dir)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
        self.savefile_path = os.path.join(
            self.aquafarm_dir, f"{self.this_user}_homestead.dat"
        )
        self.visitors_json_path = os.path.join(self.aquafarm_dir, "visitors.json")
        self.harvest_file_path = os.path.join(self.aquafarm_dir, "harvest_file.dat")
        self.harvest_json_path = os.path.join(self.aquafarm_dir, "harvest_file.json")

    def _ensure_visitors_file(self):
        if not os.path.isfile(self.visitors_json_path):
            with open(self.visitors_json_path, "w") as handle:
                json.dump([], handle)
            os.chmod(self.visitors_json_path, 0o666)

    def entity_age_formatted(self, entity):
        age_seconds = entity.entity_age_seconds()
        days, rem = divmod(age_seconds, 24 * 60 * 60)
        hours, rem = divmod(rem, 60 * 60)
        minutes, seconds = divmod(rem, 60)
        return f"{days}d:{hours}h:{minutes}m:{seconds}s"

    def homestead_age_formatted(self, homestead):
        if not homestead.all_entities():
            return "0d:0h:0m:0s"
        start = min(e.start_time for e in homestead.all_entities())
        age_seconds = max(0, int(time.time()) - start)
        days, rem = divmod(age_seconds, 24 * 60 * 60)
        hours, rem = divmod(rem, 60 * 60)
        minutes, seconds = divmod(rem, 60)
        return f"{days}d:{hours}h:{minutes}m:{seconds}s"

    def check_homestead(self):
        return (
            os.path.isfile(self.savefile_path)
            and os.path.getsize(self.savefile_path) > 0
        )

    def load_homestead(self):
        with open(self.savefile_path, "rb") as handle:
            homestead = pickle.load(handle)
        homestead.migrate_properties()
        self.process_guest_care(homestead)
        homestead.refresh_offline_ticks()
        homestead._sync_death_tracking()
        return homestead

    def save_homestead(self, homestead):
        now = int(time.time())
        for entity in homestead.all_entities():
            entity.last_time = now
        homestead._life_thread = None
        temp_path = self.savefile_path + ".temp"
        with open(temp_path, "wb") as handle:
            pickle.dump(homestead, handle, protocol=2)
        os.rename(temp_path, self.savefile_path)

    def write_json_exports(self, homestead):
        summary = {
            "owner": self.this_user,
            "generation": homestead.generation,
            "total_score": homestead.total_score(),
            "areas": {},
        }
        for key in ("aquarium", "bonsai", "farm", "livestock"):
            entity = homestead.entity_for_area(key)
            summary["areas"][key] = entity.to_json_dict()
            per_type = os.path.join(
                self.aquafarm_dir, f"{self.this_user}_{key}.json"
            )
            with open(per_type, "w") as handle:
                json.dump(entity.to_json_dict(), handle, indent=2)
        summary["tank_theme"] = homestead.tank_theme()["id"]
        summary["homestead_backdrop"] = homestead.backdrop()["id"]
        summary["age"] = self.homestead_age_formatted(homestead)
        summary["is_dead"] = all(e.dead for e in homestead.all_entities())
        showcase = homestead.aquarium
        summary["description"] = showcase.parse_description()
        summary["stage"] = showcase.stage_list[showcase.stage]
        summary["species"] = showcase.species_list[showcase.species]
        summary["score"] = homestead.total_score()
        summary_path = os.path.join(
            self.aquafarm_dir, f"{self.this_user}_homestead.json"
        )
        with open(summary_path, "w") as handle:
            json.dump(summary, handle, indent=2)
        visit_path = os.path.join(
            self.aquafarm_dir, f"{self.this_user}_homestead_data.json"
        )
        with open(visit_path, "w") as handle:
            json.dump(summary, handle, indent=2)
        full_path = os.path.join(
            self.aquafarm_dir, f"{self.this_user}_homestead_full.json"
        )
        with open(full_path, "w") as handle:
            json.dump(homestead.to_json_dict(), handle, indent=2)

    def init_database(self):
        sqlite_dir = os.path.join(self.game_dir, "sqlite")
        if not os.path.exists(sqlite_dir):
            os.makedirs(sqlite_dir)
            os.chmod(sqlite_dir, 0o777)
        conn = sqlite3.connect(self.board_db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS homestead_board (
                homestead_id TEXT PRIMARY KEY,
                owner TEXT,
                summary TEXT,
                total_score INTEGER,
                generation INTEGER,
                updated_at INTEGER
            )
            """
        )
        conn.commit()
        self.migrate_database(conn)
        conn.close()
        if os.path.exists(self.board_db_path) and os.stat(
            self.board_db_path
        ).st_uid == os.getuid():
            os.chmod(self.board_db_path, 0o666)
            open(self.board_json_path, "a").close()
            os.chmod(self.board_json_path, 0o666)
        self._ensure_visitors_file()

    def migrate_database(self, conn=None):
        close = False
        if conn is None:
            conn = sqlite3.connect(self.board_db_path)
            close = True
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS visitors (
                id INTEGER PRIMARY KEY,
                homestead_name TEXT,
                visitor_name TEXT,
                weekly_visits INTEGER
            )
            """
        )
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(homestead_board)")
        }
        if "age" not in columns:
            conn.execute("ALTER TABLE homestead_board ADD COLUMN age TEXT")
        if "is_dead" not in columns:
            conn.execute("ALTER TABLE homestead_board ADD COLUMN is_dead INTEGER")
        conn.commit()
        if close:
            conn.close()

    def process_guest_care(self, homestead):
        self._ensure_visitors_file()
        if not os.path.isfile(self.visitors_json_path):
            return
        with open(self.visitors_json_path, "r") as handle:
            try:
                payload = json.load(handle)
            except json.JSONDecodeError:
                payload = []
        if not payload:
            return
        guest_timestamps = []
        visitors_this_check = []
        now = int(time.time())
        for element in payload:
            user = element.get("user")
            ts = element.get("timestamp", 0)
            if user and user not in homestead.visitors:
                homestead.visitors.append(user)
            if user and user not in visitors_this_check:
                visitors_this_check.append(user)
            baseline = min(
                e.last_care(e.primary_care) for e in homestead.all_entities()
            )
            if ts <= now and ts >= baseline:
                guest_timestamps.append(ts)
        for entity in homestead.all_entities():
            guest_timestamps.append(entity.last_care(entity.primary_care))
        homestead.apply_guest_timestamps(guest_timestamps)
        try:
            self._update_visitor_db(homestead, visitors_this_check)
        except sqlite3.Error:
            pass
        with open(self.visitors_json_path, "w") as handle:
            json.dump([], handle)

    def _update_visitor_db(self, homestead, visitor_names):
        self.init_database()
        conn = sqlite3.connect(self.board_db_path)
        for name in visitor_names:
            row = conn.execute(
                "SELECT weekly_visits FROM visitors WHERE homestead_name = ? AND visitor_name = ?",
                (self.this_user, name),
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO visitors (homestead_name, visitor_name, weekly_visits) VALUES (?, ?, 1)",
                    (self.this_user, name),
                )
            else:
                conn.execute(
                    "UPDATE visitors SET weekly_visits = weekly_visits + 1 WHERE homestead_name = ? AND visitor_name = ?",
                    (self.this_user, name),
                )
        conn.commit()
        conn.close()

    def append_guest_care_for_host(self, host_user):
        host_dir = os.path.join(os.path.dirname(self.user_dir), host_user, ".aquafarm")
        visitor_path = os.path.join(host_dir, "visitors.json")
        if not os.path.isdir(host_dir):
            return False, "missing"
        if not os.path.isfile(visitor_path):
            try:
                with open(visitor_path, "w") as handle:
                    json.dump([], handle)
                os.chmod(visitor_path, 0o666)
            except OSError:
                return False, "missing"
        if not os.access(visitor_path, os.W_OK):
            return False, "locked"
        payload = []
        if os.path.getsize(visitor_path) > 0:
            with open(visitor_path, "r") as handle:
                try:
                    payload = json.load(handle)
                except json.JSONDecodeError:
                    payload = []
        payload.append(
            {"user": self.this_user, "timestamp": int(time.time()) - 1}
        )
        with open(visitor_path, "w") as handle:
            json.dump(payload, handle, indent=2)
        return True, "helped"

    def guest_homestead_json_path(self, host_user):
        host_dir = os.path.join(os.path.dirname(self.user_dir), host_user, ".aquafarm")
        for name in (
            f"{host_user}_homestead_data.json",
            f"{host_user}_homestead.json",
        ):
            path = os.path.join(host_dir, name)
            if os.path.isfile(path):
                return path
        return None

    def record_entity_harvest(self, homestead, area, entity):
        entry = {
            "area": area,
            "description": entity.parse_description(),
            "age": self.entity_age_formatted(entity),
            "score": int(entity.ticks),
            "generation": entity.generation,
            "recorded_at": int(time.time()),
        }
        harvest = {}
        if os.path.isfile(self.harvest_file_path):
            with open(self.harvest_file_path, "rb") as handle:
                harvest = pickle.load(handle)
        harvest[entity.entity_id] = entry
        temp_path = self.harvest_file_path + ".temp"
        with open(temp_path, "wb") as handle:
            pickle.dump(harvest, handle, protocol=2)
        os.rename(temp_path, self.harvest_file_path)
        with open(self.harvest_json_path, "w") as handle:
            json.dump(harvest, handle, indent=2)

    def list_board_owners(self):
        board = self.retrieve_board_from_db()
        return sorted({row["owner"] for row in board.values()})

    def weekly_visitors_text(self, homestead_owner):
        self.init_database()
        conn = sqlite3.connect(self.board_db_path)
        rows = conn.execute(
            "SELECT visitor_name, weekly_visits FROM visitors WHERE homestead_name = ? ORDER BY weekly_visits DESC",
            (homestead_owner,),
        ).fetchall()
        conn.close()
        if not rows:
            return "nobody :("
        return " ".join(f"{name}({count})" for name, count in rows)

    def update_board_db(self, homestead):
        self.init_database()
        summary = {
            "aquarium": homestead.aquarium.parse_description(),
            "bonsai": homestead.bonsai.parse_description(),
            "farm": homestead.farm.parse_description(),
            "livestock": homestead.livestock.parse_description(),
        }
        age = self.homestead_age_formatted(homestead)
        is_dead = int(all(e.dead for e in homestead.all_entities()))
        conn = sqlite3.connect(self.board_db_path)
        conn.execute(
            """
            INSERT OR REPLACE INTO homestead_board
            (homestead_id, owner, summary, total_score, generation, updated_at, age, is_dead)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                homestead.aquarium.entity_id,
                self.this_user,
                json.dumps(summary),
                homestead.total_score(),
                homestead.generation,
                int(time.time()),
                age,
                is_dead,
            ),
        )
        conn.execute(
            "UPDATE homestead_board SET is_dead = 1 WHERE owner = ? AND homestead_id <> ?",
            (self.this_user, homestead.aquarium.entity_id),
        )
        conn.commit()
        conn.close()

    def retrieve_board_from_db(self):
        self.init_database()
        conn = sqlite3.connect(self.board_db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM homestead_board ORDER BY owner"
        ).fetchall()
        conn.close()
        board = {}
        for row in rows:
            board[row["homestead_id"]] = {
                "owner": row["owner"],
                "summary": json.loads(row["summary"]),
                "total_score": row["total_score"],
                "generation": row["generation"],
                "age": row["age"] if "age" in row.keys() else "",
                "dead": bool(row["is_dead"]) if "is_dead" in row.keys() else False,
            }
        return board

    def update_board_json(self):
        board = self.retrieve_board_from_db()
        with open(self.board_json_path, "w") as handle:
            json.dump(board, handle, indent=2)
