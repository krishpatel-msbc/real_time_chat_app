from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.auth import decode_token, verify_password
from backend.models.models import User
from backend.db.database import get_db
from backend.crud.crud import get_user_by_username, get_active_or_searched_chats, delete_user
from backend.schemas.schemas import DeleteAccountRequest
from fastapi.security import OAuth2PasswordBearer
from typing import List

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.get("/me")
def get_me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    username = decode_token(token)
    user = get_user_by_username(db, username)
    return {"id": user.id, "username": user.username}

@router.get("/active_chats", response_model=List[str])
def active_chats(
    search: str = Query(default=None),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    current_username = decode_token(token)
    user = get_user_by_username(db, current_username)
    return get_active_or_searched_chats(db, user.id, search)

@router.delete("/delete_account")
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
