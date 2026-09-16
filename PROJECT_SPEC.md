---
spec_version: 1
project: sternhalma
status: drafting
category: ai
language: rust
created: 2025-06-19
updated: 2026-09-16
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

- **Last session:** Reorganized the 10 outstanding requirements by complexity (agenda from the command argument). R-3 (smaller board) turned out to be another large task disguised as one item -- decomposed into R-27 (Rust board size configurable, large), R-28 (expose via bindings, small-medium), R-29 (confirm agent-side adapts, small -- likely pure verification since action_space.py/heuristic.py already derive their constants at runtime). Every other outstanding item got a Complexity: note in its body.
- **Now blocked on:** Nothing (no open Q- items).
- **Next action, by complexity:**
  - Small, unblocked now: R-17 (cross-game reconnection -- likely just needs a test), R-21 (replay buffer).
  - Medium, unblocked now: R-20 (self-play generation -- R-18/R-19/R-1 are all done).
  - Then in chain order: R-22 (medium-large, needs R-21) -> R-23 (medium, needs R-20/21/22) -> R-24/R-25/R-26 (trivial/small, pick up as their prerequisite lands) -> R-10 (medium, needs R-23).
  - Large standalone track, independent of the above, tackle whenever: R-27 -> R-28 -> R-29 (board-size configurability).

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

### G-6 — AlphaZero agent passes checkpoint-gating evaluation against its own prior best
- status: accepted
- metric: A new checkpoint must beat the previous best checkpoint in >=55% of evaluation games to replace it as the new best network (the standard AlphaZero self-improvement gate).

Follow-on to G-3's cheaper early signal (win rate vs. a random baseline). Represents "more robust real-world benchmarking with self-play" from DIRECTIONS.md. Only measurable once R-5 (self-play training loop) exists.

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
- status: implemented
- acceptance: A potential/heuristic function exists and measurably influences agent move selection (e.g. biases MCTS priors or rollout evaluation toward stronger moves), per the todo's own phrasing.
- covers: [G-3]
- refs: [R-19]

From sternhalma-agent/todo.md's General section: "Implement some kind of potential function to guide the agent to the best moves." No concrete target specified yet.

