//! # Sternhalma Server Binary
//!
//! This is the entry point for the Sternhalma Server application.
//! It parses command-line arguments, initializes the logger, sets up the server thread channels,
//! and starts the TCP and WebSocket listeners.
//!
//! ## Usage
//! ```sh
//! sternhalma-server --tcp 0.0.0.0:1234 --ws 0.0.0.0:8080
//! ```

use std::{sync::Arc, time::Duration};

use anyhow::{Context, Result};
use axum::{Router, routing::get};
use clap::Parser;
use futures::{SinkExt, StreamExt};
use tokio::net::TcpListener;
use tokio_util::codec::Framed;

use sternhalma_server::{
    client::{ClientSink, ClientStream},
    handshake::{AppState, handle_handshake},
    lobby::Lobby,
    protocol::ServerCodec,
    ws::ws_handler,
};

/// Command line arguments
#[derive(Debug, Parser)]
#[command(name = "sternhalma-server", version, about)]
struct Args {
    /// Host IP address for Raw TCP
    #[arg(long, value_name = "ADDRESS")]
    tcp: Option<String>,
    /// Host IP address for WebSocket
    #[arg(long, value_name = "ADDRESS")]
    ws: Option<String>,
    /// Maximum number of turns
    #[arg(short = 'n', long, value_name = "N")]
    max_turns: Option<usize>,
    #[arg(short, long, value_name = "SECONDS", default_value_t = 300)]
    timeout: u64,
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logger
    env_logger::init();

    // Parse command line arguments
    let args = Args::parse();
    log::debug!("Command line arguments: {args:?}");
    let timeout = Duration::from_secs(args.timeout);

    // The Lobby spawns an independent game (its own Server task and channel
    // set) per match, so more than one game can run at once; it's consulted
    // fresh on every handshake rather than fixed at startup like a single
    // Server used to be.
    let max_turns = args.max_turns.unwrap_or(usize::MAX);
    let app_state = AppState {
        lobby: Arc::new(Lobby::new(timeout, max_turns)),
    };

    // --- Start Listener ---

    if args.tcp.is_none() && args.ws.is_none() {
        use clap::CommandFactory;
        let mut cmd = Args::command();
        cmd.error(
            clap::error::ErrorKind::MissingRequiredArgument,
            "Either --tcp or --ws must be provided",
        )
        .exit();
    }

    if let Some(addr) = args.tcp {
        // 1. TCP Listener (Raw protocol)
        let listener = TcpListener::bind(&addr)
            .await
            .with_context(|| "Failed to bind listener to socket")?;
        log::info!("Listening (TCP) at {addr}");

        let app_state = app_state.clone();
        tokio::spawn(async move {
            loop {
                match listener.accept().await {
                    Err(e) => {
                        log::error!("Failed to accept connection: {e:?}");
                        continue;
                    }
                    Ok((stream, _addr)) => {
                        let framed = Framed::new(stream, ServerCodec::new());
                        let (write, read) = framed.split();
                        let sink: ClientSink = Box::pin(write.sink_map_err(|e| anyhow::anyhow!(e)));
                        let stream: ClientStream =
                            Box::pin(read.map(|msg| msg.map_err(|e| anyhow::anyhow!(e))));

                        tokio::spawn(handle_handshake(stream, sink, app_state.clone()));
                    }
                }
            }
        });
    }

    if let Some(addr) = args.ws {
        // 2. WebSocket Listener (Web Clients)
        let app = Router::new()
            .route("/ws", get(ws_handler))
            .layer(tower_http::cors::CorsLayer::permissive())
            .with_state(app_state.clone());

        let listener = tokio::net::TcpListener::bind(&addr).await?;
        log::info!("Listening (WS) at {addr}");

        tokio::spawn(async move {
            if let Err(e) = axum::serve(listener, app).await {
                log::error!("Axum server error: {e}");
            }
        });
    }

    // Run until interrupted -- each game's own lifetime is independent of
    // the process's now that the Lobby can spawn more than one.
    tokio::signal::ctrl_c()
        .await
        .with_context(|| "Failed to listen for shutdown signal")?;
    log::trace!("Shutdown signal received");

    Ok(())
}
