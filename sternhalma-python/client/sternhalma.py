from typing import Any
import numpy as np  # type: ignore
import sternhalma_rs  # type: ignore

# Type aliases for clarity
Move = tuple[tuple[int, int], tuple[int, int]]
Scores = tuple[int, int]
BoardState = Any  # np.ndarray is not fully typed without external stubs in some environments

class SternhalmaGame:
    """
    A safe, typed Python wrapper around the sternhalma_rs game bindings.
    """
    
    def __init__(self) -> None:
        """Initialize a new 2-player Sternhalma (Chinese Checkers) game."""
        self._game: Any = sternhalma_rs.Game()
        
    @property
    def current_player(self) -> int:
        """
        Get the currently active player.
        Returns:
            1 for Player 1
           -1 for Player 2
            0 if the game is finished
        """
        return self._game.player()
        
    @property
    def is_finished(self) -> bool:
        """Check if the game has concluded."""
        return self.current_player == 0
        
    @property
    def winner(self) -> int:
        """
        Get the winning player.
        Returns:
            1 for Player 1
           -1 for Player 2
            0 if there is no winner yet
        """
        return self._game.winner()
        
    @property
    def turns(self) -> int:
        """Get the total number of turns played."""
        return self._game.turns()
        
    @property
    def scores(self) -> Scores:
        """
        Get the current scores.
        Returns:
            A tuple in the format (Player 1 Score, Player 2 Score).
        """
        return self._game.scores()
        
    @property
    def history(self) -> list[Move]:
        """
        Get the history of all movements made in the game.
        Returns:
            A list of movements where each movement is a tuple of coordinates: 
            ((from_x, from_y), (to_x, to_y)).
        """
        return self._game.history()
        
    @property
    def board(self) -> BoardState:
        """
        Get the current board state as a tensor mask.
        Returns:
            A float32 numpy array of shape (3, 17, 17).
            Channel 0: Current player's pieces (1.0 for present, 0.0 otherwise)
            Channel 1: Opponent player's pieces (1.0 for present, 0.0 otherwise)
            Channel 2: Board mask (1.0 for valid positions, 0.0 otherwise)
        """
        return self._game.board()
        
    @property
    def available_moves(self) -> list[Move]:
        """
        Get all legal available moves for the currently active player.
        Returns:
            A list of moves, each formatted as ((from_x, from_y), (to_x, to_y)).
        """
        return self._game.available_moves()
        
    def apply_movement(self, move: Move) -> None:
        """
        Applies a movement for the currently active player.
        Validates the movement against the game rules.
        
        Args:
            move: The move to apply, formatted as ((from_x, from_y), (to_x, to_y)).
            
        Raises:
            ValueError: If the move is invalid or not allowed.
        """
        from_idx, to_idx = move
        self._game.apply_movement(from_idx, to_idx)
        
    def apply_movement_unchecked(self, move: Move) -> None:
        """
        Applies a movement directly without validation overhead.
        Use with caution, preferably only with moves retrieved directly from `available_moves`.
        
        Args:
            move: The move to apply, formatted as ((from_x, from_y), (to_x, to_y)).
        """
        from_idx, to_idx = move
        self._game.apply_movement_unchecked(from_idx, to_idx)

def print_board(game: SternhalmaGame) -> None:
    """
    Prints the board state to the terminal using the same style as the Rust implementation.
    """
    board = game.board
    
    # In the Rust binding, Channel 0 is always the "current player" (or winner if finished),
    # and Channel 1 is the "opponent".
    # We resolve which channel corresponds to Player 1 (🟣) and Player 2 (🟤).
    if not game.is_finished:
        # If the game is ongoing, the active player is channel 0.
        p1_channel = 0 if game.current_player == 1 else 1
        p2_channel = 1 if game.current_player == 1 else 0
    else:
        # If the game is finished, the winner is channel 0.
        # If there's no winner in python (e.g. forced exit), it defaults to evaluating
        # whatever internal state Rust exposes, which typically defaults to Player 1 if unfinished.
        p1_channel = 0 if game.winner == 1 else 1
        p2_channel = 1 if game.winner == 1 else 0

    BOARD_LENGTH = 17
    
    for i in range(BOARD_LENGTH):
        # Indent each row by `i` spaces to form the rhombus/hexagonal grid projection
        line = " " * i
        for j in range(BOARD_LENGTH):
            # Check if position is valid (Channel 2 is the board mask)
            is_valid = board[2, i, j] > 0.5
            
            if not is_valid:
                line += "   "
            else:
                is_p1 = board[p1_channel, i, j] > 0.5
                is_p2 = board[p2_channel, i, j] > 0.5
                
                if is_p1:
                    line += "🟣 "
                elif is_p2:
                    line += "🟤 "
                else:
                    line += "⚫ "
        print(line)

