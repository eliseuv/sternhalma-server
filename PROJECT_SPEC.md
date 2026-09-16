---
spec_version: 1
project: sternhalma
status: drafting
category: ai
language: rust
created: 2025-06-19
updated: 2026-09-15
---

# Sternhalma AI

## 0. Handoff

<!-- Rewritten at the end of every session. Read this first; it is the only
     section guaranteed to describe the present moment. Three lines, present
     tense, concrete — "next action" must be executable by someone with no
     memory of the session:

     - **Last session:** ...
     - **Now blocked on:** ...
     - **Next action:** ... -->

- **Last session:** Migrated this repo from a legacy .claude/PROJECT.md to PROJECT_SPEC.md/DIRECTIONS.md; audited the codebase (unguided pass, DIRECTIONS.md was empty) and found the AlphaZero training loop doesn't exist yet, the agent duplicates game rules in Python instead of using the Rust bindings, and sternhalma-game has no unit tests of its own.
- **Now blocked on:** Nothing formally (no open Q- items) — R-6 (the self-play/MCTS loop) is the practical prerequisite for R-1/R-2/R-3.
- **Next action:** Implement R-6 (MCTS-guided self-play training loop), then R-7 (migrate the agent onto sternhalma_rs bindings) before touching R-1/R-2/R-3's refinements.

## 2. Problem

_What is broken today, for whom, and what it costs them. No solutions here._

## 3. Goals

<!-- items: G -->

### G-1 — sternhalma-game correctly implements the full Sternhalma ruleset
- status: accepted
- metric: Single-step and chain-jump movement, scoring, and win detection all match the official Sternhalma rules, exercised end-to-end by sternhalma-server's integration tests (tests/gameplay.rs); no unit tests of its own yet.

### G-2 — sternhalma-python exposes the game engine's full API to Python
- status: accepted
- metric: sternhalma_rs Python module exposes player/winner/turns/scores/history/board/available_moves/apply_movement, and a complete game can be driven end-to-end from Python (verified by sternhalma-python/client/test_game.py).

### G-3 — AlphaZero agent achieves high-level Sternhalma play through self-play
- status: accepted
- metric: Agent achieves >=90% win rate over N self-play games against a random-move baseline agent.

### G-4 — sternhalma-server reliably hosts games over TCP and WebSocket
- status: accepted
- metric: Passes its full integration suite (tests/connection.rs, tests/gameplay.rs, tests/reconnection.rs): connection handling up to capacity, full gameplay cycles, and session resumption after disconnect.

### G-5 — sternhalma-web provides a real-time playable web client
- status: accepted
- metric: A user can complete a full game end-to-end against a running sternhalma-server over WebSocket, with moves, turn order and scores staying in sync (manual playtest; no automated test suite yet).

## 4. Non-Goals

<!-- items: NG -->

### NG-1 — Support for more than 2 players
- status: accepted

Traditional Sternhalma supports 2, 3, 4 or 6 players. This implementation is built exclusively for 2-player games throughout: sternhalma-game's Player enum, scoring, and the client/server protocol all hard-code exactly two sides. Found while reading the code during migration, not previously stated anywhere; not planned, would require rework across every component.

## 5. Constraints

<!-- items: C -->

## 6. Glossary

_Terms that mean something specific in this project. Cheap to write, and it
stops two async participants from silently using one word for two things._

## 7. Requirements

<!-- items: R -->

### R-1 — Guide agent search with a potential/heuristic function
- status: specified
- acceptance: A potential/heuristic function exists and measurably influences agent move selection (e.g. biases MCTS priors or rollout evaluation toward stronger moves), per the todo's own phrasing.
- covers: [G-3]
- refs: [R-5]

From sternhalma-agent/todo.md's General section: "Implement some kind of potential function to guide the agent to the best moves." No concrete target specified yet.

