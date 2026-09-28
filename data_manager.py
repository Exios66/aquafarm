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

    def check_homestead(self):
        return (
            os.path.isfile(self.savefile_path)
            and os.path.getsize(self.savefile_path) > 0
        )

    def load_homestead(self):
        with open(self.savefile_path, "rb") as handle:
            homestead = pickle.load(handle)
        homestead.migrate_properties()
        homestead.refresh_offline_ticks()
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
        summary_path = os.path.join(
            self.aquafarm_dir, f"{self.this_user}_homestead.json"
        )
        with open(summary_path, "w") as handle:
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
        conn.close()
        if os.path.exists(self.board_db_path) and os.stat(
            self.board_db_path
        ).st_uid == os.getuid():
            os.chmod(self.board_db_path, 0o666)
            open(self.board_json_path, "a").close()
            os.chmod(self.board_json_path, 0o666)

    def update_board_db(self, homestead):
        self.init_database()
        summary = {
            "aquarium": homestead.aquarium.parse_description(),
            "bonsai": homestead.bonsai.parse_description(),
            "farm": homestead.farm.parse_description(),
            "livestock": homestead.livestock.parse_description(),
        }
        conn = sqlite3.connect(self.board_db_path)
        conn.execute(
            """
            INSERT OR REPLACE INTO homestead_board
            (homestead_id, owner, summary, total_score, generation, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                homestead.aquarium.entity_id,
                self.this_user,
                json.dumps(summary),
                homestead.total_score(),
                homestead.generation,
                int(time.time()),
            ),
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
            }
        return board

    def update_board_json(self):
        board = self.retrieve_board_from_db()
        with open(self.board_json_path, "w") as handle:
            json.dump(board, handle, indent=2)
