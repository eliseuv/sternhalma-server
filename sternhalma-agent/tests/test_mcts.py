import numpy as np
import sternhalma_rs

from action_space import NUM_ACTIONS
from alphazero import SternhalmaZero
from mcts import clone_game, search


def test_clone_game_reproduces_history_without_sharing_state():
    game = sternhalma_rs.Game()
    from_cell, to_cell = game.available_moves()[0]
    game.apply_movement_unchecked(from_cell, to_cell)

    clone = clone_game(game)
    assert clone.history() == game.history()
    assert np.array_equal(np.asarray(clone.board()), np.asarray(game.board()))

    # Mutating the clone must not affect the original.
    clone.apply_movement_unchecked(*clone.available_moves()[0])
    assert clone.history() != game.history()


def test_search_returns_a_legal_move():
    game = sternhalma_rs.Game()
    network = SternhalmaZero(board_size=17, num_actions=NUM_ACTIONS, num_res_blocks=1)
    network.eval()

    move = search(game, network, num_simulations=4, device="cpu")

    legal = {(tuple(m[0]), tuple(m[1])) for m in game.available_moves()}
    assert move in legal
