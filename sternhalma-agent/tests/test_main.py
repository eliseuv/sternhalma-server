import asyncio
from pathlib import Path

import main


def test_train_runs_the_loop_and_saves_checkpoints(tmp_path: Path, monkeypatch):
    # A wiring smoke test, not a real training run: tiny constants so it
    # completes quickly, and a small max_turns override (real self-play
    # games under weak/untrained play can take far longer than that to
    # finish naturally -- see self_play.DEFAULT_MAX_TURNS's own comment).
    monkeypatch.setattr(main, "GAMES_PER_ITERATION", 1)
    monkeypatch.setattr(main, "NUM_SIMULATIONS", 1)
    monkeypatch.setattr(main, "BATCH_SIZE", 2)
    monkeypatch.setattr(main, "TRAIN_STEPS_PER_ITERATION", 1)
    monkeypatch.setattr(main, "TARGET_SYNC_INTERVAL", 1)
    monkeypatch.setattr(main, "CHECKPOINT_INTERVAL", 1)

    real_play_self_play_game = main.play_self_play_game
    monkeypatch.setattr(
        main,
        "play_self_play_game",
        lambda network, num_simulations, device: real_play_self_play_game(
            network, num_simulations, device=device, max_turns=5
        ),
    )

    checkpoint_dir = tmp_path / "checkpoints"
    asyncio.run(
        main.train(num_iterations=1, checkpoint_dir=checkpoint_dir, device="cpu")
    )

    checkpoints = list(checkpoint_dir.glob("*.pt"))
    assert len(checkpoints) == 1
