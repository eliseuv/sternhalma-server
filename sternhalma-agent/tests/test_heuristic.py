import numpy as np
import sternhalma_rs

from heuristic import potential, potential_after_move
from mcts import _bias_priors_with_potential  # pyright: ignore[reportPrivateUsage]


def test_potential_flips_goal_region_with_the_current_mover():
    game = sternhalma_rs.Game()
    from_cell, to_cell = game.available_moves()[0]

    # Before Player 2 has made any move, its potential (now the current
    # mover, after Player 1's first move) depends only on its own
    # untouched starting pieces -- the same value regardless of which
    # opening move Player 1 chose.
    game_a = sternhalma_rs.Game()
    game_a.apply_movement_unchecked(from_cell, to_cell)
    other_from, other_to = [m for m in game.available_moves() if m != (from_cell, to_cell)][0]
    game_b = sternhalma_rs.Game()
    game_b.apply_movement_unchecked(other_from, other_to)

    assert game_a.player() == -1
    assert potential(game_a) == potential(game_b)


def test_potential_after_move_matches_the_incremental_formula():
    game = sternhalma_rs.Game()
    base = potential(game)
    for from_cell, to_cell in game.available_moves():
        # Player 1's piece moves off its own starting cell (distance 0 to
        # its own start is irrelevant here) toward Player 2's start (its
        # goal) -- recompute the expected delta directly against the goal
        # region a fresh game's own pieces occupy on the opposite side.
        goal = [
            (int(i), int(j))
            for i, j in np.argwhere(np.asarray(game.board())[1] == 1.0)
        ]
        expected = base + min(
            max(abs(from_cell[0] - g[0]), abs(from_cell[1] - g[1]), abs((from_cell[0] + from_cell[1]) - (g[0] + g[1])))
            for g in goal
        ) - min(
            max(abs(to_cell[0] - g[0]), abs(to_cell[1] - g[1]), abs((to_cell[0] + to_cell[1]) - (g[0] + g[1])))
            for g in goal
        )
        assert potential_after_move(game, from_cell, to_cell) == expected


def test_potential_after_move_prefers_moves_toward_goal():
    game = sternhalma_rs.Game()
    base = potential(game)
    gains = [
        potential_after_move(game, from_cell, to_cell) - base
        for from_cell, to_cell in game.available_moves()
    ]
    # At the opening position every legal move is a single step off the
    # starting triangle, strictly toward the goal side of the board -- none
    # should ever make the position look worse.
    assert all(gain >= 0 for gain in gains)
    assert any(gain > 0 for gain in gains)


def test_bias_priors_with_potential_shifts_mass_toward_better_moves():
    game = sternhalma_rs.Game()
    movements = np.array(game.available_moves())

    uniform = np.full(len(movements), 1.0 / len(movements), dtype=np.float32)
    biased = _bias_priors_with_potential(uniform, movements, game, weight=1.0)

    assert np.isclose(biased.sum(), 1.0)

    base = potential(game)
    gains = np.array(
        [
            potential_after_move(game, tuple(m[0]), tuple(m[1])) - base
            for m in movements
        ]
    )
    best = int(np.argmax(gains))
    worst = int(np.argmin(gains))
    assert gains[best] > gains[worst]
    # The move with the largest potential gain must end up with more prior
    # mass than the move with the smallest, and both must have moved away
    # from the uniform baseline in the expected direction.
    assert biased[best] > uniform[best]
    assert biased[worst] <= uniform[worst]
    assert biased[best] > biased[worst]
