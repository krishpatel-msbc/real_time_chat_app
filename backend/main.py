from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from backend.routes import auth, user, messages, websocket

app = FastAPI()

router = APIRouter()

@router.get("/")
def root():
    return {"message": "Welcome to the Real-Time Chat API"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


app.include_router(auth.router)
app.include_router(user.router)
app.include_router(messages.router)
app.include_router(websocket.router)