from minigames.base import MiniGame
from minigames.crows import CrowGame
from minigames.eggcatch import EggCatchGame
from minigames.fishing import FishingGame
from minigames.pruning import PruningGame

GAMES = {
    FishingGame.game_id: FishingGame,
    PruningGame.game_id: PruningGame,
    CrowGame.game_id: CrowGame,
    EggCatchGame.game_id: EggCatchGame,
}

__all__ = ["MiniGame", "FishingGame", "PruningGame", "CrowGame", "EggCatchGame", "GAMES"]
