from backend.models.models import User, Message
from backend.auth import hash_password
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timedelta, timezone
from typing import Optional, List

def create_user(db: Session, username: str, password: str):
    db_user = User(username=username, hashed_password=hash_password(password))
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def save_message(db: Session, sender_id: int, receiver_id: int, content: str):
    msg = Message(sender_id=sender_id, receiver_id=receiver_id, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg

def get_recent_messages(db: Session, user_id: int, partner_id: int):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    return db.query(Message).filter(
        Message.timestamp >= cutoff,
        ((Message.sender_id == user_id) & (Message.receiver_id == partner_id)) |
        ((Message.sender_id == partner_id) & (Message.receiver_id == user_id))
    ).order_by(Message.timestamp).all()

def mark_messages_seen(db: Session, sender_id: int, receiver_id: int):
    db.query(Message).filter(
        Message.sender_id == sender_id,
        Message.receiver_id == receiver_id,
        Message.seen == False
    ).update({"seen": True})
    db.commit()

def delete_expired_messages(db: Session):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    db.query(Message).filter(Message.timestamp < cutoff).delete()
    db.commit()

def get_all_users_except(db: Session, current_username: str):
    return db.query(User).filter(User.username != current_username).all()

def get_active_or_searched_chats(db: Session, user_id: int, search: Optional[str] = None):
    if search:
        # Exact search match
        user = db.query(User).filter(User.username == search).first()
        if user and user.id != user_id:
            return [user.username]
        return []

    # Fetch active chats in the last 24 hours
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    messages = db.query(Message).filter(
        or_(
            Message.sender_id == user_id,
            Message.receiver_id == user_id
        ),
        Message.timestamp >= since
    ).all()

    user_ids = set()
    for msg in messages:
        if msg.sender_id != user_id:
            user_ids.add(msg.sender_id)
        if msg.receiver_id != user_id:
            user_ids.add(msg.receiver_id)

    if not user_ids:
        return []

    usernames = db.query(User.username).filter(User.id.in_(user_ids)).all()
    return [u[0] for u in usernames]

def delete_user(db: Session, user: User):
    db.delete(user)
    db.commit()