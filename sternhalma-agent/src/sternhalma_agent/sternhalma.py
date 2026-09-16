"""Player identity and score types shared across the agent's protocol layer.

Board state and move logic used to be reimplemented here too; that's now
sternhalma_rs (the sternhalma-game Rust engine's Python bindings) instead,
per D-2.
"""

from enum import IntEnum
from typing import override


class Player(IntEnum):
    """
    Represents the two players in the game.

    Player 1 is the starting player (Blue, 🔵).
    Player 2 is the second player (Red, 🔴).
    """

    Player1 = 1
    Player2 = 2

    @override
    def __str__(self) -> str:
        match self:
            case Player.Player1:
                return "🔵"
            case Player.Player2:
                return "🔴"


# Scores of each player
type Scores = tuple[int, int]
