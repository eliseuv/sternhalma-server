import numpy as np
import sternhalma_rs

from sternhalma_agent.action_space import NUM_ACTIONS, decode_action
from sternhalma_agent.alphazero import SternhalmaZero
from sternhalma_agent.mcts import clone_game, search, search_with_policy


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


def test_search_with_policy_returns_a_normalized_policy_over_legal_moves():
    game = sternhalma_rs.Game()
    network = SternhalmaZero(board_size=17, num_actions=NUM_ACTIONS, num_res_blocks=1)
    network.eval()

    move, policy = search_with_policy(game, network, num_simulations=4, device="cpu")

    assert policy.shape == (NUM_ACTIONS,)
    assert np.isclose(policy.sum(), 1.0)
    assert np.all(policy >= 0.0)

    legal = {(tuple(m[0]), tuple(m[1])) for m in game.available_moves()}
    assert move in legal

    # Every action with nonzero probability must be one of this turn's
    # actual legal moves -- nothing outside the root's expanded children.
    nonzero_moves = {decode_action(int(a)) for a in np.nonzero(policy)[0]}
    assert nonzero_moves <= legal

    # The returned move is the one search() itself would pick (highest
    # visit count), which must also be the highest-probability move here.
    assert move == decode_action(int(np.argmax(policy)))
