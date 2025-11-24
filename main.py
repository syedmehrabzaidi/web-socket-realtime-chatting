import json
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Allow CORS for all origins (not recommended for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Message history and connection manager
MESSAGE_HISTORY = []
HISTORY_LIMIT = 100


class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, user_id, websocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    async def disconnect(self, user_id):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def broadcast(self, message: str):
        for websocket in self.active_connections.values():
            try:
                await websocket.send_text(message)
            except Exception:
                pass


manager = ConnectionManager()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")  # ✅ Root route
async def home(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for chat.
    Client first sends join message with type: "join" and payload: { user: "username" }
    Example:
    ```
    {"type": "join", "payload": {"user": "alice"}}
    {"type": "msg", "payload": {"user": "alice", "text": "hello"}}
    ```
    Server broadcasts: {type: "msg", payload: {user, text, ts}}
    """
    # For simplicity we accept any origin; in production, validate origin and tokens.
    user_id = None
    try:
        # wait for join message first
        initial = await websocket.receive_text()

        try:
            obj = json.loads(initial)
        except Exception:
            await websocket.send_text(json.dumps({"type": "error", "message": "invalid json on join"}))
            await websocket.close()
            return

        if obj.get("type") != "join" or not obj.get("payload") or not obj["payload"].get("user"):
            await websocket.send_text(json.dumps({"type": "error", "message": "missing join/user"}))
            await websocket.close()
            return

        user_id = obj["payload"]["user"]
        await manager.connect(user_id, websocket)

        # announce join
        join_msg = {"type": "join", "payload": {"user": user_id, "ts": time.time()}}
        MESSAGE_HISTORY.append(join_msg)
        # trim
        if len(MESSAGE_HISTORY) > HISTORY_LIMIT:
            del MESSAGE_HISTORY[: len(MESSAGE_HISTORY) - HISTORY_LIMIT]
        await manager.broadcast(json.dumps(join_msg))

        # main loop
        while True:
            data = await websocket.receive_text()
            try:
                obj = json.loads(data)
            except Exception:
                await websocket.send_text(json.dumps({"type": "error", "message": "invalid json"}))
                continue

            if obj.get("type") == "msg":
                payload = obj.get("payload", {})
                text = payload.get("text")
                user = payload.get("user", user_id)
                if not text:
                    continue
                message = {"type": "msg", "payload": {"user": user, "text": text, "ts": time.time()}}
                MESSAGE_HISTORY.append(message)
                if len(MESSAGE_HISTORY) > HISTORY_LIMIT:
                    del MESSAGE_HISTORY[: len(MESSAGE_HISTORY) - HISTORY_LIMIT]
                await manager.broadcast(json.dumps(message))
            elif obj.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "ts": time.time()}))
            else:
                # unknown type: ignore or send error
                await websocket.send_text(json.dumps({"type": "error", "message": "unknown type"}))

    except WebSocketDisconnect:
        # handled below
        pass
    except Exception as exc:
        # log exception, then disconnect
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        if user_id:
            await manager.disconnect(user_id)
            leave_msg = {"type": "leave", "payload": {"user": user_id, "ts": time.time()}}
            MESSAGE_HISTORY.append(leave_msg)
            if len(MESSAGE_HISTORY) > HISTORY_LIMIT:
                del MESSAGE_HISTORY[: len(MESSAGE_HISTORY) - HISTORY_LIMIT]
            await manager.broadcast(json.dumps(leave_msg))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)