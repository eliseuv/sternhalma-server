from sternhalma_agent import evaluation
from sternhalma_agent.action_space import NUM_ACTIONS
from sternhalma_agent.alphazero import SternhalmaZero
from sternhalma_agent.evaluation import (  # pyright: ignore[reportPrivateUsage]
    _should_replace_best,
    evaluate_checkpoint,
    play_evaluation_game,
)


def test_should_replace_best_at_or_above_threshold():
    # 3 wins, 2 losses out of 5 decisive games -- 0.6 win rate.
    results = [1, 1, 1, -1, -1]
    assert _should_replace_best(results, win_rate_threshold=0.55) is True
    assert _should_replace_best(results, win_rate_threshold=0.6) is True
    assert _should_replace_best(results, win_rate_threshold=0.61) is False


def test_should_replace_best_ignores_non_decisive_games():
    # 2 wins, 1 loss among decisive games; two no-winner games don't count
    # toward the rate either way.
    results = [1, 1, -1, 0, 0]
    assert _should_replace_best(results, win_rate_threshold=0.6) is True
    assert _should_replace_best(results, win_rate_threshold=0.7) is False


def test_should_replace_best_with_no_decisive_games_is_false():
    assert _should_replace_best([0, 0, 0], win_rate_threshold=0.55) is False


def test_play_evaluation_game_returns_no_winner_when_max_turns_is_hit():
    # Same lesson as R-20's self-play tests: real games under weak/untrained
    # play take far more than a handful of turns to finish naturally -- a
    # tiny max_turns deterministically exercises the early-exit path fast.
    network_a = SternhalmaZero(board_size=17, num_actions=NUM_ACTIONS, num_res_blocks=1)
    network_b = SternhalmaZero(board_size=17, num_actions=NUM_ACTIONS, num_res_blocks=1)

    result = play_evaluation_game(
        network_a, network_b, num_simulations=1, device="cpu", max_turns=3
    )

    assert result == 0


def test_evaluate_checkpoint_runs_the_full_orchestration(monkeypatch):
    # Wiring smoke test: alternating first-mover across games and the
    # result-flip for candidate-as-Player-2 games actually work together,
    # not just _should_replace_best in isolation. A small max_turns
    # override keeps it fast (see the max_turns test above).
    real_play_evaluation_game = evaluation.play_evaluation_game
    monkeypatch.setattr(
        evaluation,
        "play_evaluation_game",
        lambda network_a, network_b, num_simulations, device, heuristic_weight: (
            real_play_evaluation_game(
                network_a,
                network_b,
                num_simulations,
                device=device,
                heuristic_weight=heuristic_weight,
                max_turns=3,
            )
        ),
    )

    candidate = SternhalmaZero(board_size=17, num_actions=NUM_ACTIONS, num_res_blocks=1)
    best = SternhalmaZero(board_size=17, num_actions=NUM_ACTIONS, num_res_blocks=1)

    # No games will be decisive within 3 turns, so nothing crosses the
    # win-rate threshold -- this only needs to run without error and
    # return the expected (False) gating decision.
    replaced = evaluate_checkpoint(
        candidate, best, num_games=2, num_simulations=1, device="cpu"
    )
    assert replaced is False
