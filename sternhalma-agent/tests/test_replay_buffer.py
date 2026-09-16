import pytest
import torch as T

from action_space import NUM_ACTIONS
from replay_buffer import Example, ReplayBuffer


def _example(i: int) -> Example:
    # A distinct, checkable example per index -- state/policy filled with i
    # so retrieval can be verified exactly, not just by shape.
    return Example(
        state=T.full((3, 17, 17), float(i)),
        policy=T.full((NUM_ACTIONS,), float(i)).numpy(),
        outcome=float(i),
    )


def test_len_tracks_pushes_up_to_capacity():
    buffer = ReplayBuffer(capacity=5)
    assert len(buffer) == 0

    for i in range(3):
        buffer.push(_example(i))
    assert len(buffer) == 3

    for i in range(3, 10):
        buffer.push(_example(i))
    assert len(buffer) == 5


def test_sample_returns_exactly_what_was_pushed_uncorrupted():
    buffer = ReplayBuffer(capacity=10)
    pushed = [_example(i) for i in range(4)]
    for example in pushed:
        buffer.push(example)

    sampled = buffer.sample(4)  # the whole buffer, so order aside, exact set

    assert len(sampled) == 4
    for example in sampled:
        assert example.state.shape == (3, 17, 17)
        assert example.policy.shape == (NUM_ACTIONS,)
        # Every field on a sampled example must belong to the SAME original
        # pushed example (i == i == i), not a mix-and-match of fields from
        # different pushes.
        i = int(example.outcome)
        assert T.equal(example.state, pushed[i].state)
        assert (example.policy == pushed[i].policy).all()


def test_capacity_evicts_oldest_first():
    buffer = ReplayBuffer(capacity=3)
    for i in range(5):
        buffer.push(_example(i))

    remaining_outcomes = sorted(e.outcome for e in buffer.sample(3))
    assert remaining_outcomes == [2.0, 3.0, 4.0]  # 0 and 1 evicted


def test_sample_respects_batch_size():
    buffer = ReplayBuffer(capacity=10)
    for i in range(10):
        buffer.push(_example(i))

    for batch_size in (1, 3, 10):
        assert len(buffer.sample(batch_size)) == batch_size


def test_sample_is_without_replacement():
    buffer = ReplayBuffer(capacity=10)
    for i in range(10):
        buffer.push(_example(i))

    sampled = buffer.sample(10)
    assert len({id(e) for e in sampled}) == 10


def test_sample_more_than_available_raises():
    buffer = ReplayBuffer(capacity=10)
    for i in range(3):
        buffer.push(_example(i))

    with pytest.raises(ValueError):
        buffer.sample(4)
