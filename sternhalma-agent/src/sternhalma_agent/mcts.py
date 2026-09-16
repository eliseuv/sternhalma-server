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
from numpy.typing import NDArray

from sternhalma_agent.action_space import (
    NUM_ACTIONS,
    decode_action,
    legal_action_indices,
    mask_and_renormalize,
)
from sternhalma_agent.alphazero import SternhalmaZero, from_state
from sternhalma_agent.heuristic import potential, potential_after_move

C_PUCT = 1.5

# How strongly the potential function (heuristic.py) biases priors relative
# to the network's own policy. 0 disables it entirely. Most useful early,
# before the network is trained and its own priors are close to random.
DEFAULT_HEURISTIC_WEIGHT = 0.3


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


def _bias_priors_with_potential(
    probs: NDArray[np.float32],
    movements: NDArray[np.int_],
    game: sternhalma_rs.Game,
    weight: float,
) -> NDArray[np.float32]:
    """Reweights `probs` (over `movements`, same order) toward moves that
    increase heuristic.potential more, via a log-linear (product-of-experts)
    blend: log(prior) + weight * potential_gain, renormalized.
    """
    base = potential(game)
    gains = np.array(
        [
            potential_after_move(game, (int(m[0][0]), int(m[0][1])), (int(m[1][0]), int(m[1][1])))
            - base
            for m in movements
        ],
        dtype=np.float32,
    )
    logits = np.log(probs + 1e-8) + weight * gains
    logits -= logits.max()  # numerical stability before exponentiating
    weighted = np.exp(logits)
    return (weighted / weighted.sum()).astype(np.float32)


def _evaluate_and_expand(
    node: Node,
    game: sternhalma_rs.Game,
    network: SternhalmaZero,
    device: str,
    heuristic_weight: float = 0.0,
) -> float:
    """Runs the network on `game`, expands `node`'s children, returns the leaf value."""
    movements = np.array(game.available_moves())
    with T.no_grad():
        policy_logits, value = network(from_state(game, device=device))
    policy = T.softmax(policy_logits.squeeze(0), dim=0).cpu().numpy()
    probs = mask_and_renormalize(policy, movements)
    if heuristic_weight:
        probs = _bias_priors_with_potential(probs, movements, game, heuristic_weight)
    indices = legal_action_indices(movements)
    for action, prob in zip(indices.tolist(), probs.tolist()):
        node.children[action] = Node(prior=prob)
    return float(value.item())


def _run_search(
    game: sternhalma_rs.Game,
    network: SternhalmaZero,
    num_simulations: int,
    device: str,
    heuristic_weight: float,
) -> Node:
    """Runs MCTS from `game`'s current position, returns the expanded root.

    `game` itself is not mutated -- simulations run on independent clones.
    """
    root = Node(prior=1.0)
    _evaluate_and_expand(root, game, network, device, heuristic_weight)

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
            value = _evaluate_and_expand(
                node, sim_game, network, device, heuristic_weight
            )

        for path_node in reversed(path):
            path_node.visit_count += 1
            path_node.value_sum += value
            value = -value

    return root


def search(
    game: sternhalma_rs.Game,
    network: SternhalmaZero,
    num_simulations: int,
    device: str = "cuda",
    heuristic_weight: float = DEFAULT_HEURISTIC_WEIGHT,
) -> tuple[tuple[int, int], tuple[int, int]]:
    """Runs MCTS from `game`'s current position and returns the chosen move.

    `heuristic_weight` biases priors toward heuristic.potential (see
    _bias_priors_with_potential); 0 disables it, using the network's own
    policy alone.
    """
    root = _run_search(game, network, num_simulations, device, heuristic_weight)
    best_action = max(root.children.items(), key=lambda item: item[1].visit_count)[0]
    return decode_action(best_action)


def search_with_policy(
    game: sternhalma_rs.Game,
    network: SternhalmaZero,
    num_simulations: int,
    device: str = "cuda",
    heuristic_weight: float = DEFAULT_HEURISTIC_WEIGHT,
) -> tuple[tuple[tuple[int, int], tuple[int, int]], NDArray[np.float32]]:
    """Like search(), but also returns the MCTS visit-count policy target
    over the full fixed action space (action_space.NUM_ACTIONS) -- the
    training target self-play games record (R-20).
    """
    root = _run_search(game, network, num_simulations, device, heuristic_weight)

    policy = np.zeros(NUM_ACTIONS, dtype=np.float32)
    total_visits = sum(child.visit_count for child in root.children.values())
    for action, child in root.children.items():
        policy[action] = child.visit_count / total_visits

    best_action = max(root.children.items(), key=lambda item: item[1].visit_count)[0]
    return decode_action(best_action), policy
