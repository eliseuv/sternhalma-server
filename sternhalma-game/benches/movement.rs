//! Throughput benchmarks for move generation and application.
//!
//! Self-play training (R-5) calls these in a tight loop millions of times per
//! iteration, so their cost is the actual bottleneck to size a throughput
//! target against (R-9) -- no target is asserted here, this just measures.

use std::hint::black_box;

use criterion::{BatchSize, Criterion, criterion_group, criterion_main};
use sternhalma_game::Game;
use sternhalma_game::board::Board;
use sternhalma_game::player::Player;

fn bench_iter_available_moves(c: &mut Criterion) {
    let game = Game::new();
    c.bench_function("game_iter_available_moves", |b| {
        b.iter(|| black_box(game.iter_available_moves().count()));
    });
}

fn bench_apply_movement_unchecked(c: &mut Criterion) {
    // [4, 8] (a Player 2 starting position) has an empty neighbor at [4, 7]
    // even on a fresh board, giving a single-step move usable every batch
    // without needing to compute available moves first.
    c.bench_function("board_apply_movement_unchecked", |b| {
        b.iter_batched(
            Board::<Player>::new,
            |mut board| unsafe {
                board.apply_movement_unchecked(black_box(&[[4, 8], [4, 7]]));
            },
            BatchSize::SmallInput,
        );
    });
}

criterion_group!(
    benches,
    bench_iter_available_moves,
    bench_apply_movement_unchecked
);
criterion_main!(benches);
