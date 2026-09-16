import numpy as np
import sternhalma_rs

from alphazero import from_state


def test_from_state_matches_raw_board_on_player_ones_turn():
    game = sternhalma_rs.Game()
    assert game.player() == 1

    tensor = from_state(game, device="cpu").squeeze(0).numpy()
    raw = np.asarray(game.board())

    # No swap needed: it's already locally Player 1's turn.
    np.testing.assert_array_equal(tensor, raw)


def test_from_state_swaps_channels_on_player_twos_turn():
    game = sternhalma_rs.Game()
    from_idx, to_idx = game.available_moves()[0]
    game.apply_movement(from_idx, to_idx)
    assert game.player() == -1

    tensor = from_state(game, device="cpu").squeeze(0).numpy()
    raw = np.asarray(game.board())

    # sternhalma_rs.Game.board()'s channel 0 is now Player 2 (raw's "current
    # player"), channel 1 is Player 1 -- from_state must swap them back so
    # channel 0 is always "me" (Player 1), regardless of whose turn it is.
    np.testing.assert_array_equal(tensor[0], raw[1])
    np.testing.assert_array_equal(tensor[1], raw[0])
    np.testing.assert_array_equal(tensor[2], raw[2])
