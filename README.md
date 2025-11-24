# Realtime WebSocket Chat

A simple realtime chat server and frontend using FastAPI (WebSockets) and a lightweight client UI. This repository contains:

- `main.py` — FastAPI server that accepts WebSocket connections, keeps an in-memory message history, and broadcasts messages to all connected clients.
- `templates/chat.html` — A minimal frontend served by the FastAPI app that connects to the `/ws` endpoint and shows chat messages.
- `gradio_app.py` — An alternate UI using Gradio that displays an embedded HTML chat UI.

This README explains how to run the project, the WebSocket message format used by the server, troubleshooting tips, and a short WebSocket primer (FAQ/tutorial).

---

## Quickstart

Recommended: run inside a Python virtual environment.

1. Create and activate a venv (POSIX):

```bash
python3 -m venv env
source env/bin/activate
```

2. Install dependencies (fastapi, uvicorn, jinja2, gradio if you want the Gradio UI):

```bash
pip install fastapi uvicorn jinja2
# optional for gradio-based interface
pip install gradio
```

3. Run the FastAPI server (this serves `chat.html` and the `/ws` WebSocket endpoint):

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in two browser windows and test the chat.

If you prefer the Gradio wrapper UI instead of the template:

```bash
python gradio_app.py
# then open http://localhost:7860
```

---

## What this project does

- Accepts WebSocket connections at `/ws`.
- Clients must send a `join` message first to set their username.
- The server stores recent messages in `MESSAGE_HISTORY` (in-memory) and sends the history to newly joined users.
- When a client sends a `msg` message, the server broadcasts it to all connected clients and saves it in history.

Note: This is an in-memory example (no DB). For production use, persist messages to a database and add authentication, rate limiting, origin checks, and secure deployment.

---

## WebSocket protocol used (message format)

All messages exchanged between client and server are JSON objects with a `type` string and an optional `payload` object.

Client -> Server formats:

- Join (first message):

```json
{ "type": "join", "payload": { "user": "alice" } }
```

- Send message:

```json
{ "type": "msg", "payload": { "text": "Hello everyone" } }
```

- Ping (keepalive/example):

```json
{ "type": "ping" }
```

Server -> Client formats:

- Broadcasted message:

```json
{ "type": "msg", "payload": { "user": "alice", "text": "Hello", "ts": 169XXX } }
```

- Join/leave/system notifications:

```json
{ "type": "join", "payload": { "user": "alice", "ts": 169XXX } }
{ "type": "leave", "payload": { "user": "alice", "ts": 169XXX } }
```

- Pong reply to ping:

```json
{ "type": "pong", "ts": 169XXX }
```

- Error:

```json
{ "type": "error", "message": "explanation" }
```

---

## Important implementation notes

- The server currently accepts any origin. In real deployments restrict origins and validate tokens.
- `MESSAGE_HISTORY` is an in-memory list. It is trimmed to `HISTORY_LIMIT` to bound memory usage.
- `ConnectionManager` stores active WebSocket objects in memory, keyed by `user_id` (UUID). Replace this with a distributed pub/sub or a database-backed store if you need multiple server instances.

---

## Troubleshooting

- "WebSocket is not connected. Need to call accept first." — make sure you call `await websocket.accept()` in the WebSocket route before calling `receive_text()` or `send_text()`.
- "Expected ASGI message 'websocket.send' or 'websocket.close', but got 'websocket.accept'" — accept must be called only once; avoid calling `accept()` in both the endpoint and some helper function.
- If messages disappear after sending: verify the client sends the correct JSON (type `msg` with a `payload.text` field) and the server broadcasts JSON strings (it uses `json.dumps`). Also confirm clients parse incoming messages as JSON.

---

## Basic WebSocket primer & FAQ (short tutorial)

Q: What is a WebSocket?

A: WebSocket is a bidirectional, full-duplex communication protocol over a single TCP connection. It allows servers to push messages to clients without the client repeatedly polling for updates.

Q: How does a WebSocket connection start?

A: The client sends an HTTP-based handshake request (an `Upgrade: websocket` request). The server responds with a 101 Switching Protocols response and both sides then speak the WebSocket protocol frames.

Q: What is `accept()` in FastAPI / Starlette?

A: In FastAPI's WebSocket route you must call `await websocket.accept()` to accept the connection and start exchanging messages. After that you can call `await websocket.receive_text()` and `await websocket.send_text()`.

Q: What message patterns should I follow for a chat app?

A: It's good to use a small message envelope with `type` and `payload`. Example types: `join`, `msg`, `ping`, `pong`, `leave`, `error`. Keep payloads small and consistent.

Q: How do I debug a WebSocket connection?

- Use browser devtools Network → WS frames to inspect sent/received frames.
- Log messages on server side before broadcasting.
- Ensure `await websocket.accept()` is called only once per connection.
- Test with two browser tabs to ensure broadcasting works.

Q: How do I handle reconnects and user identity?

- Decide whether usernames are ephemeral (client-provided) or authenticated (tokens + server-side mapping).
- On reconnect you can map the same user to the same server-side id using a token or cookie.
- Consider `last seen` timestamps and re-sending missed messages (store offsets or message IDs).

---

## Suggested next steps / production hardening

- Persist messages in a database (Postgres, Redis streams, or a time-series DB) and store user sessions.
- Use authentication tokens (JWT) and validate them on connect.
- Use a message broker (Redis Pub/Sub, NATS, Kafka) if you plan to scale to multiple app instances.
- Add rate limiting and spam protections.
- Add tests for the message flows and connection handling.

---

## Contact

If you want improvements (DB storage, authentication, scaling to multiple nodes, or tests), open an issue or send me the requirements and I can add them.

---

## License

This project is provided as-is for learning/demo use. Add your preferred license file if you plan to publish or distribute.
