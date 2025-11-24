import json
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
import uuid

app = FastAPI(title="Realtime Chat Server")

# ------------------ CORS ------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ Templates & Static ------------------
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ------------------ Connection & History ------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}  # user_id -> WebSocket

    async def connect(self, user_id: str, websocket: WebSocket):
        self.active_connections[user_id] = websocket

    async def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def broadcast(self, message: dict):
        # Convert to JSON string
        data = json.dumps(message)
        for ws in list(self.active_connections.values()):
            try:
                await ws.send_text(data)
            except Exception:
                pass  # Ignore errors for now

manager = ConnectionManager()

MESSAGE_HISTORY = []
HISTORY_LIMIT = 100

# ------------------ Routes ------------------
@app.get("/")
async def home(request: Request):
    """
    Root route serving the chat page.
    """
    return templates.TemplateResponse("chat.html", {"request": request})

# ------------------ WebSocket ------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    user_id = None
    try:
        # Accept the WebSocket connection first
        await websocket.accept()
        
        # ------------------ Wait for join ------------------
        init_text = await websocket.receive_text()
        try:
            init_obj = json.loads(init_text)
        except Exception:
            await websocket.close()
            return

        if init_obj.get("type") != "join" or not init_obj.get("payload") or not init_obj["payload"].get("user"):
            await websocket.close()
            return

        # ------------------ Assign user ------------------
        username = init_obj["payload"]["user"]
        user_id = str(uuid.uuid4())
        await manager.connect(user_id, websocket)

        # ------------------ Send join message ------------------
        join_msg = {"type": "join", "payload": {"user": username, "ts": time.time()}}
        MESSAGE_HISTORY.append(join_msg)
        if len(MESSAGE_HISTORY) > HISTORY_LIMIT:
            del MESSAGE_HISTORY[: len(MESSAGE_HISTORY) - HISTORY_LIMIT]
        await manager.broadcast(join_msg)

        # ------------------ Send history to the new user ------------------
        for msg in MESSAGE_HISTORY:
            await websocket.send_text(json.dumps(msg))

        # ------------------ Main loop ------------------
        while True:
            data = await websocket.receive_text()
            try:
                obj = json.loads(data)
            except Exception:
                await websocket.send_text(json.dumps({"type": "error", "message": "invalid json"}))
                continue

            msg_type = obj.get("type")
            payload = obj.get("payload", {})

            if msg_type == "msg":
                text = payload.get("text")
                if not text:
                    continue
                message = {
                    "type": "msg",
                    "payload": {
                        "user": username,
                        "text": text,
                        "ts": time.time()
                    }
                }
                MESSAGE_HISTORY.append(message)
                if len(MESSAGE_HISTORY) > HISTORY_LIMIT:
                    del MESSAGE_HISTORY[: len(MESSAGE_HISTORY) - HISTORY_LIMIT]
                await manager.broadcast(message)

            elif msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "ts": time.time()}))

            else:
                await websocket.send_text(json.dumps({"type": "error", "message": "unknown type"}))

    except WebSocketDisconnect:
        pass
    finally:
        if user_id:
            await manager.disconnect(user_id)
            leave_msg = {"type": "leave", "payload": {"user": username, "ts": time.time()}}
            MESSAGE_HISTORY.append(leave_msg)
            if len(MESSAGE_HISTORY) > HISTORY_LIMIT:
                del MESSAGE_HISTORY[: len(MESSAGE_HISTORY) - HISTORY_LIMIT]
            await manager.broadcast(leave_msg)

# ------------------ Run ------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
