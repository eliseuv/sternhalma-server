---
status: active
category: ai
progress: 0  # unassessed
started: 2025-06-19
updated: 2026-09-15
vault_ref: chinese-checkers-ai
---

## Log
- 2026-09-15: Implemented R-9 — added criterion benchmarks for
  sternhalma-game's move generation and move application. No throughput
  target set (measured only ~2.1us/move-generation, ~30ns/move-application
  on this machine); per its own acceptance criteria, a real target waits for
  R-5's self-play loop to exist and reveal the actual bottleneck.
- 2026-09-15: Implemented R-7 — sternhalma-game now has 23 unit tests of its
  own (board bounds/placement, single-step and chain-jump movement,
  validation errors, scoring, win detection), independent of
  sternhalma-server's integration tests. Found and documented, but did not
  fix (out of scope for a test-coverage item), a real validation gap: a
  length-1 `Hops` path currently validates as a no-op instead of being
  rejected as too short.
- 2026-09-15: Guided review pass — user wrote a roadmap into `DIRECTIONS.md`
  (Preparation/Learning/Improvement). Confirmed it matched what the prior
  unguided pass had already found (R-5/R-6/R-7/R-8, D-2) and folded in two
  extensions it named beyond that: a throughput benchmark for
  `sternhalma-game` with no invented target (R-9, deferred until R-5 exists
  to calibrate against), and checkpoint-gating as a more rigorous self-play
  benchmark than the random-baseline win rate (G-6, R-10). Recorded the three
  named phases as M-1/M-2/M-3.
- 2026-09-15: Migrated tracking from the legacy `.claude/PROJECT.md` shape
  (About/Notes/Log) to `PROJECT_SPEC.md` + `DIRECTIONS.md`. The About
  paragraph's content now lives in the root `README.md` and `PROJECT_SPEC.md`'s
  Goals; the Notes section's state-graph math moved into R-3's body, its open
  question ("is a board configuration tied to a given player's turn?") was
  resolved as D-1 (yes — canonicalized to the current player's perspective),
  and its todo item became R-3. Audit (unguided pass, `DIRECTIONS.md` was
  empty) found: the AlphaZero training loop doesn't exist yet — no MCTS, no
  self-play, `main.py --train` is a no-op (now R-5); the agent duplicates game
  rules in a from-scratch Python reimplementation instead of using the Rust
  bindings, per the user's direction that Python consumers should use bindings
  rather than reimplement rules (D-2, R-6); `sternhalma-game` has no unit
  tests of its own (R-7); three TODOs in `sternhalma-server` silently drop
  invalid client requests instead of reporting them (R-8).
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
