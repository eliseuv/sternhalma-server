import torch as T

from action_space import NUM_ACTIONS
from alphazero import SternhalmaZero
from replay_buffer import Example, ReplayBuffer
from training import Trainer


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
