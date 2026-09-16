import logging

import torch as T

from sternhalma_agent.action_space import NUM_ACTIONS
from sternhalma_agent.alphazero import SternhalmaZero
from sternhalma_agent.replay_buffer import Example, ReplayBuffer
from sternhalma_agent.training import Trainer


def _buffer_with_examples(n: int) -> ReplayBuffer:
    buffer = ReplayBuffer(capacity=n)
    for i in range(n):
        buffer.push(
            Example(
                state=T.rand(3, 17, 17),
                policy=T.softmax(T.rand(NUM_ACTIONS), dim=0).numpy(),
                outcome=1.0 if i % 2 == 0 else -1.0,
            )
        )
    return buffer


def test_train_step_returns_a_finite_loss_and_updates_the_network():
    network = SternhalmaZero(board_size=17, num_actions=NUM_ACTIONS, num_res_blocks=1)
    trainer = Trainer(network, target_sync_interval=1_000_000, device="cpu")
    buffer = _buffer_with_examples(8)

    before = [p.clone() for p in trainer.network.parameters()]
    loss = trainer.train_step(buffer, batch_size=4)

    assert loss == loss  # not NaN
    assert loss >= 0.0
    after = list(trainer.network.parameters())
    assert any(not T.equal(b, a) for b, a in zip(before, after))


def test_train_step_increments_step_count():
    network = SternhalmaZero(board_size=17, num_actions=NUM_ACTIONS, num_res_blocks=1)
    trainer = Trainer(network, target_sync_interval=1_000_000, device="cpu")
    buffer = _buffer_with_examples(8)

    assert trainer.step_count == 0
    trainer.train_step(buffer, batch_size=4)
    assert trainer.step_count == 1
    trainer.train_step(buffer, batch_size=4)
    assert trainer.step_count == 2


def test_train_step_logs_the_loss_and_its_components(caplog):
    network = SternhalmaZero(board_size=17, num_actions=NUM_ACTIONS, num_res_blocks=1)
    trainer = Trainer(network, target_sync_interval=1_000_000, device="cpu")
    buffer = _buffer_with_examples(8)

    with caplog.at_level(logging.INFO):
        loss = trainer.train_step(buffer, batch_size=4)

    [record] = [r for r in caplog.records if "Training step" in r.message]
    assert f"loss={loss:.4f}" in record.message
    assert "policy=" in record.message
    assert "value=" in record.message


def _networks_match(trainer: Trainer) -> bool:
    eval_state = trainer.network.state_dict()
    target_state = trainer.target_network.state_dict()
    return all(T.equal(eval_state[k], target_state[k]) for k in eval_state)


def test_target_network_syncs_on_the_configured_schedule():
    network = SternhalmaZero(board_size=17, num_actions=NUM_ACTIONS, num_res_blocks=1)
    trainer = Trainer(network, target_sync_interval=3, device="cpu")
    buffer = _buffer_with_examples(8)

    # A fresh Trainer's target network is a deepcopy -- matches immediately.
    assert _networks_match(trainer)

    trainer.train_step(buffer, batch_size=4)  # step 1
    assert not _networks_match(trainer), "should have diverged before the sync interval"

    trainer.train_step(buffer, batch_size=4)  # step 2
    assert not _networks_match(trainer)

    trainer.train_step(buffer, batch_size=4)  # step 3 -- crosses the interval
    assert _networks_match(trainer), "should match immediately after the scheduled sync"

    trainer.train_step(buffer, batch_size=4)  # step 4
    assert not _networks_match(trainer), "should diverge again after the sync"
