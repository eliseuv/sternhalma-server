from typing import override
import numpy as np
import sternhalma_rs
import torch as T
import torch.nn as nn
import torch.nn.functional as F


def from_state(game: sternhalma_rs.Game, device: str = "cuda") -> T.Tensor:
    """
    Converts the board state to a canonical tensor representation for neural network input.

    The input `board` is always from the perspective of the current player (Player 1).
    This means the current player's pieces are at the bottom (Player 1's starting position)
    and the opponent's pieces are at the top (Player 2's starting position).

    - Channel 0: Binary mask for "friendly" pieces (always Player 1).
    - Channel 1: Binary mask for "enemy" pieces (always Player 2).
    - Channel 2: Binary mask for all valid board positions (board geometry).

    Args:
        game: The current game state (in relative coordinates, i.e. this
            agent is always Player 1 -- see the client protocol).
        device: The device (e.g., "cpu", "cuda") where the tensor will be allocated.

    Returns:
        A tensor of shape (1, 3, 17, 17) ready for the network.
    """
    # sternhalma_rs.Game.board()'s channels 0/1 are relative to whichever
    # player's turn it currently is, not fixed to Player 1 -- swap them back
    # to a turn-independent "channel 0 == me" whenever it's locally Player
    # 2's turn, to match this function's contract.
    tensor = np.asarray(game.board())
    if game.player() == -1:
        tensor = tensor[[1, 0, 2]]

    # Convert to torch tensor, add batch dimension (N=1), and move to device
    return T.from_numpy(tensor.copy()).unsqueeze(0).to(device)


class ResBlock(nn.Module):
    """
    Standard Residual Block implementation.
    Consists of two 3x3 convolutional layers with batch normalization and a skip connection.
    """

    def __init__(self, num_channels: int) -> None:
        """
        Initializes the ResBlock with the specified number of channels.

        Args:
            num_channels (int): Number of input and output channels for the convolutions.
        """
        super().__init__()

        # First convolutional layer: 3x3 kernel, padding=1 to keep spatial dimensions constant.
        self.conv1 = nn.Conv2d(num_channels, num_channels, kernel_size=3, padding=1)
        # Batch normalization to stabilize and accelerate training.
        self.bn1 = nn.BatchNorm2d(num_channels)

        # Second convolutional layer: identical to the first.
        self.conv2 = nn.Conv2d(num_channels, num_channels, kernel_size=3, padding=1)
        # Batch normalization for the second convolution's output.
        self.bn2 = nn.BatchNorm2d(num_channels)

    @override
    def forward(self, x: T.Tensor) -> T.Tensor:
        """
        Forward pass through the residual block.

        Args:
            x (T.Tensor): Input tensor of shape (N, C, H, W).

        Returns:
            T.Tensor: Output tensor after applying the residual mapping.
        """
        # Save the input for the skip connection.
        residual = x

        # First block: Convolution -> Batch Norm -> ReLU.
        x = F.relu(self.bn1(self.conv1(x)))

        # Second block: Convolution -> Batch Norm.
        x = self.bn2(self.conv2(x))

        # Add the original input (residual) to the processed features.
        x += residual

        # Final ReLU activation.
        return F.relu(x)


class SternhalmaZero(nn.Module):
    """
    AlphaZero-inspired neural network architecture for Sternhalma.
    Consists of a shared residual backbone followed by separate policy and value heads.
    """

    def __init__(self, board_size: int, num_actions: int, num_res_blocks: int = 10):
        """
        Initializes the SternhalmaZero model.

        Args:
            board_size (int): The dimension of the square board representation.
            num_actions (int): Total number of possible actions in the game.
            num_res_blocks (int): Number of residual blocks in the backbone.
        """
        super().__init__()

        # Initial Convolutional Block: Extracts low-level features from the input state.
        self.start_conv = nn.Conv2d(3, 128, kernel_size=3, padding=1)
        self.start_bn = nn.BatchNorm2d(128)

        # Backbone: A sequence of residual blocks to extract deep features.
        self.backbone = nn.Sequential(*[ResBlock(128) for _ in range(num_res_blocks)])

        # Policy Head: Predicts the probability distribution over all possible actions.
        # Outputs a vector of size `num_actions` with the log-probabilities (priors) of each action.
        self.policy_conv = nn.Conv2d(128, 32, kernel_size=1)
        self.policy_bn = nn.BatchNorm2d(32)
        self.policy_fc = nn.Linear(32 * board_size * board_size, num_actions)

        # Value Head: Estimates the value of the current board state.
        # Outputs a scalar value typically interpreted in the range [-1, 1].
        self.value_conv = nn.Conv2d(128, 3, kernel_size=1)
        self.value_bn = nn.BatchNorm2d(3)
        self.value_fc1 = nn.Linear(3 * board_size * board_size, 64)
        self.value_fc2 = nn.Linear(64, 1)

    @override
    def forward(self, x: T.Tensor) -> tuple[T.Tensor, T.Tensor]:
        """
        Forward pass through the network to compute policy logits and state value.

        Args:
            x (T.Tensor): Input tensor of shape (N, 3, board_size, board_size).

        Returns:
            tuple[T.Tensor, T.Tensor]: A tuple containing:
                - policy: Logits for each action, shape (N, num_actions).
                - value: Scalar value estimate, shape (N, 1).
        """
        # Initial Convolutional Block: Conv -> BN -> ReLU.
        x = F.relu(self.start_bn(self.start_conv(x)))

        # Pass through the stack of Residual Blocks.
        x = self.backbone(x)

        # Policy Head: Conv -> BN -> ReLU -> Flatten -> Linear.
        policy = F.relu(self.policy_bn(self.policy_conv(x)))
        policy = policy.view(policy.size(0), -1)
        policy = self.policy_fc(policy)

        # Value Head: Conv -> BN -> ReLU -> Flatten -> Linear -> ReLU -> Linear.
        value = F.relu(self.value_bn(self.value_conv(x)))
        value = value.view(value.size(0), -1)
        value = self.value_fc1(value)
        value = F.relu(value)
        value = self.value_fc2(value)

        return policy, value
