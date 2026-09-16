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

## Project Structure

- `sternhalma.py`: `Player` and `Scores` types shared by the protocol layer. Board state and move logic used to be reimplemented here too; that's now `sternhalma_rs` (the `sternhalma-game` Rust engine's Python bindings) instead.
- `alphazero.py`: Neural network architecture and tensor conversions.
- `client.py`: Async TCP client for connecting to the game server.
- `protocol.py`: Protocol message definitions (Server/Client messages).
- `agent.py`: Abstract agent definition and basic implementations (Random, Constant).

## Current Progress

- **Core Game Logic**: Provided by `sternhalma_rs`, not reimplemented here. `Agent` mirrors board state locally via a `sternhalma_rs.Game`, applied unchecked (see `agent.py`'s comment) since the engine's own turn validation assumes its Player 1 always moves first, which isn't true from a real Player 2 client's perspective.
- **Networking**: connection handling and protocol implementation in `client.py` and `protocol.py`. Supports asynchronous communication with the game server.
- **Neural Network**: Basic AlphaZero-style architecture (ResNet backbone, Policy Head, Value Head) implemented using PyTorch in `alphazero.py`.
- **State Representation**: `from_state` converts a `sternhalma_rs.Game` into a canonical (1, 3, 17, 17) tensor, correcting for the bindings' turn-relative channel order so channel 0 is always "me" regardless of whose turn it locally is.
- **Testing**: `tests/test_integration.py` covers the client-server handshake and game flow; `tests/test_alphazero.py` covers `from_state`'s channel canonicalization.
- **Dependency Management**: Project dependencies managed via `uv` and `pyproject.toml`, including `sternhalma-rs` as a local path dependency built via `maturin`.
