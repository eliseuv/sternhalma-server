//! # Sternhalma Gam
//!
//! This crate contains the core game logic for Sternhalma (Chinese Checkers).
//! It defines the game state, rules, board representation, and victory conditions.
//!
//! ## Key Components
//! - [`Game`]: The main struct representing the game state.
//! - [`GameStatus`]: Enum representing the current state of the game (Playing, Finished).
//! - [`GameResult`]: Enum representing the final outcome of a game.
//! - [`board`]: Submodule containing board-related logic (grid, movement, players).
//! - [`timing`]: Submodule for game timing and statistics.

use std::fmt::{Debug, Display};

use anyhow::Result;

use board::{Board, HexIdx, goal_indices};
use movement::{Movement, MovementError, MovementIndices};
use player::{PLAYER_COUNT, Player};

/// Player pieces
pub mod player;

/// Hexagonal Sternhalma board
pub mod board;

/// Movements on the board
pub mod movement;

use serde::{Deserialize, Serialize};

pub type Scores = [usize; PLAYER_COUNT];

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case", tag = "type")]
pub enum GameResult {
    Finished {
        winner: Player,
        total_turns: usize,
        scores: Scores,
    },
    MaxTurns {
        total_turns: usize,
        scores: Scores,
    },
}

#[derive(Debug, Clone, Copy)]
pub enum GameStatus {
    /// Game is ongoing
    Playing {
        player: Player,
        turns: usize,
        scores: [usize; PLAYER_COUNT],
    },
    /// Game finished
    Finished {
        winner: Player,
        total_turns: usize,
        scores: [usize; PLAYER_COUNT],
    },
}

impl GameStatus {
    /// Get number of turns
    pub fn turns(&self) -> usize {
        match self {
            GameStatus::Playing { turns, .. } => *turns,
            GameStatus::Finished { total_turns, .. } => *total_turns,
        }
    }

    /// Get scores
    pub fn scores(&self) -> [usize; PLAYER_COUNT] {
        match self {
            GameStatus::Playing { scores, .. } => *scores,
            GameStatus::Finished { scores, .. } => *scores,
        }
    }
}

impl Display for GameStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            GameStatus::Playing {
                player,
                turns,
                scores,
            } => {
                write!(f, "Playing: {player} | Turn: {turns} | Scores: {scores:?}")
            }
            GameStatus::Finished {
                winner,
                total_turns,
                scores,
            } => {
                write!(
                    f,
                    "Winner: {winner} | Total turns: {total_turns} | Scores: {scores:?}"
                )
            }
        }
    }
}

#[derive(Debug)]
pub struct Game {
    /// Board state
    board: Board<Player>,
    /// Game status
    status: GameStatus,
    /// Game history
    history: Vec<MovementIndices>,
}

impl Display for Game {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "{board}{status}",
            board = self.board,
            status = self.status
        )
    }
}

impl Game {
    pub fn new() -> Self {
        Self {
            board: Board::new(),
            status: GameStatus::Playing {
                player: Player::Player1,
                turns: 0,
                scores: [0; PLAYER_COUNT],
            },
            history: Vec::with_capacity(128),
        }
    }

    pub fn board(&self) -> &Board<Player> {
        &self.board
    }

    pub fn status(&self) -> GameStatus {
        self.status
    }

    pub fn history(&self) -> &[[HexIdx; 2]] {
        &self.history
    }

    pub fn history_bytes(&self) -> usize {
        self.history.capacity() * std::mem::size_of::<[HexIdx; 2]>()
    }
}

impl Default for Game {
    fn default() -> Self {
        Self::new()
    }
}

/// Error that can occur during game operations
#[derive(Debug, Clone, Copy)]
pub enum GameError {
    /// Movement error
    Movement(MovementError),
    /// Movement made out of turn
    OutOfTurn,
    /// Movement made after the game is finished
    GameFinished,
}

impl Game {
    /// Update the game status based on current state of the game
    fn next_status(&self, movement: &MovementIndices) -> GameStatus {
        match self.status {
            // Game finished is absorbing state
            GameStatus::Finished { .. } => {
                log::warn!("Attempting to update state of finished game");
                self.status
            }
            // Game is ongoing
            GameStatus::Playing {
                player,
                turns,
                mut scores,
            } => {
                // Update game scores
                let goal = goal_indices(&player);
                if goal.contains(&movement[0]) {
                    scores[player as usize - 1] -= 1;
                }
                if goal.contains(&movement[1]) {
                    scores[player as usize - 1] += 1;
                }

                // Check winning conditions
                if let Some(player) = self.board.check_winner() {
                    GameStatus::Finished {
                        winner: player,
                        total_turns: turns + 1,
                        scores,
                    }
                } else {
                    // Game is still ongoing, switch to the opponent
                    GameStatus::Playing {
                        player: player.opponent(),
                        turns: turns + 1,
                        scores,
                    }
                }
            }
        }
    }