Depends on R-5 (the self-play training loop doesn't exist yet; this item refines it once it does).

Corrected a real bug found by my own first test: potential() must be symmetric (current-mover-relative, same convention as SternhalmaZero's own value head and MCTS's backup), not fixed to a single identity like from_state()'s canonical 'me' -- a fixed-identity version silently measured the wrong side's pieces after every odd number of moves, since sternhalma_rs.Game.board()'s channel 0 tracks whoever's turn it currently is. Goal region for the current mover is picked via move-count parity (the game always starts with Player 1 to move and alternates deterministically).

### R-2 — Add correctness checks for the agent training loop
- status: superseded
- acceptance: All four hold: (1) training loss is printed/logged every step; (2) a test confirms the replay buffer stores and samples transitions correctly; (3) a test confirms target-network weights are copied from the evaluation network on the configured schedule; (4) board state inputs fed to the network are normalized rather than raw arbitrary IDs.
- covers: [G-3]
- refs: [R-5]

From sternhalma-agent/todo.md's Testing section ("avoid silent failures where the program runs but the agent never learns because the math isn't right"):
- Print the loss at each training step.
- Replay buffer stores and samples transitions correctly.
- Target network weights are copied from the evaluation network on schedule.
- Board state inputs are normalized rather than raw arbitrary IDs.

Depends on R-5 (the self-play training loop doesn't exist yet; this item refines it once it does).

Point 4 (board inputs normalized) is already satisfied: alphazero.py's from_state emits binary 0.0/1.0 mask channels (via sternhalma_rs.Game.board()), not raw arbitrary IDs -- confirmed by reading the code, not carried forward as a new item. Points 1-3 became R-24/R-25/R-26.

### R-3 — Support a smaller/reduced board variant for faster iteration
- status: superseded
- acceptance: The game/agent can be configured to run on a board smaller than the standard 121-cell board, reducing the training/testing state space.
- covers: [G-3]
- refs: [R-23]

From the old vault note (now this repo's .claude/PROJECT.md): reduced state space for faster training/testing iteration. No concrete board size specified yet.

Depends on R-5 (the self-play training loop doesn't exist yet; this item refines it once it does).

State-space context, carried over from the old vault note: full board has $N = \frac{121!}{(121-30)!15!15!} \approx 3.5 \times 10^{36}$ configurations ($\log_2 N \approx 121.4$).

### R-4 — Support multiple concurrent game sessions on sternhalma-server
- status: superseded
- covers: [G-4]
- acceptance: Server can host N>1 simultaneous games without cross-session interference, each with its own Game state and connected clients, via a Lobby actor spawning independent Server Tasks per match.

Explicitly named as a future direction in sternhalma-server/README.md: currently configured for a single game session; architecture is designed to support this.

### R-5 — Implement MCTS-guided self-play training loop
- status: superseded
- covers: [G-3]
- acceptance: SternhalmaZero's policy/value outputs drive a Monte Carlo Tree Search over available moves; self-play games generate training data via a replay buffer; the network is optimized against that data with a target-network update schedule. main.py's --train flag actually trains, rather than being a no-op.

Currently missing entirely: no MCTS implementation exists anywhere in sternhalma-agent, main.py's training_mode branch is `if training_mode: pass`, and AgentConstant/AgentDQN/AgentBrownian are stub or trivial agents (AgentDQN.decide_movement always returns 0, self.nn is never used). alphazero.py only defines the network architecture (ResBlock, SternhalmaZero) and state encoding (from_state) — nothing consumes them for search or training yet. R-1, R-2 and R-3 (from the old todo.md) assume refining an existing training loop; this item is their actual prerequisite.

### R-6 — Migrate sternhalma-agent to use sternhalma_rs bindings instead of its own Python game-rules reimplementation
- status: superseded
- covers: [G-3]
- from: [D-2]
- acceptance: Agent's board-state tracking and move application (currently in sternhalma-agent/sternhalma.py's Board/Player/movement code) go through sternhalma_rs via sternhalma-python instead; the independent Python reimplementation is removed once migrated.

Implements D-2. Also removes the duplication between sternhalma-agent/sternhalma.py and sternhalma-python/client/sternhalma.py (the latter is a thin wrapper already doing roughly this, for a single-process demo/test client rather than the network-play agent).

### R-7 — Add direct unit test coverage for sternhalma-game
- status: implemented
- covers: [G-1]
- acceptance: sternhalma-game has its own unit/property tests covering single-step movement, chain-jump movement, scoring, and win detection, independent of sternhalma-server's integration tests.

Found during audit: sternhalma-game has zero #[test] functions of its own; correctness is currently only exercised indirectly via sternhalma-server's tests/gameplay.rs. movement.rs also contains several unsafe blocks (apply_movement_unchecked, unwrap_unchecked) whose invariants are presently unverified by any test at this layer.

"Very robust" per DIRECTIONS.md: interpreted as property/fuzz-style tests (already reflected in this item's acceptance) covering edge cases — board boundaries, repeated chain-jumps, near-finished-game states — not just example-based unit tests.

### R-8 — Report invalid client requests back to the offending client
- status: implemented
- covers: [G-4]
- acceptance: An out-of-turn move or an invalid movement_index results in an explicit rejection message sent back to that client (not just a server-side log line), so misbehaving or desynced clients can recover.

Three TODOs in sternhalma-server/src/lib.rs (lines ~117, ~301, ~310) mark this as known-missing: out-of-turn moves and invalid movement indices are currently logged and silently dropped rather than reported to the client. Low severity — a misbehaving client only misses its own turn — but explicitly called out in the code as intended follow-up.

### R-9 — Benchmark sternhalma-game's core operations for self-play throughput
- status: implemented
- covers: [G-1, G-3]
- refs: [R-20, R-23, R-7]
- acceptance: Move generation and move application are benchmarked (e.g. via criterion); a concrete throughput target is set once R-5's self-play loop exists and reveals the actual required moves/sec, since self-play calls this in a tight loop millions of times per training iteration.

From DIRECTIONS.md: "make this crate very robust and performant." No target invented yet — deliberately deferred until there's a real self-play loop to calibrate against, per the same judgment already applied to R-3's board size.

Measured (release build, this machine): game_iter_available_moves ~2.1us/call, board_apply_movement_unchecked ~30ns/call. No target enforced -- see R-9's acceptance.

### R-10 — Implement checkpoint-gating evaluation harness for self-play training
- status: specified
- covers: [G-6]
- refs: [R-23]
- acceptance: After each training iteration, the new checkpoint plays a fixed number of evaluation games against the previous best checkpoint; if it wins >=55%, it replaces the best network used for subsequent self-play generation.

Implements G-6. Depends on R-5 existing first.

Complexity: medium. Reuses most of R-20's self-play-via-MCTS machinery (play games, track outcomes) against two fixed checkpoints instead of one live network; the new part is just the win-rate gate and swapping 'best'. Depends on R-23 (needs checkpointing to exist).

### R-11 — Package sternhalma-python as an installable Python module and wire it as a uv dependency of sternhalma-agent
- status: implemented
- covers: [G-3]
- supersedes: [R-6]
- acceptance: sternhalma-python has a maturin-backed pyproject.toml; sternhalma-agent's uv project depends on it via a local path source; `uv sync` inside sternhalma-agent builds the Rust extension and `import sternhalma_rs` succeeds in its venv.

First slice of R-6, split off because it's packaging/build-tooling groundwork (maturin + uv path dependency across a Rust crate and a uv-managed Python project), not a code migration -- currently unwritten: sternhalma-python has no pyproject.toml at all, and neither flake.nix has maturin. Needs a flake change, which per standing instructions gets asked about before being made.

Found a pre-existing, unrelated test-collection failure while verifying (tests/test_integration.py: ModuleNotFoundError: No module named 'client') -- confirmed present before this change too (checked via git stash). Not fixed here, out of scope for R-11.

### R-12 — Migrate sternhalma-agent's board-state tracking onto sternhalma_rs bindings
- status: implemented
- covers: [G-3]
- supersedes: [R-6]
- acceptance: Agent's board-state tracking and move application go through sternhalma_rs instead of sternhalma-agent/sternhalma.py's independent Board/Player/movement reimplementation; that reimplementation is removed once migrated.
- refs: [R-11]

Second slice of R-6 -- the actual code migration this was originally about. Blocked on the packaging slice existing first (see the sibling R- item this was split alongside).

Found and fixed a real bug while implementing this: sternhalma_rs.Game always assumes its own Player 1 moves first, but for a real Player 2 client the opponent moves first (mismatched with the mirror's hardcoded turn order) -- the validating apply_movement() rejected the very first mirrored move with ValueError('Invalid movement'). Fixed by using apply_movement_unchecked() instead (matches the old Board's blind, unvalidated mirroring). Verified live against the real server binary: 237 successful moves across a real multi-turn game for both clients, zero errors. Known limitation, documented in agent.py: self.board's own turn/score bookkeeping (player()/turns()/scores()) is not reliable ground truth for a real Player 2 client -- only its board() tensor is, which from_state's existing channel-swap (added with R-12) correctly compensates for.

### R-13 — Fix sternhalma-python's clippy and rustfmt violations
- status: implemented
- covers: [G-2]
- acceptance: cargo clippy -p sternhalma_rs --all-targets -- -D warnings and cargo fmt -p sternhalma_rs -- --check both pass. Specifically: factor the (usize,usize),(usize,usize)) return types in available_moves/history into a named type alias (clippy::type_complexity), replace the two unnecessary .try_into().unwrap() with .into() in the movement-index conversion (clippy::unnecessary_fallible_conversions), and apply rustfmt's line-wrapping/whitespace fixes to apply_movement/apply_movement_unchecked.

Found while verifying R-11 (this crate was never checked with -D warnings before): 4 clippy errors and 3 formatting diffs, all in sternhalma-python/src/lib.rs. Confirmed pre-existing on the commit before R-11 too. Purely style/lint -- no behavior change, verified the exact clippy suggestions above by running clippy directly.

### R-14 — Fix sternhalma-agent's pytest collection failure
- status: implemented
- covers: [G-3]
- acceptance: uv run pytest inside sternhalma-agent collects and runs tests/test_integration.py without a ModuleNotFoundError.

Root cause confirmed: pytest inserts tests/ itself onto sys.path for rootless test files, not the project root, so tests/test_integration.py's 'from client.client import Client' can't find the root-level client/ package (this only works when running main.py/agent.py directly, since running a script adds its own directory to sys.path[0]).

Fix verified in a throwaway edit, reverted before writing this item: adding
  [tool.pytest.ini_options]
  pythonpath = ["."]
to sternhalma-agent/pyproject.toml (pytest's built-in pythonpath option, no new dependency) makes 'uv run pytest' collect and pass the one existing test.

Verified: uv run pytest collects and passes (1 passed), ruff check clean. basedpyright still reports 5 pre-existing errors + 145 warnings in tests/test_integration.py (uninitialized test-fixture attributes, unrelated to pythonpath) -- not fixed, out of scope for this item.

### R-15 — Reject length-1 Hops paths in sternhalma-game's validate_movement
- status: implemented
- covers: [G-1]
- acceptance: validate_movement returns Err(MovementError::ShortHopping(1)) for a Movement::Hops{path} of length 1, matching the existing length-0 case, instead of validating it as a no-op 'hop to the same cell'.

Found and documented, not fixed, while adding R-7's test coverage (see movement.rs's single_element_hops_path_is_a_validation_gap_not_a_rejection test and its doc comment). Root cause: path.get(1..) returns Some(&[]) rather than None when path.len() == 1, so the ShortHopping check never fires for exactly that length. Not reachable via sternhalma-server (it only ever applies moves selected by index from its own precomputed move list, never an arbitrary client-supplied path), but is a latent correctness gap in the public validate_movement/apply_movement API that sternhalma-python and any future direct caller (e.g. a self-play harness) can hit. Fixing it means updating single_element_hops_path_is_a_validation_gap_not_a_rejection's assertion (it currently pins the buggy behavior) to expect the rejection instead.

### R-16 — Add a Lobby that spawns an independent Server per match
- status: implemented
- covers: [G-4]
- supersedes: [R-4]
- acceptance: A Lobby component routes new connections to an open (not-yet-full) game or spawns a new independent Server task (with its own channel set and Game state) when none is open. Two games can run simultaneously without cross-session interference -- moves and broadcasts in one never reach the other. Verified by an integration test connecting 4 clients and confirming they split into two independent 2-player games.

First slice of R-4, split off because it needs a subsystem that doesn't exist yet: main.rs spawns exactly one Server for the process's whole lifetime today, and handshake.rs/AppState route every connection into that single global instance with no concept of "which game".

Also routes reconnection across concurrent games (tries each tracked game's session map in turn) -- this may satisfy R-17 as a side effect of the design, not verified with a dedicated test yet. Known limitation, not fixed here: finished games are never pruned from the Lobby's tracked list, so their (now-dead) channels linger and get uselessly probed on every join()/reconnect() scan -- harmless at this server's scale, a real leak over a long-lived process.

### R-17 — Route session reconnection across concurrent games
- status: implemented
- covers: [G-4]
- supersedes: [R-4]
- refs: [R-16]
- acceptance: A reconnecting client's session ID resolves to the correct game among however many are running concurrently, not just a player slot within a single game.

Second slice of R-4. Depends on R-16's Lobby existing first -- today each Server's own sessions: HashMap<Uuid, Player> only makes sense when there's exactly one game.

Complexity: small. Independent of the M-2 chain (different subsystem, sternhalma-server). R-16's Lobby.reconnect() already tries every tracked game in turn, so this may just need a verification test with 2+ concurrent games, not new implementation -- confirm rather than assume.

Confirmed: R-16's Lobby.reconnect() already routes correctly -- no new implementation needed, just this verification test. Verified via reconnection_resolves_to_the_correct_game_among_several: 2 concurrent games, disconnect+reconnect a player from the second game, confirm the reconnected client's move reaches only its true game partner and never the distractor game.

### R-18 — Define a fixed action encoding for the policy head and translate to/from the server's move list
- status: implemented
- covers: [G-3]
- supersedes: [R-5]
- acceptance: SternhalmaZero's policy head scores a fixed 121x121 (source-cell, target-cell) action space; a function maps this to/from the server's current-turn (from,to) move list, masking illegal actions and renormalizing over the legal ones. Verified by a unit test: masking+renormalizing a known policy vector against a known move list produces a distribution summing to 1 over exactly the legal moves.

First slice of R-5. Refines the user's chosen approach (fixed move-type grid, masked per turn) into something concrete: a (source-cell x direction x hop-distance) grid, as first proposed, can't cleanly represent chain-hop moves -- sternhalma-game's own MovementIndices already compresses a chain hop down to just [start, end] with no fixed direction/distance relationship between them, so a flat 121x121 (source,target) matrix is used instead. Strictly more general (handles chain hops uniformly) and simpler to implement than the direction/distance framing originally sketched.

### R-19 — Implement MCTS search using SternhalmaZero's policy/value outputs
- status: implemented
- covers: [G-3]
- acceptance: A MCTS implementation (selection via UCB using policy priors, expansion, leaf evaluation via SternhalmaZero's value head, backup) selects a move given a game state and a SternhalmaZero network; a test confirms it returns a legal move from the current available-moves list within a bounded number of simulations.
- refs: [R-18]

Second slice of R-5.

Terminal-value convention: sternhalma-game only ever finishes a game via the mover completing their own goal (no opponent-blocks-you loss condition), so at any terminal node reached during simulation, whoever's turn would be next always just lost -- terminal value is simply -1, always. clone_game() works around sternhalma_rs.Game having no clone/undo by replaying history() onto a fresh instance; cheap per R-9's ~30ns/move benchmark.

### R-20 — Implement self-play game generation
- status: specified
- covers: [G-3]
- acceptance: A self-play routine plays a complete game of SternhalmaZero (via MCTS) against itself, recording each turn's (board tensor, MCTS visit-count policy target, eventual game outcome) as a training example.
- refs: [R-19]

Third slice of R-5.

Complexity: medium. Unblocked now -- R-18/R-19/R-1 are all done. Orchestration over existing pieces (mcts.search, from_state, action_space), not a new algorithm: alternate search() calls, record (state, policy target, outcome) per turn, backfill the outcome once the game ends.

### R-21 — Implement a replay buffer for self-play training data
- status: implemented
- covers: [G-3]
- acceptance: A replay buffer stores (state, policy, outcome) training examples from self-play games and supports random-sampling a training batch; a fixed capacity with oldest-eviction (or similar) keeps memory bounded.
- refs: [R-20]

Fourth slice of R-5.

Complexity: small. A self-contained data structure (bounded-capacity buffer, push + random-sample) -- no dependency on the rest of the chain to start; only needs real self-play data (R-20) to be exercised end-to-end.

Dedicated test coverage deferred to R-25 (its own selected item this session, same acceptance) rather than duplicated here -- spot-verified manually (push beyond capacity evicts oldest, sample() is without-replacement and raises when asked for more than the buffer holds).

### R-22 — Implement the training step with target-network updates
- status: specified
- covers: [G-3]
- acceptance: A training step samples a batch from the replay buffer, computes the AlphaZero loss (policy cross-entropy + value MSE) against SternhalmaZero's evaluation network, and performs an optimizer step; a separate target network's weights are synced from the evaluation network on a configured interval.
- refs: [R-21]

Fifth slice of R-5.

Complexity: medium-large. The most involved piece of the chain still ahead: batched loss computation (policy cross-entropy over the 121x121 action space + value MSE), an optimizer, and a target-network sync schedule -- getting tensor shapes and the policy-target format consistent with action_space.py matters here.

### R-23 — Wire main.py --train to run the full self-play/train loop
- status: specified
- covers: [G-3]
- acceptance: Running main.py --train repeatedly generates self-play games, stores them in the replay buffer, and runs training steps on a configured schedule, saving model checkpoints periodically -- no longer a no-op.
- refs: [R-18, R-19, R-20, R-21, R-22]

Sixth and final slice of R-5, tying the previous five together.

Complexity: medium. Mostly plumbing once R-20/R-21/R-22 exist, but real plumbing: a training loop driving self-play -> buffer -> train on a schedule, plus checkpoint save/load and tracking which checkpoint self-play currently uses.

### R-24 — Log training loss at each training step
- status: specified
- covers: [G-3]
- supersedes: [R-2]
- refs: [R-22]
- acceptance: Each training step (R-22) logs/prints its computed loss value (policy and value components) so training progress is observable without instrumenting code.

First of R-2's three still-open checks (point 4 was already satisfied, see R-2's body).

Complexity: trivial. A logging statement inside R-22's training step, once it exists.

### R-25 — Test replay buffer stores and samples transitions correctly
- status: specified
- covers: [G-3]
- supersedes: [R-2]
- refs: [R-21]
- acceptance: A test confirms the replay buffer (R-21) returns exactly what was pushed into it (no corruption, correct shapes) and that sampling respects the configured batch size.

Second of R-2's three still-open checks.

Complexity: small. A focused unit test once R-21 exists, same shape as this session's other test-writing items (R-7, R-15, etc.).

### R-26 — Test target-network sync schedule
- status: specified
- covers: [G-3]
- supersedes: [R-2]
- refs: [R-22]
- acceptance: A test confirms the target network's weights match the evaluation network's immediately after a scheduled sync interval, and can differ between syncs.

Third of R-2's three still-open checks.

Complexity: small. A focused unit test once R-22 exists.

### R-27 — Make sternhalma-game's board size configurable instead of compile-time-fixed
- status: specified
- covers: [G-1, G-3]
- supersedes: [R-3]
- acceptance: sternhalma-game can construct a Board/Game at a board size smaller than the standard 17x17/121-cell star, with correct valid-position, starting-position, and goal-region layouts at that size (movement, hopping, scoring, and win detection all still correct -- covered by tests analogous to R-7's, run at at least one reduced size).

First (hardest) slice of R-3. Currently BOARD_LENGTH, VALID_POSITIONS ([HexIdx; 121]), PLAYER1_STARTING_POSITIONS/PLAYER2_STARTING_POSITIONS ([HexIdx; 15]) are all compile-time constants with sizes baked into the array types (sternhalma-game/src/board/lut.rs) -- this needs real restructuring (e.g. Vec-backed LUTs computed for a given size, or a const generic), not a parameter tweak. Complexity: large.

### R-28 — Expose configurable board size through sternhalma-python's bindings
- status: specified
- covers: [G-2, G-3]
- supersedes: [R-3]
- refs: [R-27]
- acceptance: sternhalma_rs.Game accepts a board-size argument (or equivalent) and constructs a game at that size, with board()/available_moves()/etc. all correctly shaped for it.

Second slice of R-3. Depends on R-27 existing first. Complexity: small-to-medium -- mostly plumbing a new constructor argument through once the Rust side supports it.

### R-29 — Confirm agent-side code adapts to a configurable board size
- status: specified
- covers: [G-3]
- supersedes: [R-3]
- refs: [R-28]
- acceptance: action_space.py, heuristic.py, alphazero.py (SternhalmaZero's board_size/num_actions) and mcts.py all work correctly against a reduced-size game, verified by re-running their existing test suites (or size-parametrized variants) at a reduced size.

Third slice of R-3. Depends on R-28. Complexity: small -- action_space.py and heuristic.py already derive their board-size-dependent constants (NUM_CELLS, goal regions) at runtime from a fresh Game rather than hardcoding them, so this slice may turn out to be pure verification rather than new code. alphazero.py's SternhalmaZero construction (board_size, num_actions) already takes these as constructor arguments, so no change expected there either -- but confirm, don't assume.

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

### M-1 — Preparation: dedupe game rules, harden and benchmark the engine, fix small bugs
- status: done
- covers: [R-11, R-12, R-7, R-8, R-9]

From DIRECTIONS.md's Preparation section. Groups: remove the agent's duplicate Python rules (R-6, implementing D-2), add robust/property test coverage and a throughput benchmark to sternhalma-game (R-7, R-9), and fix the server's silent-drop of invalid client requests (R-8).

Updated after R-6 was decomposed into R-11 (packaging, done) and R-12 (the migration itself, outstanding) -- M-1 isn't done until R-12 lands too.

### M-2 — Learning: implement the AlphaZero-compatible training architecture
- status: planned
- covers: [R-18, R-19, R-20, R-21, R-22, R-23]

From DIRECTIONS.md's Learning section. R-5 is the whole of this milestone: MCTS-guided self-play wiring SternhalmaZero into actual move selection and training, which R-1/R-2/R-3 then refine.

Updated after R-5 was decomposed into R-18..R-23 (a sequenced chain: action encoding, MCTS search, self-play generation, replay buffer, training step, main.py wiring). R-1/R-24/R-25/R-26 (formerly folded under R-2) refine this milestone once it lands, but aren't required for it to count as done.

### M-3 — Improvement: real-world self-play benchmarking
- status: planned
- covers: [G-6, R-10]

From DIRECTIONS.md's Improvement section. Checkpoint-gating evaluation (G-6, R-10) as the more rigorous benchmark beyond G-3's random-baseline win rate.

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
- 2026-09-15 — R-7 status: specified -> specified
- 2026-09-15 — added R-9: Benchmark sternhalma-game's core operations for self-play throughput
- 2026-09-15 — added G-6: AlphaZero agent passes checkpoint-gating evaluation against its own prior best
- 2026-09-15 — added R-10: Implement checkpoint-gating evaluation harness for self-play training
- 2026-09-15 — added M-1: Preparation: dedupe game rules, harden and benchmark the engine, fix small bugs
- 2026-09-15 — added M-2: Learning: implement the AlphaZero-compatible training architecture
- 2026-09-15 — added M-3: Improvement: real-world self-play benchmarking
- 2026-09-15 — R-7 status: specified -> implemented
- 2026-09-15 — R-9 status: specified -> implemented
- 2026-09-15 — R-8 status: specified -> implemented
- 2026-09-15 — R-6 status: specified -> superseded
- 2026-09-15 — added R-11: Package sternhalma-python as an installable Python module and wire it as a uv dependency of sternhalma-agent
- 2026-09-15 — added R-12: Migrate sternhalma-agent's board-state tracking onto sternhalma_rs bindings
- 2026-09-15 — R-12 refs: ∅ -> [R-11]
- 2026-09-15 — R-11 status: specified -> implemented
- 2026-09-15 — M-1 covers: [R-6, R-7, R-8, R-9] -> [R-11,R-12,R-7,R-8,R-9]
- 2026-09-15 — added R-13: Fix sternhalma-python's clippy and rustfmt violations
- 2026-09-15 — added R-14: Fix sternhalma-agent's pytest collection failure
- 2026-09-15 — added R-15: Reject length-1 Hops paths in sternhalma-game's validate_movement
- 2026-09-15 — R-13 status: specified -> implemented
- 2026-09-15 — R-14 status: specified -> implemented
- 2026-09-15 — R-15 status: specified -> implemented
- 2026-09-15 — R-4 status: specified -> superseded
- 2026-09-15 — added R-16: Add a Lobby that spawns an independent Server per match
- 2026-09-15 — added R-17: Route session reconnection across concurrent games
- 2026-09-15 — R-16 status: specified -> implemented
- 2026-09-16 — R-12 status: specified -> implemented
- 2026-09-16 — R-12 refs: [R-11] -> [R-11]
- 2026-09-16 — M-1 status: planned -> done
- 2026-09-16 — R-5 status: specified -> superseded
- 2026-09-16 — added R-18: Define a fixed action encoding for the policy head and translate to/from the server's move list
- 2026-09-16 — added R-19: Implement MCTS search using SternhalmaZero's policy/value outputs
- 2026-09-16 — added R-20: Implement self-play game generation
- 2026-09-16 — added R-21: Implement a replay buffer for self-play training data
- 2026-09-16 — added R-22: Implement the training step with target-network updates
- 2026-09-16 — added R-23: Wire main.py --train to run the full self-play/train loop
- 2026-09-16 — R-19 refs: ∅ -> [R-18]
- 2026-09-16 — R-20 refs: ∅ -> [R-19]
- 2026-09-16 — R-21 refs: ∅ -> [R-20]
- 2026-09-16 — R-22 refs: ∅ -> [R-21]
- 2026-09-16 — R-23 refs: ∅ -> [R-18,R-19,R-20,R-21,R-22]
- 2026-09-16 — R-1 refs: [R-5] -> [R-19]
- 2026-09-16 — R-10 refs: [R-5] -> [R-23]
- 2026-09-16 — R-2 status: specified -> superseded
- 2026-09-16 — added R-24: Log training loss at each training step
- 2026-09-16 — added R-25: Test replay buffer stores and samples transitions correctly
- 2026-09-16 — added R-26: Test target-network sync schedule
- 2026-09-16 — M-2 covers: [R-5] -> [R-18,R-19,R-20,R-21,R-22,R-23]
- 2026-09-16 — R-3 refs: [R-5] -> [R-23]
- 2026-09-16 — R-9 refs: [R-5, R-7] -> [R-20,R-23,R-7]
- 2026-09-16 — R-18 status: specified -> implemented
- 2026-09-16 — R-19 status: specified -> implemented
- 2026-09-16 — R-1 status: specified -> implemented
- 2026-09-16 — R-3 status: specified -> superseded
- 2026-09-16 — added R-27: Make sternhalma-game's board size configurable instead of compile-time-fixed
- 2026-09-16 — added R-28: Expose configurable board size through sternhalma-python's bindings
- 2026-09-16 — added R-29: Confirm agent-side code adapts to a configurable board size
- 2026-09-16 — R-17 status: specified -> specified
- 2026-09-16 — R-20 status: specified -> specified
- 2026-09-16 — R-21 status: specified -> specified
- 2026-09-16 — R-22 status: specified -> specified
- 2026-09-16 — R-23 status: specified -> specified
- 2026-09-16 — R-24 status: specified -> specified
- 2026-09-16 — R-25 status: specified -> specified
- 2026-09-16 — R-26 status: specified -> specified
- 2026-09-16 — R-10 status: specified -> specified
- 2026-09-16 — R-17 status: specified -> implemented
- 2026-09-16 — R-21 status: specified -> implemented
