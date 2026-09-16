---
status: active
category: ai
progress: 0  # unassessed
started: 2025-06-19
updated: 2026-09-15
vault_ref: chinese-checkers-ai
---

## About
This project implements the AlphaZero algorithm from scratch to master the
game of **Sternhalma** (commonly known as Chinese Checkers). It covers the
whole stack: the Rust game engine and server (`sternhalma-game`,
`sternhalma-server`), Python bindings onto that engine (`sternhalma-python`,
including a safe wrapper client at `sternhalma-python/client`), the AlphaZero
agent (`sternhalma-agent`), and a React/TypeScript web client
(`sternhalma-web`). Formerly three separate repos, merged into this one on
2026-09-15 with full commit history preserved via git subtree merges.

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
- 2026-09-15: Merged the sibling `sternhalma-agent` and `sternhalma-web` repos
  into this repo via git subtree merge, preserving full commit history from
  both. Moved the pre-existing Python bindings client wrapper from
  `sternhalma-agent/` to `sternhalma-python/client/` to free that path for the
  merged agent project. Consolidated the three repos' separate
  `.claude/PROJECT.md` files into this one.
- 2026-08-22: Added agent project-tracking file (`.claude/PROJECT.md`) in each
  of the three now-merged repos; status/progress inferred from repo state, not
  yet hand-reviewed.
- 2026-08-22: Migrated tracking from the vault's `Projects/chinese-checkers-ai.md`
  idea note to the `sternhalma-agent` repo (now merged in here). Progress not
  yet assessed against repo state.
- 2026-06-10: Last commit in this repo's (`sternhalma`) history before the
  tracking-file migration.
- 2026-04-06: Last commit in `sternhalma-web`'s history before its migration.
- 2026-02-01: Last commit in `sternhalma-agent`'s history — refactored client
  and protocol into a client package.
