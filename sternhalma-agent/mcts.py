"""Monte Carlo Tree Search guided by SternhalmaZero's policy and value heads.

Standard AlphaZero-style MCTS: UCB selection using policy priors down to a
leaf, network-based expansion and evaluation at the leaf, then backup along
the path with the value negated at each level (each level alternates whose
perspective "value" is measured from).
"""

import math
from dataclasses import dataclass, field

import numpy as np
import sternhalma_rs
import torch as T

from action_space import decode_action, legal_action_indices, mask_and_renormalize
from alphazero import SternhalmaZero, from_state

C_PUCT = 1.5


def clone_game(game: sternhalma_rs.Game) -> sternhalma_rs.Game:
    """An independent copy of `game`'s current position.

    sternhalma_rs.Game exposes no clone or undo, so this replays its move
    history onto a fresh instance instead -- cheap, since applying a move
    is ~30ns (see sternhalma-game's own criterion benchmarks).
    """
    clone = sternhalma_rs.Game()
    for from_cell, to_cell in game.history():
        clone.apply_movement_unchecked(from_cell, to_cell)
    return clone


@dataclass
class Node:
    prior: float
    visit_count: int = 0
    value_sum: float = 0.0
    children: dict[int, "Node"] = field(default_factory=dict)  # action -> child

    @property
    def value(self) -> float:
        return self.value_sum / self.visit_count if self.visit_count else 0.0

    @property
    def expanded(self) -> bool:
        return bool(self.children)


def _ucb_score(parent: Node, child: Node) -> float:
    exploration = (
        C_PUCT * child.prior * math.sqrt(parent.visit_count) / (1 + child.visit_count)
    )
    # child.value is from the child's own (the opponent's) perspective.
    return -child.value + exploration


def _select_child(node: Node) -> tuple[int, Node]:
    return max(node.children.items(), key=lambda item: _ucb_score(node, item[1]))


def _evaluate_and_expand(
    node: Node, game: sternhalma_rs.Game, network: SternhalmaZero, device: str
) -> float:
    """Runs the network on `game`, expands `node`'s children, returns the leaf value."""
    movements = np.array(game.available_moves())
    with T.no_grad():
        policy_logits, value = network(from_state(game, device=device))
    policy = T.softmax(policy_logits.squeeze(0), dim=0).cpu().numpy()
    probs = mask_and_renormalize(policy, movements)
    indices = legal_action_indices(movements)
    for action, prob in zip(indices.tolist(), probs.tolist()):
        node.children[action] = Node(prior=prob)
    return float(value.item())


def search(
    game: sternhalma_rs.Game,
    network: SternhalmaZero,
    num_simulations: int,
    device: str = "cuda",
) -> tuple[tuple[int, int], tuple[int, int]]:
    """Runs MCTS from `game`'s current position and returns the chosen move.

    `game` itself is not mutated -- simulations run on independent clones.
    """
    root = Node(prior=1.0)
    _evaluate_and_expand(root, game, network, device)

    for _ in range(num_simulations):
        node = root
        sim_game = clone_game(game)
        path = [node]

        while node.expanded:
            action, node = _select_child(node)
            from_cell, to_cell = decode_action(action)
            sim_game.apply_movement_unchecked(from_cell, to_cell)
            path.append(node)

        if sim_game.player() == 0:
            # Terminal position: sternhalma-game only ever finishes a game
            # by the mover completing their own goal (there is no
            # opponent-blocks-you loss condition), so whoever's turn would
            # be next always just lost. "Value" is measured from the
            # perspective of whoever's turn it is at a node, so that's -1.
            value = -1.0
        else:
            value = _evaluate_and_expand(node, sim_game, network, device)

        for path_node in reversed(path):
            path_node.visit_count += 1
            path_node.value_sum += value
            value = -value

    best_action = max(root.children.items(), key=lambda item: item[1].visit_count)[0]
    return decode_action(best_action)
