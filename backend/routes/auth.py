from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.auth import create_access_token, verify_password
from backend.models.models import User
from backend.db.database import get_db
from backend.crud.crud import create_user, get_user_by_username
from backend.schemas.schemas import UserCreate, Token
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter()

@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="Username already exists.")
    return create_user(db, user.username, user.password)

@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}
