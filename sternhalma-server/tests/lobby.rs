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

/// A reconnecting session resolves to the game it actually belongs to, not
/// just any game the Lobby happens to be tracking -- R-17, verifying that
/// R-16's Lobby.reconnect() (which tries every tracked game in turn)
/// actually routes correctly rather than assuming it does.
#[tokio::test(flavor = "multi_thread")]
async fn reconnection_resolves_to_the_correct_game_among_several() {
    let server = TestServer::new().expect("Failed to start server");

    // Game 1: players 1 and 2 -- exists purely as a distractor the
    // reconnect must NOT be matched against.
    let mut g1p1 = server.client().await.expect("Failed to connect g1p1");
    g1p1.send(RemoteInMessage::Hello).await.unwrap();
    g1p1.recv().await.expect("g1p1 Welcome");

    let mut g1p2 = server.client().await.expect("Failed to connect g1p2");
    g1p2.send(RemoteInMessage::Hello).await.unwrap();
    g1p2.recv().await.expect("g1p2 Welcome");

    // Drain game 1's own initial Turn message (g1p1, connected first, is
    // its Player 1) before checking isolation below, so that legitimate,
    // independent message isn't mistaken for a leak from game 2.
    match g1p1.recv().await.expect("g1p1 Turn") {
        RemoteOutMessage::Turn { .. } => {}
        other => panic!("Expected Turn for g1p1, got {other:?}"),
    }

    // Game 2: players 3 and 4 -- the one we'll actually disconnect from and
    // reconnect to.
    let mut g2p1 = server.client().await.expect("Failed to connect g2p1");
    g2p1.send(RemoteInMessage::Hello).await.unwrap();
    let session_id = match g2p1.recv().await.expect("g2p1 Welcome") {
        RemoteOutMessage::Welcome { session_id } => session_id,
        other => panic!("Expected Welcome for g2p1, got {other:?}"),
    };

    let mut g2p2 = server.client().await.expect("Failed to connect g2p2");
    g2p2.send(RemoteInMessage::Hello).await.unwrap();
    g2p2.recv().await.expect("g2p2 Welcome");

    // g2p1 connected first, so it's game 2's Player 1 and moves first (same
    // assumption tests/reconnection.rs's single-game test already makes).
    match g2p1.recv().await.expect("g2p1 Turn") {
        RemoteOutMessage::Turn { .. } => {}
        other => panic!("Expected Turn for g2p1, got {other:?}"),
    }

    // Disconnect game 2's mover (g2p1) and reconnect using its session ID.
    drop(g2p1);
    let mut reconnected = server
        .client()
        .await
        .expect("Failed to reconnect to game 2");
    reconnected
        .send(RemoteInMessage::Reconnect { session_id })
        .await
        .unwrap();
    match reconnected.recv().await.expect("reconnect response") {
        RemoteOutMessage::Welcome {
            session_id: new_sid,
        } => assert_eq!(session_id, new_sid),
        RemoteOutMessage::Reject { reason } => panic!("Reconnection rejected: {reason}"),
        other => panic!("Unexpected reconnect response: {other:?}"),
    }
    match reconnected.recv().await.expect("Turn after reconnect") {
        RemoteOutMessage::Turn { .. } => {}
        other => panic!("Expected Turn after reconnect, got {other:?}"),
    }

    // Make a move as the reconnected player.
    reconnected
        .send(RemoteInMessage::Choice { movement_index: 0 })
        .await
        .unwrap();

    // Game 2's other player sees it -- proving the reconnect landed in game
    // 2, not some other tracked game.
    let msg = g2p2.recv().await.expect("g2p2 Movement broadcast");
    assert!(matches!(msg, RemoteOutMessage::Movement { .. }));

    // Game 1's players see nothing -- proving the reconnect wasn't (even
    // partially) matched against the wrong game.
    for client in [&mut g1p1, &mut g1p2] {
        let result = tokio::time::timeout(Duration::from_millis(200), client.recv()).await;
        assert!(
            result.is_err(),
            "expected no message to have crossed over to game 1, got {result:?}"
        );
    }
}
