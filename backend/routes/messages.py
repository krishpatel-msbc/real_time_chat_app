from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.auth import decode_token
from backend.models.models import User
from backend.db.database import get_db
from backend.crud.crud import get_user_by_username, get_recent_messages, mark_messages_seen
from backend.schemas.schemas import MessageDisplay
from fastapi.security import OAuth2PasswordBearer
from typing import List

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.get("/messages/{partner_username}", response_model=List[MessageDisplay])
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
    mark_messages_seen(db, sender_id=partner.id, receiver_id=user.id)
    return messages
