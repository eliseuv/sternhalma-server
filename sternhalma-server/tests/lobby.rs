use std::time::Duration;

use common::TestServer;
use sternhalma_server::protocol::{RemoteInMessage, RemoteOutMessage};

mod common;

/// Two games running concurrently don't leak moves or broadcasts into each
/// other -- confirms R-16's "without cross-session interference".
#[tokio::test(flavor = "multi_thread")]
async fn concurrent_games_do_not_interfere() {
    let server = TestServer::new().expect("Failed to start server");

    // Game 1: players 1 and 2
    let mut g1p1 = server.client().await.expect("Failed to connect g1p1");
    g1p1.send(RemoteInMessage::Hello).await.unwrap();
    g1p1.recv().await.expect("g1p1 Welcome");

    let mut g1p2 = server.client().await.expect("Failed to connect g1p2");
    g1p2.send(RemoteInMessage::Hello).await.unwrap();
    g1p2.recv().await.expect("g1p2 Welcome");

    // Game 2: players 3 and 4, a second independent game
    let mut g2p1 = server.client().await.expect("Failed to connect g2p1");
    g2p1.send(RemoteInMessage::Hello).await.unwrap();
    g2p1.recv().await.expect("g2p1 Welcome");

    let mut g2p2 = server.client().await.expect("Failed to connect g2p2");
    g2p2.send(RemoteInMessage::Hello).await.unwrap();
    g2p2.recv().await.expect("g2p2 Welcome");

    // Drain game 2's own initial Turn message (sent to whichever of g2p1/g2p2
    // is its Player1) before checking isolation below, so that legitimate,
    // independent message isn't mistaken for a leak from game 1.
    for client in [&mut g2p1, &mut g2p2] {
        let _ = tokio::time::timeout(Duration::from_millis(500), client.recv()).await;
    }

    // Whichever of game 1's players goes first makes a move.
    let (mover, other) = match g1p1.recv().await.expect("g1 Turn") {
        RemoteOutMessage::Turn { .. } => (&mut g1p1, &mut g1p2),
        other => panic!("Expected Turn for g1p1, got {other:?}"),
    };
    mover
        .send(RemoteInMessage::Choice { movement_index: 0 })
        .await
        .unwrap();

    // Both game 1 players see the move broadcast.
    let msg = mover.recv().await.expect("mover Movement broadcast");
    assert!(matches!(msg, RemoteOutMessage::Movement { .. }));
    let msg = other.recv().await.expect("other Movement broadcast");
    assert!(matches!(msg, RemoteOutMessage::Movement { .. }));

    // Game 2's players see none of it: each is still only waiting on its own
    // Turn message, which hasn't arrived yet since neither has moved.
    for client in [&mut g2p1, &mut g2p2] {
        let result = tokio::time::timeout(Duration::from_millis(200), client.recv()).await;
        assert!(
            result.is_err(),
            "expected no message to have crossed over from game 1, got {result:?}"
        );
    }
}
