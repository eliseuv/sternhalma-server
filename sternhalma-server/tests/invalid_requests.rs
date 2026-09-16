use assert_matches::assert_matches;
use common::TestServer;
use sternhalma_server::protocol::{RemoteInMessage, RemoteOutMessage};

mod common;

async fn connect_both_players(server: &TestServer) -> (common::TestClient, common::TestClient) {
    let mut client1 = server.client().await.expect("Failed to connect client 1");
    client1
        .send(RemoteInMessage::Hello)
        .await
        .expect("Failed to send Hello 1");
    let _welcome1 = client1.recv().await.expect("Failed to receive Welcome 1");

    let mut client2 = server.client().await.expect("Failed to connect client 2");
    client2
        .send(RemoteInMessage::Hello)
        .await
        .expect("Failed to send Hello 2");
    let _welcome2 = client2.recv().await.expect("Failed to receive Welcome 2");

    (client1, client2)
}

#[tokio::test(flavor = "multi_thread")]
async fn out_of_turn_move_is_rejected_with_a_reason() {
    let server = TestServer::new().expect("Failed to start server");
    let (mut client1, mut client2) = connect_both_players(&server).await;

    // Player 1 goes first; wait for their Turn message.
    let _turn1 = client1
        .recv()
        .await
        .expect("Player 1 failed to receive Turn");

    // Player 2 tries to move anyway.
    client2
        .send(RemoteInMessage::Choice { movement_index: 0 })
        .await
        .expect("Failed to send out-of-turn Choice");

    let response = client2
        .recv()
        .await
        .expect("Player 2 failed to receive a response");
    assert_matches!(response, RemoteOutMessage::InvalidRequest { reason } if !reason.is_empty());
}

#[tokio::test(flavor = "multi_thread")]
async fn invalid_movement_index_is_rejected_with_a_reason() {
    let server = TestServer::new().expect("Failed to start server");
    let (mut client1, _client2) = connect_both_players(&server).await;

    let msg_turn = client1
        .recv()
        .await
        .expect("Player 1 failed to receive Turn");
    let movements = match msg_turn {
        RemoteOutMessage::Turn { movements } => movements,
        other => panic!("Expected Turn message for Player 1, got {other:?}"),
    };

    // Any index at or past the end of the list is invalid.
    client1
        .send(RemoteInMessage::Choice {
            movement_index: movements.len(),
        })
        .await
        .expect("Failed to send invalid Choice");

    let response = client1
        .recv()
        .await
        .expect("Player 1 failed to receive a response");
    assert_matches!(response, RemoteOutMessage::InvalidRequest { reason } if !reason.is_empty());
}
