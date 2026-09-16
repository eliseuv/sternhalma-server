"""Self-play game generation.

Plays a complete game of SternhalmaZero against itself via MCTS, recording
each turn as a training example (R-20): the board tensor, the MCTS
visit-count policy target, and -- once the game ends -- the eventual
outcome, backfilled from each position's own current-mover perspective.
"""

import numpy as np
import sternhalma_rs
import torch as T
from numpy.typing import NDArray

from alphazero import SternhalmaZero, from_state
from mcts import DEFAULT_HEURISTIC_WEIGHT, search_with_policy
from replay_buffer import Example

# Safety cap: sternhalma_rs.Game has no max-turns concept of its own (that's
# the server's job) -- self-play needs its own bound so a pathological game
# can't run forever.
#
# Untuned: under weak/near-random play (an untrained network, low
# num_simulations), verification runs of 150-500 turns never reached a
# natural finish at all -- Sternhalma games apparently take many more turns
# than that to complete without strong play. 300 is a placeholder, not a
# calibrated value; real training will likely need this raised, or discard
# most self-play games. Concretely motivates R-27..R-29 (a smaller board
# would cut turns-to-completion substantially).
DEFAULT_MAX_TURNS = 300


def _backfill_outcomes(
    states: list[T.Tensor], policies: list[NDArray[np.float32]]
) -> list[Example]:
    """Labels each recorded (state, policy) with the eventual game outcome.

    sternhalma-game only ever finishes via the mover completing their own
    goal (see mcts.py's terminal-value comment), so the mover of the LAST
    recorded turn won: outcome +1 for that state, from their own
    perspective. Perspective alternates every turn, so outcome alternates
    sign walking backward from there.
    """
    examples: list[Example] = []
    outcome = 1.0
    for state, policy in zip(reversed(states), reversed(policies)):
        examples.append(Example(state=state, policy=policy, outcome=outcome))
        outcome = -outcome
    examples.reverse()
    return examples


def play_self_play_game(
    network: SternhalmaZero,
    num_simulations: int,
    device: str = "cuda",
    heuristic_weight: float = DEFAULT_HEURISTIC_WEIGHT,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> list[Example]:
    """Plays one self-play game, returning a training example per turn.

    A game that hits `max_turns` without finishing contributes no examples
    -- there's no winner to backfill an outcome from.
    """
    game = sternhalma_rs.Game()
    states: list[T.Tensor] = []
    policies: list[NDArray[np.float32]] = []

    turns = 0
    while game.player() != 0 and turns < max_turns:
        states.append(from_state(game, device=device).squeeze(0))
        move, policy = search_with_policy(
            game,
            network,
            num_simulations,
            device=device,
            heuristic_weight=heuristic_weight,
        )
        policies.append(policy)
        game.apply_movement_unchecked(*move)
        turns += 1

    if game.player() != 0:
        return []

    return _backfill_outcomes(states, policies)
