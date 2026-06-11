# Sternhalma Python Bindings

This crate serves as a wrapper for the Sternhalma game crate, allowing the core Rust logic to be used in Python. 

## Installation

To use this module locally, use `maturin` to build and install it into your active python environment:
```bash
pip install maturin
maturin develop
```

## Interface `sternhalma_rs.Game`

The primary interface exposed to Python is the `Game` class.

### Initialization

```python
import sternhalma_rs
game = sternhalma_rs.Game()
```
Creates a new 2-player Sternhalma (Chinese Checkers) game.

### Game State Inspection

* `game.player() -> int`
  * Gets the currently active player. 
  * Returns `1` for Player 1, `-1` for Player 2, and `0` if the game is finished.
* `game.winner() -> int`
  * Gets the winning player. 
  * Returns `1` for Player 1, `-1` for Player 2, and `0` if there is no winner yet.
* `game.turns() -> int`
  * Gets the total number of turns played.
* `game.scores() -> tuple[int, int]`
  * Gets the current scores of the players.
  * Returns a tuple in the format `(Player 1 Score, Player 2 Score)`.
* `game.history() -> list[tuple[tuple[int, int], tuple[int, int]]]`
  * Gets the history of all movements made in the game.
  * Returns a list of movements where each movement is represented as a tuple of coordinates: `((from_x, from_y), (to_x, to_y))`.
* `game.board() -> numpy.ndarray`
  * Gets the current board state as a tensor mask.
  * Returns a float32 numpy array of shape `(3, 17, 17)`.
    * Channel 0: Current player's pieces (1.0 for present, 0.0 otherwise)
    * Channel 1: Opponent player's pieces (1.0 for present, 0.0 otherwise)
    * Channel 2: Board mask (1.0 for valid positions, 0.0 otherwise)

### Moving Pieces

* `game.available_moves() -> list[tuple[tuple[int, int], tuple[int, int]]]`
  * Gets all legal available moves for the currently active player. 
  * Moves are returned as tuples of start and end indices: `((from_x, from_y), (to_x, to_y))`.
* `game.apply_movement(from_idx: tuple[int, int], to_idx: tuple[int, int]) -> None`
  * Applies a movement for the currently active player from an origin index to a target index.
  * Validates the movement against the game rules. Raises a `ValueError` if the move is invalid.
* `game.apply_movement_unchecked(from_idx: tuple[int, int], to_idx: tuple[int, int]) -> None`
  * Applies a movement directly without validation overhead. Use with caution (preferably with moves retrieved from `available_moves()`).
