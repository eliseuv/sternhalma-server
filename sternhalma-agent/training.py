"""The AlphaZero training step: policy + value loss against replay buffer
samples, with a target network kept in sync on a configured interval.
"""

import copy

import numpy as np
import torch as T
import torch.nn.functional as F

from alphazero import SternhalmaZero
from replay_buffer import ReplayBuffer


class Trainer:
    """Owns the evaluation network, its optimizer, and a target network
    kept in sync with it on a configured interval.
    """

    def __init__(
        self,
        network: SternhalmaZero,
        target_sync_interval: int,
        lr: float = 1e-3,
        device: str = "cuda",
    ) -> None:
        self.device = device
        self.network = network.to(device)
        self.optimizer = T.optim.Adam(self.network.parameters(), lr=lr)
        self.target_sync_interval = target_sync_interval

        self.target_network = copy.deepcopy(network).to(device)
        self.target_network.eval()

        self.step_count = 0

    def train_step(self, buffer: ReplayBuffer, batch_size: int) -> float:
        """Samples a batch, computes the AlphaZero loss, and takes one
        optimizer step against the evaluation network. Syncs the target
        network from it every `target_sync_interval` steps.

        Returns the scalar loss value.
        """
        batch = buffer.sample(batch_size)
        states = T.stack([example.state for example in batch]).to(self.device)
        policy_targets = T.from_numpy(np.stack([example.policy for example in batch])).to(
            self.device
        )
        outcome_targets = T.tensor(
            [example.outcome for example in batch], dtype=T.float32
        ).to(self.device)

        self.network.train()
        policy_logits, values = self.network(states)

        # Soft-label cross-entropy against the MCTS visit-count policy
        # target, plus MSE against the eventual game outcome -- the
        # standard AlphaZero loss.
        policy_loss = (
            -(policy_targets * F.log_softmax(policy_logits, dim=1)).sum(dim=1).mean()
        )
        value_loss = F.mse_loss(values.squeeze(-1), outcome_targets)
        loss = policy_loss + value_loss

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        self.step_count += 1
        if self.step_count % self.target_sync_interval == 0:
            self.sync_target_network()

        return float(loss.item())

    def sync_target_network(self) -> None:
        """Copies the evaluation network's weights into the target network."""
        self.target_network.load_state_dict(self.network.state_dict())
