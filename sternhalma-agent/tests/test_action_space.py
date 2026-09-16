import numpy as np
import sternhalma_rs

from action_space import (
    NUM_ACTIONS,
    NUM_CELLS,
    decode_action,
    encode_action,
    legal_action_indices,
    mask_and_renormalize,
)


def test_num_cells_matches_the_board():
    assert NUM_CELLS == 121
    assert NUM_ACTIONS == 121 * 121


def test_encode_decode_are_inverses():
    game = sternhalma_rs.Game()
    for from_cell, to_cell in game.available_moves():
        action = encode_action(from_cell, to_cell)
        assert 0 <= action < NUM_ACTIONS
        assert decode_action(action) == (from_cell, to_cell)


def test_legal_action_indices_matches_available_moves():
    game = sternhalma_rs.Game()
    movements = np.array(game.available_moves())

    indices = legal_action_indices(movements)
    assert len(indices) == len(movements)
    assert len(set(indices.tolist())) == len(movements)  # all distinct

    decoded = [decode_action(int(a)) for a in indices]
    expected = [
        ((int(m[0][0]), int(m[0][1])), (int(m[1][0]), int(m[1][1]))) for m in movements
    ]
    assert decoded == expected


def test_mask_and_renormalize_distributes_over_legal_moves_only():
    game = sternhalma_rs.Game()
    movements = np.array(game.available_moves())

    # A uniform policy over the whole action space: after masking to just
    # the legal moves and renormalizing, should become uniform over them.
    policy = np.ones(NUM_ACTIONS, dtype=np.float32)
    probs = mask_and_renormalize(policy, movements)

    assert probs.shape == (len(movements),)
    assert np.isclose(probs.sum(), 1.0)
    assert np.allclose(probs, 1.0 / len(movements))


def test_mask_and_renormalize_falls_back_to_uniform_when_all_zero():
    game = sternhalma_rs.Game()
    movements = np.array(game.available_moves())

    policy = np.zeros(NUM_ACTIONS, dtype=np.float32)
    probs = mask_and_renormalize(policy, movements)

    assert np.isclose(probs.sum(), 1.0)
    assert np.allclose(probs, 1.0 / len(movements))
