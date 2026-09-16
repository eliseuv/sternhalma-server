"""Checkpoint-gating: play evaluation games between two checkpoints and
decide whether the new one should replace the current best (G-6).
"""

import sternhalma_rs

from alphazero import SternhalmaZero
from mcts import DEFAULT_HEURISTIC_WEIGHT, search
from self_play import DEFAULT_MAX_TURNS

DEFAULT_WIN_RATE_THRESHOLD = 0.55


def play_evaluation_game(
    network_a: SternhalmaZero,
    network_b: SternhalmaZero,
    num_simulations: int,
    device: str = "cuda",
    heuristic_weight: float = DEFAULT_HEURISTIC_WEIGHT,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> int:
    """Plays one game, `network_a` as Player 1 (moves first), `network_b`
    as Player 2.

    Returns 1 if `network_a` won, -1 if `network_b` won, 0 if the game hit
    `max_turns` without a winner.
    """
    game = sternhalma_rs.Game()
    turns = 0
    while game.player() != 0 and turns < max_turns:
        network = network_a if game.player() == 1 else network_b
        move = search(
            game,
            network,
            num_simulations,
            device=device,
            heuristic_weight=heuristic_weight,
        )
        game.apply_movement_unchecked(*move)
        turns += 1

    if game.player() != 0:
        return 0

    return 1 if game.winner() == 1 else -1


def _should_replace_best(results: list[int], win_rate_threshold: float) -> bool:
    """Decides whether `candidate` should replace `best`, given a list of
    per-game results from the candidate's own perspective (1 win, -1 loss,
    0 no winner within max_turns).

    Games with no winner don't count toward the rate either way -- there's
    nothing decisive to gate on.
    """
    decisive = [r for r in results if r != 0]
    if not decisive:
        return False
    win_rate = sum(1 for r in decisive if r == 1) / len(decisive)
    return win_rate >= win_rate_threshold


def evaluate_checkpoint(
    candidate: SternhalmaZero,
    best: SternhalmaZero,
    num_games: int,
    num_simulations: int,
    device: str = "cuda",
    heuristic_weight: float = DEFAULT_HEURISTIC_WEIGHT,
    win_rate_threshold: float = DEFAULT_WIN_RATE_THRESHOLD,
) -> bool:
    """Plays `num_games` evaluation games between `candidate` and `best`,
    alternating which one moves first each game to cancel out first-move
    advantage, and returns whether `candidate` should replace `best` as the
    network used for subsequent self-play generation.
    """
    results: list[int] = []
    for i in range(num_games):
        if i % 2 == 0:
            result = play_evaluation_game(
                candidate, best, num_simulations, device, heuristic_weight
            )
        else:
            # candidate played as network_b (Player 2) this game -- flip
            # the result back to the candidate's own perspective.
            result = -play_evaluation_game(
                best, candidate, num_simulations, device, heuristic_weight
            )
        results.append(result)

    return _should_replace_best(results, win_rate_threshold)