Depends on R-5 (the self-play training loop doesn't exist yet; this item refines it once it does).

### R-2 — Add correctness checks for the agent training loop
- status: specified
- acceptance: All four hold: (1) training loss is printed/logged every step; (2) a test confirms the replay buffer stores and samples transitions correctly; (3) a test confirms target-network weights are copied from the evaluation network on the configured schedule; (4) board state inputs fed to the network are normalized rather than raw arbitrary IDs.
- covers: [G-3]
- refs: [R-5]

From sternhalma-agent/todo.md's Testing section ("avoid silent failures where the program runs but the agent never learns because the math isn't right"):
- Print the loss at each training step.
- Replay buffer stores and samples transitions correctly.
- Target network weights are copied from the evaluation network on schedule.
- Board state inputs are normalized rather than raw arbitrary IDs.

Depends on R-5 (the self-play training loop doesn't exist yet; this item refines it once it does).

### R-3 — Support a smaller/reduced board variant for faster iteration
- status: specified
- acceptance: The game/agent can be configured to run on a board smaller than the standard 121-cell board, reducing the training/testing state space.
- covers: [G-3]
- refs: [R-5]

From the old vault note (now this repo's .claude/PROJECT.md): reduced state space for faster training/testing iteration. No concrete board size specified yet.

Depends on R-5 (the self-play training loop doesn't exist yet; this item refines it once it does).

State-space context, carried over from the old vault note: full board has $N = \frac{121!}{(121-30)!15!15!} \approx 3.5 \times 10^{36}$ configurations ($\log_2 N \approx 121.4$).

### R-4 — Support multiple concurrent game sessions on sternhalma-server
- status: specified
- covers: [G-4]
- acceptance: Server can host N>1 simultaneous games without cross-session interference, each with its own Game state and connected clients, via a Lobby actor spawning independent Server Tasks per match.

Explicitly named as a future direction in sternhalma-server/README.md: currently configured for a single game session; architecture is designed to support this.

### R-5 — Implement MCTS-guided self-play training loop
- status: specified
- covers: [G-3]
- acceptance: SternhalmaZero's policy/value outputs drive a Monte Carlo Tree Search over available moves; self-play games generate training data via a replay buffer; the network is optimized against that data with a target-network update schedule. main.py's --train flag actually trains, rather than being a no-op.

Currently missing entirely: no MCTS implementation exists anywhere in sternhalma-agent, main.py's training_mode branch is `if training_mode: pass`, and AgentConstant/AgentDQN/AgentBrownian are stub or trivial agents (AgentDQN.decide_movement always returns 0, self.nn is never used). alphazero.py only defines the network architecture (ResBlock, SternhalmaZero) and state encoding (from_state) — nothing consumes them for search or training yet. R-1, R-2 and R-3 (from the old todo.md) assume refining an existing training loop; this item is their actual prerequisite.

### R-6 — Migrate sternhalma-agent to use sternhalma_rs bindings instead of its own Python game-rules reimplementation
- status: specified
- covers: [G-3]
- from: [D-2]
- acceptance: Agent's board-state tracking and move application (currently in sternhalma-agent/sternhalma.py's Board/Player/movement code) go through sternhalma_rs via sternhalma-python instead; the independent Python reimplementation is removed once migrated.

Implements D-2. Also removes the duplication between sternhalma-agent/sternhalma.py and sternhalma-python/client/sternhalma.py (the latter is a thin wrapper already doing roughly this, for a single-process demo/test client rather than the network-play agent).

### R-7 — Add direct unit test coverage for sternhalma-game
- status: specified
- covers: [G-1]
- acceptance: sternhalma-game has its own unit/property tests covering single-step movement, chain-jump movement, scoring, and win detection, independent of sternhalma-server's integration tests.

Found during audit: sternhalma-game has zero #[test] functions of its own; correctness is currently only exercised indirectly via sternhalma-server's tests/gameplay.rs. movement.rs also contains several unsafe blocks (apply_movement_unchecked, unwrap_unchecked) whose invariants are presently unverified by any test at this layer.

### R-8 — Report invalid client requests back to the offending client
- status: specified
- covers: [G-4]
- acceptance: An out-of-turn move or an invalid movement_index results in an explicit rejection message sent back to that client (not just a server-side log line), so misbehaving or desynced clients can recover.

Three TODOs in sternhalma-server/src/lib.rs (lines ~117, ~301, ~310) mark this as known-missing: out-of-turn moves and invalid movement indices are currently logged and silently dropped rather than reported to the client. Low severity — a misbehaving client only misses its own turn — but explicitly called out in the code as intended follow-up.

## 8. Interfaces

_The externally visible contract: CLI surface, API shapes, file formats, exit
codes. Prose and code blocks, not items — this section is quoted, not queried._

## 9. Decisions

<!-- items: D -->

### D-1 — Board state is canonicalized to the current player's perspective
- status: accepted
- options: [perspective-relative encoding, absolute Player1/Player2 encoding]
- chosen: perspective-relative encoding

Resolves an open question carried over from the old vault note ("Is a board configuration tied to a given player's turn?"): yes. sternhalma-agent/alphazero.py's from_state() states the input board tensor is always from the perspective of the current player (canonicalized as Player 1), confirmed by reading the implementation.

### D-2 — Game rules live canonically in sternhalma-game (Rust); Python consumers use it via bindings, not reimplementations
- status: accepted
- options: [each Python consumer reimplements rules independently, all Python consumers use sternhalma_rs via sternhalma-python bindings]
- chosen: all Python consumers use sternhalma_rs via sternhalma-python bindings

User's explicit direction: "There should be a core high performance rust implementation of the game with bindings for python and a python agent that will use these bindings and implement the AlphaZero algorithm." Resolves the duplication found during migration: sternhalma-agent currently maintains its own 250-line from-scratch Python reimplementation of board/movement/scoring (sternhalma-agent/sternhalma.py), completely independent of sternhalma-game and unused by sternhalma-python's own bindings/client. Superseded going forward by this decision; see R- item migrating the agent.

## 10. Assumptions

<!-- items: A -->

## 11. Open Questions

<!-- items: Q -->

## 12. Risks

<!-- items: RK -->

## 13. Milestones

<!-- items: M -->

## 14. Changelog

_Append-only. Newest at the bottom._
- 2026-09-15 — added G-1: sternhalma-game correctly implements the full Sternhalma ruleset
- 2026-09-15 — added G-2: sternhalma-python exposes the game engine's full API to Python
- 2026-09-15 — added G-3: AlphaZero agent achieves high-level Sternhalma play through self-play
- 2026-09-15 — added G-4: sternhalma-server reliably hosts games over TCP and WebSocket
- 2026-09-15 — added G-5: sternhalma-web provides a real-time playable web client
- 2026-09-15 — added R-1: Guide agent search with a potential/heuristic function
- 2026-09-15 — added R-2: Add correctness checks for the agent training loop
- 2026-09-15 — added R-3: Support a smaller/reduced board variant for faster iteration
- 2026-09-15 — added R-4: Support multiple concurrent game sessions on sternhalma-server
- 2026-09-15 — added D-1: Board state is canonicalized to the current player's perspective
- 2026-09-15 — R-1 acceptance: ∅ -> A potential/heuristic function exists and measurably influences agent move selection (e.g. biases MCTS priors or rollout evaluation toward stronger moves), per the todo's own phrasing.
- 2026-09-15 — R-2 acceptance: ∅ -> All four hold: (1) training loss is printed/logged every step; (2) a test confirms the replay buffer stores and samples transitions correctly; (3) a test confirms target-network weights are copied from the evaluation network on the configured schedule; (4) board state inputs fed to the network are normalized rather than raw arbitrary IDs.
- 2026-09-15 — R-3 acceptance: ∅ -> The game/agent can be configured to run on a board smaller than the standard 121-cell board, reducing the training/testing state space.
- 2026-09-15 — added NG-1: Support for more than 2 players
- 2026-09-15 — added R-5: Implement MCTS-guided self-play training loop
- 2026-09-15 — added D-2: Game rules live canonically in sternhalma-game (Rust); Python consumers use it via bindings, not reimplementations
- 2026-09-15 — added R-6: Migrate sternhalma-agent to use sternhalma_rs bindings instead of its own Python game-rules reimplementation
- 2026-09-15 — added R-7: Add direct unit test coverage for sternhalma-game
- 2026-09-15 — added R-8: Report invalid client requests back to the offending client
- 2026-09-15 — R-1 refs: ∅ -> [R-6]
- 2026-09-15 — R-2 refs: ∅ -> [R-6]
- 2026-09-15 — R-3 refs: ∅ -> [R-6]
- 2026-09-15 — R-3 status: specified -> specified
- 2026-09-15 — R-1 refs: [R-6] -> [R-5]
- 2026-09-15 — R-2 refs: [R-6] -> [R-5]
- 2026-09-15 — R-3 refs: [R-6] -> [R-5]
