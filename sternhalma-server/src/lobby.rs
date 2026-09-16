//! # Lobby Module
//!
//! Spawns and tracks independent game [`Server`] tasks, so more than one game
//! can run concurrently. Routes a new connection to whichever tracked game has
//! a free player slot, spawning a fresh one if none does; routes a
//! reconnection to whichever tracked game recognizes the session.

use std::time::Duration;

use tokio::sync::{Mutex, broadcast, mpsc, oneshot};
use uuid::Uuid;

use sternhalma_game::player::Player;

use crate::{
    MainThreadMessage, Server,
    messages::{ClientMessage, ServerBroadcast},
};

const LOCAL_CHANNEL_CAPACITY: usize = 32;

/// Channels needed to talk to one running game's `Server` task
#[derive(Clone)]
pub struct GameChannels {
    pub main_tx: mpsc::Sender<MainThreadMessage>,
    pub client_msg_tx: mpsc::Sender<ClientMessage>,
    pub server_broadcast_tx: broadcast::Sender<ServerBroadcast>,
}

/// Spawns and tracks independent games, routing handshakes to one of them
///
/// Tracked games are never removed once finished -- their channels just stop
/// responding (the `Server` task has exited, dropping its receivers), so a
/// scan skips them. Harmless at the scale this server runs at, but a real
/// resource leak over a long-lived process; worth pruning in a follow-up.
pub struct Lobby {
    timeout: Duration,
    max_turns: usize,
    games: Mutex<Vec<GameChannels>>,
}

impl Lobby {
    pub fn new(timeout: Duration, max_turns: usize) -> Self {
        Self {
            timeout,
            max_turns,
            games: Mutex::new(Vec::new()),
        }
    }

    /// Find a game with a free player slot, or spawn a new one
    ///
    /// Always succeeds: a freshly spawned game always has free player slots.
    pub async fn join(&self) -> (GameChannels, Player) {
        {
            let games = self.games.lock().await;
            for channels in games.iter() {
                if let Some(player) = request_free_player(channels).await {
                    return (channels.clone(), player);
                }
            }
        }

        let channels = self.spawn_game().await;
        let player = request_free_player(&channels)
            .await
            .expect("a freshly spawned game always has a free player slot");
        (channels, player)
    }

    /// Find which tracked game a reconnecting session belongs to
    pub async fn reconnect(&self, session_id: Uuid) -> Option<(GameChannels, Player)> {
        let games = self.games.lock().await;
        for channels in games.iter() {
            if let Some(player) = request_reconnect(channels, session_id).await {
                return Some((channels.clone(), player));
            }
        }
        None
    }

    /// Spawn a new game's `Server` task and register its channels
    async fn spawn_game(&self) -> GameChannels {
        let (client_msg_tx, client_msg_rx) = mpsc::channel::<ClientMessage>(LOCAL_CHANNEL_CAPACITY);
        let (server_broadcast_tx, _server_broadcast_rx) =
            broadcast::channel::<ServerBroadcast>(LOCAL_CHANNEL_CAPACITY);
        let (main_tx, main_rx) = mpsc::channel::<MainThreadMessage>(LOCAL_CHANNEL_CAPACITY);

        let server = Server::new(main_rx, client_msg_rx, server_broadcast_tx.clone())
            .expect("Server::new is currently infallible");

        let timeout = self.timeout;
        let max_turns = self.max_turns;
        tokio::spawn(async move {
            if let Err(e) = server.try_run(timeout, max_turns).await {
                log::error!("Game encountered an error: {e:?}");
            }
        });

        let channels = GameChannels {
            main_tx,
            client_msg_tx,
            server_broadcast_tx,
        };
        self.games.lock().await.push(channels.clone());
        channels
    }
}

async fn request_free_player(channels: &GameChannels) -> Option<Player> {
    let (resp_tx, resp_rx) = oneshot::channel();
    channels
        .main_tx
        .send(MainThreadMessage::RequestFreePlayer(resp_tx))
        .await
        .ok()?;
    resp_rx.await.ok().flatten()
}

async fn request_reconnect(channels: &GameChannels, session_id: Uuid) -> Option<Player> {
    let (resp_tx, resp_rx) = oneshot::channel();
    channels
        .main_tx
        .send(MainThreadMessage::ClientReconnectedHandle(
            session_id, resp_tx,
        ))
        .await
        .ok()?;
    resp_rx.await.ok().flatten()
}
