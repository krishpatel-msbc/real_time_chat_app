from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from backend.auth import create_access_token, verify_password, decode_token
from backend.models.models import Base, User
from backend.db.database import engine, get_db
from backend.crud.crud import (
    create_user, get_recent_messages, get_user_by_username,
    save_message, delete_expired_messages, mark_messages_seen,
    get_active_or_searched_chats, delete_user
)
from backend.schemas.schemas import UserCreate, Token, MessageDisplay, DeleteAccountRequest
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
def root():
    return {"message": "Welcome to the Real-Time Chat API"}

@app.get("/me")
def get_me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    username = decode_token(token)
    user = get_user_by_username(db, username)
    return {"id": user.id, "username": user.username}

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="Username already exists.")
    return create_user(db, user.username, user.password)

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/messages/{partner_username}", response_model=List[MessageDisplay])
def get_messages(
    partner_username: str,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    username = decode_token(token)
    user = get_user_by_username(db, username)
    partner = get_user_by_username(db, partner_username)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    messages = get_recent_messages(db, user.id, partner.id)
    # Mark messages from partner as seen
    mark_messages_seen(db, sender_id=partner.id, receiver_id=user.id)
    return messages

@app.get("/active_chats", response_model=List[str])
def active_chats(
    search: str = Query(default=None),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    current_username = decode_token(token)
    user = get_user_by_username(db, current_username)
    return get_active_or_searched_chats(db, user.id, search)



@app.delete("/delete_account")
def delete_account(
    request: DeleteAccountRequest,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    username = decode_token(token)
    user = get_user_by_username(db, username)
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid password")
    delete_user(db, user)
    return {"detail": "Account deleted successfully"}

# WebSocket Chatroom Logic

from collections import defaultdict

active_connections = defaultdict(set)  # username -> set of websockets

def add_connection(username, websocket):
    active_connections[username].add(websocket)

def remove_connection(username, websocket):
    active_connections[username].discard(websocket)
    if not active_connections[username]:
        del active_connections[username]

@app.websocket("/ws/{partner_username}")
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
    except HTTPException:
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