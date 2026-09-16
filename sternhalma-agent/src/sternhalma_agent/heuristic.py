"""A potential function biasing MCTS search toward pieces closer to goal.

Classic Chinese-Checkers heuristic: the closer a player's pieces sit to
their goal region, the better the position for them. game.scores() (goal
cells occupied) only changes when a piece enters/leaves the goal, giving no
signal for most of a game; this gives a smooth signal on every move.

potential() is deliberately symmetric -- "how good for whoever's turn it
currently is" -- the same convention SternhalmaZero's own value head and
MCTS's backup use (see PROJECT_SPEC.md's R-1), not fixed to a single
identity like from_state()'s canonical "me" is. Biasing a simulated
opponent-turn node's priors toward ITS OWN goal is what makes self-play
realistic; biasing it toward this agent's goal instead would make the
simulated opponent play into this agent's hands.
"""

import numpy as np
import sternhalma_rs

# The two fixed starting regions, in absolute physical terms -- derived at
# runtime from a fresh game's board (before any move, when channel 0 is
# still literally Player 1), never hardcoded. A player's goal is always the
# region the OTHER side started in (mirrors sternhalma-game's own
# board::goal_indices).
_fresh_board = np.asarray(sternhalma_rs.Game().board())
_PLAYER1_START: list[tuple[int, int]] = [
    (int(i), int(j)) for i, j in np.argwhere(_fresh_board[0] == 1.0)
]
_PLAYER2_START: list[tuple[int, int]] = [
    (int(i), int(j)) for i, j in np.argwhere(_fresh_board[1] == 1.0)
]


def _hex_distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    """Mirrors sternhalma-game's own board::hex_distance."""
    dq = abs(a[0] - b[0])
    dr = abs(a[1] - b[1])
    return max(dq, dr, abs((a[0] + a[1]) - (b[0] + b[1])))


def _nearest_distance(cell: tuple[int, int], region: list[tuple[int, int]]) -> int:
    return min(_hex_distance(cell, c) for c in region)


def _goal_region_for_current_mover(game: sternhalma_rs.Game) -> list[tuple[int, int]]:
    # sternhalma-game always starts with Player 1 to move and alternates
    # every move, so the move count's parity tells us which absolute side
    # is currently to move, and therefore which fixed region is their goal.
    return _PLAYER2_START if len(game.history()) % 2 == 0 else _PLAYER1_START


def potential(game: sternhalma_rs.Game) -> float:
    """Higher is better for whoever's turn it currently is.

    Negative sum of the current mover's pieces' hex-distance to their own
    goal region -- board()'s channel 0 is always "whoever's turn it is",
    which is exactly the piece set this needs.
    """
    board = np.asarray(game.board())
    pieces = np.argwhere(board[0] == 1.0)
    goal = _goal_region_for_current_mover(game)
    return -float(sum(_nearest_distance((int(i), int(j)), goal) for i, j in pieces))


def potential_after_move(
    game: sternhalma_rs.Game, from_cell: tuple[int, int], to_cell: tuple[int, int]
) -> float:
    """potential(), for the current mover, after hypothetically playing
    from_cell -> to_cell.

    Computed incrementally (only one piece's term changes, and it's still
    evaluated toward the SAME mover's goal) rather than by cloning and
    replaying -- cheap, since this runs once per candidate move at every
    MCTS expansion.
    """
    goal = _goal_region_for_current_mover(game)
    return (
        potential(game)
        + _nearest_distance(from_cell, goal)
        - _nearest_distance(to_cell, goal)
    )
