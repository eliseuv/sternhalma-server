# Sternhalma Game

Core game logic library for Sternhalma (Chinese Checkers) implemented in Rust.

## Overview

`sternhalma-game` provides the complete rule set, state management, and movement validation for the Sternhalma board game. It is designed to be robust and efficient, suitable for use in game servers, AI agents, or local applications.

## Features

- **Standard Board**: Implements the classic star-shaped board with 121 positions.
- **Rules Enforcement**: Validates moves including single adjacent steps and valid jump sequences.
- **State Management**: Tracks game status (Playing vs Finished), current turn, scores, and complete move history.
- **Efficient Representation**: Optimized internal representations for board state and move generation.
- **Serialization**: Full support for `serde` serialization and deserialization, making it easy to save states or transmit them over a network.

## Usage

Add this crate to your dependencies:

```toml
[dependencies]
sternhalma-game = { version = "0.1.0" }
```

### Example

```rust
use sternhalma_game::{Game, GameStatus};

fn main() -> anyhow::Result<()> {
    // Initialize a new game
    let mut game = Game::new();

    // Check game status
    if let GameStatus::Playing { player, turns, .. } = game.status() {
        println!("Turn {}: Player {}", turns, player);
    }

    // Generate valid moves
    for movement in game.iter_available_moves() {
        println!("Valid move: {:?}", movement);
    }

    // Apply a move (example logic)
    // let result = game.apply_movement(&chosen_movement)?;

    Ok(())
}
```

## Testing & Benchmarks

Unit tests (`cargo test -p sternhalma-game`) cover board bounds and placement,
single-step and chain-jump movement, `validate_movement`'s error cases,
scoring, and win detection -- independent of `sternhalma-server`'s
integration tests, which only exercise this crate indirectly.

Throughput benchmarks (`cargo bench -p sternhalma-game`) measure move
generation (`Game::iter_available_moves`) and move application
(`Board::apply_movement_unchecked`) via `criterion`. No throughput target is
enforced yet -- self-play training doesn't exist yet either, and that's what
will determine what "fast enough" means.

## Modules

- **`board`**: Contains the `Board` struct, grid coordinates, and board initialization logic.
- **`movement`**: Handles move validation, jump logic, and `Movement` types.
- **`player`**: Defines player identities (`Player1`, `Player2`), colors, and utilities.

## Rules

The game is played on an hexagonal board in the shape of a six point star with 121 valid positions.

### Setup

Each player has 15 pieces and start on the opposite sides of the board. The pieces are represented by colored circles, one color for each player.

```text
   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠     󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   🔴
    󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠     󠀠󠀠󠀠󠀠   🔴 🔴
  󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠     🔴 🔴 🔴
   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠  🔴 🔴 🔴 🔴
   ⚫ ⚫ ⚫ ⚫ 🔴 🔴 🔴 🔴 🔴 ⚫ ⚫ ⚫ ⚫
  󠀠󠀠󠀠󠀠   ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫
   󠀠󠀠󠀠󠀠   ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫
       ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫
  󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫
   󠀠󠀠󠀠󠀠   ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫
    ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫
  ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫ ⚫
⚫ ⚫ ⚫ ⚫ 🔵 🔵 🔵 🔵 🔵 ⚫ ⚫ ⚫ ⚫
 󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   🔵 🔵 🔵 🔵
  󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   🔵 🔵 🔵
   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   🔵 🔵
    󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   󠀠󠀠󠀠󠀠   🔵
```

### Gameplay

1. The game is turn-based.
2. A player can move one piece per turn.
3. A piece can be moved to an adjacent empty position.
4. Alternatively, a piece can jump over an adjacent piece (of any color) into an empty spot immediately beyond it.
5. Multiple jumps (chain jumps) are allowed in a single turn if they are available.

### Goal

The goal of the game is to move all of your pieces into the triangle on the opposite side of the board (the opponent's starting area). The first player to achieve this wins.
