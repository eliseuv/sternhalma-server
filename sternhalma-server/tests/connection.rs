use assert_matches::assert_matches;
use common::TestServer;
use sternhalma_server::protocol::{RemoteInMessage, RemoteOutMessage};

mod common;

#[tokio::test]
async fn test_successful_connection_and_handshake() {
    // Start server
    let server = TestServer::new().expect("Failed to start server");

    // Client
    let mut client = server.client().await.expect("Failed to connect client");

    // Send Hello
    client
        .send(RemoteInMessage::Hello)
        .await
        .expect("Failed to send Hello");

    // Expect Welcome
    let msg = client.recv().await.expect("Failed to receive response");
    match msg {
        RemoteOutMessage::Welcome { session_id: _ } => {}
        _ => panic!("Expected Welcome message"),
    };
}

#[tokio::test]
async fn test_multiple_players_connection() {
    let server = TestServer::new().expect("Failed to start server");

    // Player 1
    let mut client1 = server.client().await.expect("Failed to connect client 1");
    client1
        .send(RemoteInMessage::Hello)
        .await
        .expect("Failed to send Hello 1");
    let msg1 = client1.recv().await.expect("Failed to receive response 1");
    match msg1 {
        RemoteOutMessage::Welcome { session_id: _ } => {}
        other => panic!("Unexpected message for client 1: {:?}", other),
    }

    // Player 2
    let mut client2 = server.client().await.expect("Failed to connect client 2");
    client2
        .send(RemoteInMessage::Hello)
        .await
        .expect("Failed to send Hello 2");
    let msg2 = client2.recv().await.expect("Failed to receive response 2");
    match msg2 {
        RemoteOutMessage::Welcome { session_id: _ } => {}
        other => panic!("Unexpected message for client 2: {:?}", other),
    }
}

/// A third and fourth connection, arriving once the first game already has
/// two players, start a second independent game instead of being rejected --
/// the server supports multiple concurrent games (R-16), it no longer caps
/// out at one.
#[tokio::test]
async fn test_third_and_fourth_players_start_a_second_game() {
    let server = TestServer::new().expect("Failed to start server");

    // Game 1: players 1 and 2
    let mut client1 = server.client().await.expect("Failed to connect client 1");
    client1.send(RemoteInMessage::Hello).await.unwrap();
    client1.recv().await.unwrap();

    let mut client2 = server.client().await.expect("Failed to connect client 2");
    client2.send(RemoteInMessage::Hello).await.unwrap();
    client2.recv().await.unwrap();

    // Game 2: players 3 and 4 -- both welcomed, not rejected
    let mut client3 = server.client().await.expect("Failed to connect client 3");
    client3.send(RemoteInMessage::Hello).await.unwrap();
    let msg3 = client3.recv().await.expect("Failed to receive response 3");
    assert_matches!(msg3, RemoteOutMessage::Welcome { .. });

    let mut client4 = server.client().await.expect("Failed to connect client 4");
    client4.send(RemoteInMessage::Hello).await.unwrap();
    let msg4 = client4.recv().await.expect("Failed to receive response 4");
    assert_matches!(msg4, RemoteOutMessage::Welcome { .. });
}
