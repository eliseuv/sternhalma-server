# Sternhalma Agent

This project aims to implement the AlphaZero algorithm from scratch to master the game of **Sternhalma** (commonly known as Chinese Checkers).

The agent is designed to interact with a Sternhalma server using a custom CBOR-based protocol.

## Project Goal

The primary objective is to build a reinforcement learning agent capable of achieving high-level play in Sternhalma without human knowledge, using:

- **Monte Carlo Tree Search (MCTS)** for lookahead planning.
- **Deep Neural Networks (ResNet)** for evaluating board states and predicting move policies.
- **Self-Play** for iterative improvement.

## Setup & Usage

This project uses [`uv`](https://github.com/astral-sh/uv) for dependency management.

### Installation

```bash
# Install dependencies
uv sync
```

This includes `sternhalma-rs` (`../sternhalma-python`), the Rust game engine's Python bindings, built from source via `maturin` as part of `uv sync` -- requires the `cargo`/`rustc`/`maturin` packages in this project's `flake.nix` devshell.

### Running Tests

To verify the installation and current functionality:

```bash
uv run pytest
```

### Running the Agent

This agent requires a running instance of the Sternhalma server. You can find the server implementation and setup instructions here: [sternhalma-server](https://github.com/eliseuv/sternhalma-server).

To start the agent and connect to a server:

```bash
uv run main.py --host 127.0.0.1 --port 8080
```

**Arguments:**

- `--host`: The hostname or IP address of the game server (default: `127.0.0.1`).
- `--port`: The port number the server is listening on (default: `8080`).

### Training

Training runs entirely offline via self-play (no server needed):

```bash
uv run main.py --train --iterations 100 --checkpoint-dir checkpoints --device cuda
```

Each iteration plays `GAMES_PER_ITERATION` self-play games via MCTS, buffers their examples, runs `TRAIN_STEPS_PER_ITERATION` training steps once the buffer holds enough for a batch, and saves a checkpoint every `CHECKPOINT_INTERVAL` iterations. These (and `NUM_SIMULATIONS`, `BATCH_SIZE`, `TARGET_SYNC_INTERVAL`, `BUFFER_CAPACITY`) are module-level constants in `main.py`, not yet exposed as their own CLI flags.

**Arguments:**

- `--iterations`: Number of self-play/train iterations to run (default: `100`).
- `--checkpoint-dir`: Directory to save model checkpoints to (default: `checkpoints`).
- `--device`: Device to run the network on (default: `cuda`).

## Project Structure

- `sternhalma.py`: `Player` and `Scores` types shared by the protocol layer. Board state and move logic used to be reimplemented here too; that's now `sternhalma_rs` (the `sternhalma-game` Rust engine's Python bindings) instead.
- `action_space.py`: Translates between the server's variable-length legal-move list and `SternhalmaZero`'s fixed 121x121 (source, target) policy action space.
- `mcts.py`: Monte Carlo Tree Search over `SternhalmaZero`'s policy/value outputs.
- `heuristic.py`: A distance-to-goal potential function biasing MCTS priors, most useful before the network is trained.
- `replay_buffer.py`: Bounded, oldest-evicted store of self-play training examples, with random-sampling.
- `self_play.py`: Plays a complete game via MCTS against itself, recording a training example per turn.
- `training.py`: The training step -- policy + value loss against replay buffer samples, with a periodically-synced target network.
- `alphazero.py`: Neural network architecture and tensor conversions.
- `client.py`: Async TCP client for connecting to the game server.
- `protocol.py`: Protocol message definitions (Server/Client messages).
- `agent.py`: Abstract agent definition and basic implementations (Random, Constant).

## Current Progress

- **Core Game Logic**: Provided by `sternhalma_rs`, not reimplemented here. `Agent` mirrors board state locally via a `sternhalma_rs.Game`, applied unchecked (see `agent.py`'s comment) since the engine's own turn validation assumes its Player 1 always moves first, which isn't true from a real Player 2 client's perspective.
- **Networking**: connection handling and protocol implementation in `client.py` and `protocol.py`. Supports asynchronous communication with the game server.
- **Neural Network**: Basic AlphaZero-style architecture (ResNet backbone, Policy Head, Value Head) implemented using PyTorch in `alphazero.py`.
- **State Representation**: `from_state` converts a `sternhalma_rs.Game` into a canonical (1, 3, 17, 17) tensor, correcting for the bindings' turn-relative channel order so channel 0 is always "me" regardless of whose turn it locally is.
- **Action Space**: `action_space.py` gives `SternhalmaZero`'s policy head a fixed 121x121 (source, target) action space, and translates to/from the server's per-turn legal-move list (masking illegal actions and renormalizing).
- **MCTS**: `mcts.py`'s `search`/`search_with_policy` run UCB-guided tree search using `SternhalmaZero`'s policy priors and value estimates; `search_with_policy` also returns the visit-count policy target self-play records. Not yet wired into `Agent.decide_movement` (no `AgentMCTS` yet).
- **Heuristic**: `heuristic.py`'s `potential` (a symmetric, current-mover-relative distance-to-goal score) biases MCTS priors toward stronger-looking moves via `mcts.search`'s `heuristic_weight`, on by default.
- **Self-Play**: `self_play.py`'s `play_self_play_game` plays a full game via MCTS against itself and returns a training `Example` per turn, outcome backfilled from the winner once the game ends. A game that hits its turn cap without finishing contributes nothing -- verified manually that untrained/weak play can take far more than 150-500 turns to finish naturally, so the current `DEFAULT_MAX_TURNS=300` is a placeholder, not calibrated.
- **Replay Buffer**: `replay_buffer.py`'s `ReplayBuffer` stores `Example(state, policy, outcome)` records (the same type `self_play.py` produces) with a bounded capacity (oldest evicted first) and samples training batches without replacement.
- **Training**: `training.py`'s `Trainer` samples a replay-buffer batch, computes the AlphaZero loss (soft-label policy cross-entropy + value MSE) against its evaluation network, takes an optimizer step, and syncs a target network from it every `target_sync_interval` steps. Each step logs its loss and the policy/value components, so progress is observable without instrumenting code.
- **Training Loop**: `main.py --train` (see `train()`) runs the full loop -- self-play games each iteration, buffered, trained on once there's enough for a batch, checkpointed on a schedule. No longer a no-op. This closes M-2 (Learning): the AlphaZero-compatible training architecture exists end-to-end, though untrained and with several constants (game count, simulation count, batch size, etc.) still hardcoded rather than tuned or exposed as flags.
- **Testing**: `tests/test_integration.py` covers the client-server handshake and game flow; `tests/test_alphazero.py` covers `from_state`'s channel canonicalization; `tests/test_action_space.py` covers the action encoding round-trip and masking; `tests/test_mcts.py` covers game-state cloning and that search/search_with_policy return legal, correctly-shaped results; `tests/test_heuristic.py` covers the potential function and its MCTS bias; `tests/test_self_play.py` covers outcome backfilling and the turn-cap early exit; `tests/test_replay_buffer.py` covers exact push/sample round-tripping, capacity eviction, batch-size and without-replacement sampling, and the over-request error; `tests/test_training.py` covers that a training step returns a finite loss, actually updates the network, and logs the loss breakdown; `tests/test_main.py` is a wiring smoke test confirming the full loop runs and checkpoints.
- **Dependency Management**: Project dependencies managed via `uv` and `pyproject.toml`, including `sternhalma-rs` as a local path dependency built via `maturin`.
