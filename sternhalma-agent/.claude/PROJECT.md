---
status: active
category: ai
progress: 0  # unassessed
started: 2025-07-25
updated: 2026-08-22
vault_ref: chinese-checkers-ai
---

## About
An AI for Chinese Checkers (Sternhalma), implementing AlphaZero from scratch. This repo holds the agent (`agent.py`, `alphazero.py`); sibling repos `../sternhalma` (game engine + Python bindings) and `../sternhalma-web` cover the rest of the effort — the latter had a commit as recently as 2026-06-10.

## Notes
Carried over from the original "Sternhalma" note in the old vault:

### State graph
Total number of nodes:
$$N = \frac{121!}{(121-30)!15!15!} \approx 3.5 \times 10^{36}$$
$$\log_2 N \approx 121.4$$

#### Questions
1. Is a board configuration tied to a given player's turn?

### Concepts
- Policy network: Provides move priors for MCTS.

### Todo
- Smaller board (reduced state space for faster iteration/testing).

## Log
- 2026-08-22: Migrated tracking from the vault's `Projects/chinese-checkers-ai.md` idea note to this repo. Progress not yet assessed against repo state.
- 2026-02-01: Last commit in this repo's history — refactored client and protocol into a client package.
