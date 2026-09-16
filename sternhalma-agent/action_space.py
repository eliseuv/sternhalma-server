"""Fixed action-space encoding for SternhalmaZero's policy head.

The server hands the agent a variable-length list of legal (from, to) moves
each turn. SternhalmaZero's policy head instead scores a fixed-size action
space -- this module translates between them.

Encoding: a flat 121x121 (source cell, target cell) matrix, rather than a
(source cell, direction, hop-distance) grid. sternhalma-game's own
MovementIndices already compresses a chain-hop move down to just
[start, end], with no fixed direction/distance relationship between them --
the flat (source, target) matrix represents that uniformly, where a grid
keyed on direction/distance could not. See PROJECT_SPEC.md's R-18.
"""

import numpy as np
import sternhalma_rs
from numpy.typing import NDArray

# The 121 valid board cells, in a fixed canonical order -- derived from a
# fresh game's board mask (channel 2), never hardcoded, so this can never
# drift from sternhalma-game's own definition of the board.
_VALID_CELLS: list[tuple[int, int]] = [
    (int(i), int(j))
    for i, j in np.argwhere(np.asarray(sternhalma_rs.Game().board())[2] == 1.0)
]
_CELL_INDEX: dict[tuple[int, int], int] = {
    cell: idx for idx, cell in enumerate(_VALID_CELLS)
}

NUM_CELLS = len(_VALID_CELLS)
NUM_ACTIONS = NUM_CELLS * NUM_CELLS


def encode_action(from_cell: tuple[int, int], to_cell: tuple[int, int]) -> int:
    """Flat action index for a single (from, to) move."""
    return _CELL_INDEX[from_cell] * NUM_CELLS + _CELL_INDEX[to_cell]


def decode_action(action: int) -> tuple[tuple[int, int], tuple[int, int]]:
    """Inverse of encode_action: (from_cell, to_cell) for a flat action index."""
    from_idx, to_idx = divmod(action, NUM_CELLS)
    return _VALID_CELLS[from_idx], _VALID_CELLS[to_idx]


def legal_action_indices(movements: NDArray[np.int_]) -> NDArray[np.int64]:
    """Flat action indices for the server's current-turn move list.

    Args:
        movements: Shape (N, 2, 2) array of [[from_i, from_j], [to_i, to_j]]
            moves, e.g. ServerMessageTurn.movements.

    Returns:
        Shape (N,) array of flat action indices, in the same order as
        `movements`.
    """
    return np.array(
        [
            encode_action((int(m[0][0]), int(m[0][1])), (int(m[1][0]), int(m[1][1])))
            for m in movements
        ],
        dtype=np.int64,
    )


def mask_and_renormalize(
    policy: NDArray[np.float32], movements: NDArray[np.int_]
) -> NDArray[np.float32]:
    """Restrict a full-action-space policy to the legal moves, renormalized.

    Args:
        policy: Shape (NUM_ACTIONS,) probabilities (or non-negative scores)
            over the full fixed action space, e.g. softmax(policy logits).
        movements: Shape (N, 2, 2) legal moves for the current turn, same
            shape as ServerMessageTurn.movements.

    Returns:
        Shape (N,) probability distribution over `movements`, in the same
        order, summing to 1.
    """
    indices = legal_action_indices(movements)
    legal = policy[indices].astype(np.float32)
    total = legal.sum()
    if total <= 0:
        # Degenerate case (e.g. an untrained network's masked scores are all
        # zero): fall back to uniform rather than dividing by zero.
        return np.full(len(movements), 1.0 / len(movements), dtype=np.float32)
    return legal / total
