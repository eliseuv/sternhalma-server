use numpy::PyArray3;
use pyo3::prelude::*;

// Sternhalma Game
#[pyclass]
pub struct Game {
    game: sternhalma_game::Game,
}

#[pymethods]
impl Game {
    /// Create a new 2 player game
    #[new]
    fn new() -> Self {
        Self {
            game: sternhalma_game::Game::new(),
        }
    }

    /// Get currently active player
    /// Returns 1 for Player 1, -1 for Player 2, and 0 for finished game
    fn player(&self) -> PyResult<i32> {
        match self.game.status() {
            sternhalma_game::GameStatus::Finished { .. } => Ok(0),
            sternhalma_game::GameStatus::Playing { player, .. } => Ok(match player {
                sternhalma_game::player::Player::Player1 => 1,
                sternhalma_game::player::Player::Player2 => -1,
            }),
        }
    }

    /// Get winner
    /// Returns 1 for Player 1, -1 for Player 2, and 0 for finished game
    fn winner(&self) -> PyResult<i32> {
        match self.game.status() {
            sternhalma_game::GameStatus::Finished { winner, .. } => Ok(match winner {
                sternhalma_game::player::Player::Player1 => 1,
                sternhalma_game::player::Player::Player2 => -1,
            }),
            sternhalma_game::GameStatus::Playing { .. } => Ok(0),
        }
    }

    /// Get number of turns
    fn turns(&self) -> PyResult<usize> {
        match self.game.status() {
            sternhalma_game::GameStatus::Finished { total_turns, .. } => Ok(total_turns),
            sternhalma_game::GameStatus::Playing { turns, .. } => Ok(turns),
        }
    }

    /// Get board state as tensor mask
    /// Shape: (3,17,17)
    /// Channel 0: Current player pieces
    /// Channel 1: Opponent player pieces
    /// Channel 2: Board mask (1 for valid positions, 0 otherwise)
    fn board<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyArray3<f32>>> {
        let (p1, p2) = match self.game.status() {
            sternhalma_game::GameStatus::Playing { player, .. } => (player, player.opponent()),
            sternhalma_game::GameStatus::Finished { winner, .. } => (winner, winner.opponent()),
        };

        let mut data = numpy::ndarray::Array3::<f32>::zeros((
            3,
            sternhalma_game::board::BOARD_LENGTH,
            sternhalma_game::board::BOARD_LENGTH,
        ));
        let board = self.game.board();

        for i in 0..sternhalma_game::board::BOARD_LENGTH {
            for j in 0..sternhalma_game::board::BOARD_LENGTH {
                match board[[i, j]] {
                    Some(Some(player)) => {
                        data[[2, i, j]] = 1.0;
                        if player == p1 {
                            data[[0, i, j]] = 1.0;
                        } else if player == p2 {
                            data[[1, i, j]] = 1.0;
                        }
                    }
                    Some(None) => {
                        data[[2, i, j]] = 1.0;
                    }
                    None => {}
                }
            }
        }

        Ok(PyArray3::from_array(py, &data))
    }
}

#[pymodule]
fn sternhalma_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Game>()?;

    Ok(())
}
