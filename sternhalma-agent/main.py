import argparse
import asyncio
import logging
from pathlib import Path

import torch as T

from action_space import NUM_ACTIONS
from agent import Agent, AgentBrownian
from alphazero import SternhalmaZero
from client.client import Client
from client.protocol import GameResult, GameResultFinished, GameResultMaxTurns
from replay_buffer import ReplayBuffer
from self_play import play_self_play_game
from training import Trainer
from utils import printer

# Training loop defaults -- not yet exposed as CLI flags, tune here.
GAMES_PER_ITERATION = 5
NUM_SIMULATIONS = 25
BATCH_SIZE = 64
TRAIN_STEPS_PER_ITERATION = 10
TARGET_SYNC_INTERVAL = 20
BUFFER_CAPACITY = 10_000
CHECKPOINT_INTERVAL = 10


# Set up logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format="[{asctime} {levelname}] {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Set up command-line argument parser
parser = argparse.ArgumentParser(
    prog="SternhalmaAgent",
    description="Sternhalma player agent",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
# Game server socket
_ = parser.add_argument(
    "--host",
    type=str,
    default="127.0.0.1",
    help="Game server host",
)
_ = parser.add_argument(
    "--port",
    type=int,
    default=8080,
    help="Game server port",
)
# Training mode
_ = parser.add_argument(
    "--train",
    action="store_true",
    dest="training_mode",
    help="Enable agent training mode",
)
_ = parser.add_argument(
    "--iterations",
    type=int,
    default=100,
    help="Number of self-play/train iterations to run (training mode only)",
)
_ = parser.add_argument(
    "--checkpoint-dir",
    type=Path,
    default=Path("checkpoints"),
    help="Directory to save model checkpoints to (training mode only)",
)
_ = parser.add_argument(
    "--device",
    type=str,
    default="cuda",
    help="Device to run the network on (training mode only)",
)


async def train(num_iterations: int, checkpoint_dir: Path, device: str) -> None:
    """Runs the self-play / train loop: each iteration generates self-play
    games, buffers them, runs training steps on the buffer, and -- every
    CHECKPOINT_INTERVAL iterations -- saves the evaluation network's
    weights.
    """
    network = SternhalmaZero(board_size=17, num_actions=NUM_ACTIONS)
    trainer = Trainer(network, target_sync_interval=TARGET_SYNC_INTERVAL, device=device)
    buffer = ReplayBuffer(capacity=BUFFER_CAPACITY)

    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    for iteration in range(1, num_iterations + 1):
        for _ in range(GAMES_PER_ITERATION):
            examples = play_self_play_game(
                trainer.network, NUM_SIMULATIONS, device=device
            )
            for example in examples:
                buffer.push(example)
        logging.info(
            f"Iteration {iteration}: self-play done, buffer holds {len(buffer)} examples"
        )

        if len(buffer) >= BATCH_SIZE:
            for _ in range(TRAIN_STEPS_PER_ITERATION):
                trainer.train_step(buffer, BATCH_SIZE)
        else:
            logging.info(
                f"Iteration {iteration}: buffer too small ({len(buffer)} < "
                f"{BATCH_SIZE}), skipping training this iteration"
            )

        if iteration % CHECKPOINT_INTERVAL == 0:
            checkpoint_path = checkpoint_dir / f"checkpoint_{iteration}.pt"
            T.save(trainer.network.state_dict(), checkpoint_path)
            logging.info(f"Iteration {iteration}: saved checkpoint to {checkpoint_path}")


async def play(agent: Agent, client: Client):
    result = await agent.play(client)
    match result:
        case GameResultMaxTurns(total_turns, scores):
            logging.info(
                f"The game has reached its maximum number of turns {total_turns} with scores {scores}"
            )

        case GameResultFinished(winner, total_turns):
            logging.info(f"Game finished! Winner {winner} after {total_turns} turns")

        case GameResult():
            pass


async def main():
    # Parse command-line arguments
    args = parser.parse_args()
    logging.debug(f"Arguments: {printer.pformat(vars(args))}")

    # Training mode runs entirely offline via self-play (sternhalma_rs, no
    # network) -- it needs no server connection at all, so this branches
    # before ever spawning a Client, unlike network play below.
    if bool(args.training_mode):
        await train(
            num_iterations=int(args.iterations),
            checkpoint_dir=Path(args.checkpoint_dir),
            device=str(args.device),
        )
        return

    host = str(args.host)
    port = int(args.port)

    # Spawn client
    async with Client(host, port) as client:
        # Wait for player assignment from server
        await client.handshake()

        # Create agent
        agent = AgentBrownian()
        await play(agent, client)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Client stopped by user.")
