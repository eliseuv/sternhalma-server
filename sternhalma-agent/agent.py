import logging
from abc import ABC, abstractmethod
from typing import final, override

import numpy as np
import sternhalma_rs
from numpy.typing import NDArray

from client.client import Client
from client.protocol import (
    ClientMessageChoice,
    GameResult,
    ServerMessage,
    ServerMessageDisconnect,
    ServerMessageGameFinished,
    ServerMessageMovement,
    ServerMessageTurn,
)


class Agent(ABC):
    def __init__(self):
        # Board state, mirrored locally via the Rust bindings (sternhalma_rs).
        # sternhalma_rs.Game always starts assuming its own Player 1 moves
        # first -- true for a real Player 1 client, but not for a real
        # Player 2 client (whose opponent, i.e. the real Player 1, moves
        # first). Mirroring with the validating apply_movement() would then
        # reject that first move as out of turn, even though the server's
        # relative-coordinate protocol (every client sees itself as "Player
        # 1") already guarantees the piece positions line up correctly.
        # apply_movement_unchecked() only updates positions, matching this
        # mirror's actual job -- feeding from_state() a board tensor -- and
        # sidesteps that validation entirely.
        #
        # Known limitation: this means self.board's own turn/score
        # bookkeeping (player(), turns(), scores()) is not reliable ground
        # truth for a real Player 2 client -- only its board() tensor is.
        # Nothing here reads the former; decide_movement always gets its
        # move list from the server's own (already-relative) Turn message.
        self.board: sternhalma_rs.Game = sternhalma_rs.Game()

    async def play(self, client: Client) -> GameResult:
        logging.info("Agent started playing...")
        while True:
            match await client.receive_message():
                case ServerMessageTurn(movements):
                    logging.debug("It's my turn")
                    movement_index: int = self.decide_movement(movements)
                    logging.debug(f"Chosen movement index: {movement_index}")
                    await client.send_message(ClientMessageChoice(movement_index))

                case ServerMessageMovement(player, indices):
                    logging.debug(f"Player {player} made move {indices}")
                    from_idx, to_idx = indices
                    self.board.apply_movement_unchecked(
                        (int(from_idx[0]), int(from_idx[1])),
                        (int(to_idx[0]), int(to_idx[1])),
                    )

                case ServerMessageGameFinished(result):
                    return result

                case ServerMessageDisconnect():
                    logging.error("Disconnection signal received mid game")
                    raise ConnectionAbortedError

                case ServerMessage() as unhandled:
                    logging.warning(f"Unhandled server message: {unhandled}")

    def prepare_training(self):
        self.nn: None = None

    @abstractmethod
    def decide_movement(self, movements: NDArray[np.int_]) -> int:
        pass


@final
class AgentConstant(Agent):
    @override
    def decide_movement(self, movements: NDArray[np.int_]) -> int:
        return 0


@final
class AgentBrownian(Agent):
    @override
    def decide_movement(self, movements: NDArray[np.int_]) -> int:
        return np.random.randint(0, len(movements))


@final
class AgentDQN(Agent):
    @override
    def __init__(self):
        # Parent constructor
        super().__init__()

        # Neural network
        self.nn = None

    @override
    def decide_movement(self, movements: NDArray[np.int_]) -> int:
        return 0
