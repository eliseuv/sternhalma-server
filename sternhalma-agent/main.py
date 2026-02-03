import numpy as np
import sternhalma_rs


def main():
    print("Hello from sternhalma-agent!")
    game = sternhalma_rs.Game()
    print(f"Current player: {game.player()}")
    print(f"Winner: {game.winner()}")
    print(f"Turns: {game.turns()}")
    print(f"Board: {game.board()}")


if __name__ == "__main__":
    main()
