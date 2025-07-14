from pydantic import BaseModel
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class MessageDisplay(BaseModel):
    sender_id: int
    receiver_id: int
    content: str
    timestamp: datetime
    seen: bool

    class Config:
        from_attributes = True

class UserPublic(BaseModel):
    username: str

    class Config:
        from_attributes = True

class DeleteAccountRequest(BaseModel):
    password: str