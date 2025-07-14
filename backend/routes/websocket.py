from fastapi import APIRouter, WebSocket, WebSocketDisconnect, BackgroundTasks
from backend.auth import decode_token
from backend.models.models import User
from backend.db.database import get_db
from backend.crud.crud import get_user_by_username, save_message, delete_expired_messages
from collections import defaultdict

router = APIRouter()

active_connections = defaultdict(set)  # username -> set of websockets

def add_connection(username, websocket):
    active_connections[username].add(websocket)

def remove_connection(username, websocket):
    active_connections[username].discard(websocket)
    if not active_connections[username]:
        del active_connections[username]

@router.websocket("/ws/{partner_username}")
async def websocket_endpoint(websocket: WebSocket, partner_username: str, token: str, background_tasks: BackgroundTasks):
    await websocket.accept()
    db = next(get_db())
    try:
        username = decode_token(token)
        user = get_user_by_username(db, username)
        partner = get_user_by_username(db, partner_username)
        if not user or not partner:
            await websocket.close()
            return
    except Exception:
        await websocket.close()
        return

    add_connection(username, websocket)
    background_tasks.add_task(delete_expired_messages, db)

    try:
        while True:
            data = await websocket.receive_json()
            msg_text = data.get("message")
            if msg_text:
                save_message(db, user.id, partner.id, msg_text)
                # Broadcast to sender and receiver if connected
                for ws in active_connections.get(username, []):
                    await ws.send_json({"sender": username, "message": msg_text})
                for ws in active_connections.get(partner_username, []):
                    await ws.send_json({"sender": username, "message": msg_text})
    except WebSocketDisconnect:
        remove_connection(username, websocket)
