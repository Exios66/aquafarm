#!/usr/bin/env python3
"""Aquafarm — kawaii homestead care (aquarium, bonsai, farm, livestock)."""

import os
import sys

# Allow running as script from repo root
GAME_DIR = os.path.dirname(os.path.realpath(__file__))
if GAME_DIR not in sys.path:
    sys.path.insert(0, GAME_DIR)

import menu_screen as ms
from data_manager import DataManager
from homestead import Homestead


def main():
    data = DataManager()
    data.init_database()
    if data.check_homestead():
        homestead = data.load_homestead()
    else:
        homestead = Homestead()
        data.write_json_exports(homestead)
    homestead.start_life(data)
    ms.main(homestead, data)
    data.save_homestead(homestead)
    data.write_json_exports(homestead)
    data.update_board_db(homestead)
    data.update_board_json()


if __name__ == "__main__":
    main()
