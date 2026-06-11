import random
from typing import Any

from sternhalma import SternhalmaGame, Move, print_board

def main() -> None:
    print("Initializing Sternhalma game using safe wrapper...")
    game = SternhalmaGame()
    
    # Run the game loop
    max_turns: int = 50
    while not game.is_finished:
        if game.turns >= max_turns:
            print(f"\nReached max turns ({max_turns}) for testing. Stopping early.")
            break
            
        print(f"\n--- Turn {game.turns} ---")
        print(f"Current Player: {'Player 1' if game.current_player == 1 else 'Player 2'}")
        
        # Get scores
        scores = game.scores
        print(f"Scores -> Player 1: {scores[0]}, Player 2: {scores[1]}")
        
        # Print the board
        print_board(game)
        
        # Get available moves
        available_moves: list[Move] = game.available_moves
        if not available_moves:
            print("No available moves! Game over.")
            break
            
        print(f"Available moves: {len(available_moves)}")
        
        # Pick a random move
        chosen_move: Move = random.choice(available_moves)
        from_idx, to_idx = chosen_move
        print(f"Applying move from {from_idx} to {to_idx}")
        
        # Apply the selected movement
        game.apply_movement(chosen_move)

    # Game finished
    print("\n--- Game Finished! ---")
    print(f"Total turns: {game.turns}")
    
    winner: int = game.winner
    if winner == 1:
        print("Winner: Player 1")
    elif winner == -1:
        print("Winner: Player 2")
    else:
        print("Draw / No winner")
        
    final_scores = game.scores
    print(f"Final Scores -> Player 1: {final_scores[0]}, Player 2: {final_scores[1]}")
    
    history: list[Move] = game.history
    print(f"Total history length: {len(history)} moves")

if __name__ == '__main__':
    main()