    /// Iterate over the available movements for the current turn's player
    pub fn iter_available_moves(&self) -> impl Iterator<Item = Movement> {
        match &self.status {
            GameStatus::Finished { .. } => {
                panic!("Cannot iterate over available moves of finished game")
            }
            GameStatus::Playing { player, .. } => self.board.iter_player_movements(player),
        }
    }

    /// Apply movement to the current game
    pub fn apply_movement(&mut self, movement: &Movement) -> Result<GameStatus, GameError> {
        match self.status {
            GameStatus::Finished { .. } => Err(GameError::GameFinished),
            GameStatus::Playing {
                player: current_player,
                ..
            } => {
                // Validate movement
                let (movement, player) = self
                    .board
                    .validate_movement(movement)
                    .map_err(GameError::Movement)?;

                // Check if the movement is made by the current player
                if player != &current_player {
                    return Err(GameError::OutOfTurn);
                }

                // Apply the movement to the board
                unsafe {
                    self.apply_movement_unchecked(&movement.into());
                }

                Ok(self.status)
            }
        }
    }

    /// Apply movement in the game without validating it or the player
    ///
    /// # Safety
    ///
    /// It is advised have validated the movement on the current board and check the player's turn beforehand
    pub unsafe fn apply_movement_unchecked(&mut self, movement: &MovementIndices) -> GameStatus {
        // Apply movement on the board
        unsafe {
            self.board.apply_movement_unchecked(movement);
        }

        // Update game history
        self.history.push(*movement);

        // Update game status
        self.status = self.next_status(movement);

        self.status
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use board::goal_indices;

    #[test]
    fn new_game_starts_player1_at_turn_zero() {
        let game = Game::new();
        assert!(matches!(
            game.status(),
            GameStatus::Playing {
                player: Player::Player1,
                turns: 0,
                scores: [0, 0],
            }
        ));
    }

    #[test]
    fn apply_movement_switches_player_and_advances_turns() {
        let mut game = Game::new();
        let movement = game.iter_available_moves().next().unwrap();

        let status = game.apply_movement(&movement).unwrap();
        assert!(matches!(
            status,
            GameStatus::Playing {
                player: Player::Player2,
                turns: 1,
                ..
            }
        ));
        assert_eq!(game.history().len(), 1);
    }

    #[test]
    fn apply_movement_out_of_turn_is_rejected() {
        let mut game = Game::new();
        // Player 2's [4, 8] has an empty neighbor at [4, 7] even from the
        // starting position, so this is a legal move for Player 2 -- just
        // not on Player 1's turn.
        let out_of_turn = Movement::Move {
            from: [4, 8],
            to: [4, 7],
        };
        assert!(matches!(
            game.apply_movement(&out_of_turn),
            Err(GameError::OutOfTurn)
        ));
    }

    #[test]
    fn apply_movement_after_game_finished_is_rejected() {
        // Player 1's goal is Player 2's starting triangle. Fill all but one
        // goal cell, and stage the last piece one step away from it.
        let goal = goal_indices(&Player::Player1);
        let mut board = Board::empty();
        board
            .place_pieces(&goal[..goal.len() - 1], Player::Player1)
            .unwrap();
        board.set_piece([4, 7], Player::Player1).unwrap();

        let mut game = Game {
            board,
            status: GameStatus::Playing {
                player: Player::Player1,
                turns: 0,
                scores: [14, 0],
            },
            history: Vec::new(),
        };

        let winning_move = Movement::Move {
            from: [4, 7],
            to: goal[goal.len() - 1],
        };
        let status = game.apply_movement(&winning_move).unwrap();
        assert!(matches!(
            status,
            GameStatus::Finished {
                winner: Player::Player1,
                total_turns: 1,
                scores: [15, 0],
            }
        ));

        // Any further movement is rejected outright, regardless of content.
        assert!(matches!(
            game.apply_movement(&winning_move),
            Err(GameError::GameFinished)
        ));
    }
}
