use pyo3::prelude::*;

// Player enum
#[pyclass]
pub struct Player {
    player: sternhalma_game::player::Player,
}

#[pymethods]
impl Player {
    #[new]
    fn new(player: u32) -> Self {
        Self {
            player: match player {
                1 => sternhalma_game::player::Player::Player1,
                2 => sternhalma_game::player::Player::Player2,
                _ => panic!("Invalid player"),
            },
        }
    }

    #[staticmethod]
    fn variants() -> PyResult<[Player; 2]> {
        Ok([
            Player {
                player: sternhalma_game::player::Player::Player1,
            },
            Player {
                player: sternhalma_game::player::Player::Player2,
            },
        ])
    }
}

// Board struct
#[pyclass]
pub struct Board {
    board: sternhalma_game::board::Board<sternhalma_game::player::Player>,
}

#[pymethods]
impl Board {
    #[new]
    fn new() -> Self {
        Self {
            board: sternhalma_game::board::Board::new(),
        }
    }
}

#[pymodule]
fn sternhalma_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Player>()?;
    m.add_class::<Board>()?;
    Ok(())
}
