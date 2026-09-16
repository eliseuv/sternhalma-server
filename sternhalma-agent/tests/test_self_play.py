import torch as T

from action_space import NUM_ACTIONS
from alphazero import SternhalmaZero
from self_play import _backfill_outcomes, play_self_play_game  # pyright: ignore[reportPrivateUsage]


def test_backfill_outcomes_alternates_sign_from_the_last_turn():
    # Three recorded turns; the mover at the LAST one won.
    states = [T.zeros(3, 17, 17) for _ in range(3)]
    policies = [T.zeros(NUM_ACTIONS).numpy() for _ in range(3)]

    examples = _backfill_outcomes(states, policies)

    assert len(examples) == 3
    assert [e.outcome for e in examples] == [1.0, -1.0, 1.0]


def test_backfill_outcomes_matches_states_and_policies_by_position():
    states = [T.zeros(3, 17, 17) + i for i in range(4)]
    policies = [T.zeros(NUM_ACTIONS).numpy() for _ in range(4)]

    examples = _backfill_outcomes(states, policies)

    for i, example in enumerate(examples):
        assert T.equal(example.state, states[i])


def test_play_self_play_game_returns_nothing_when_max_turns_is_hit():
    # A real Sternhalma game between two weak/untrained players takes far
    # more than a handful of turns to finish naturally (verified manually:
    # 150-500 turns wasn't enough) -- max_turns=3 deterministically exercises
    # the "no winner yet" early-exit path fast, without waiting for a real
    # game to actually finish.
    network = SternhalmaZero(board_size=17, num_actions=NUM_ACTIONS, num_res_blocks=1)
    network.eval()

    examples = play_self_play_game(
        network, num_simulations=1, device="cpu", max_turns=3
    )

    assert examples == []
