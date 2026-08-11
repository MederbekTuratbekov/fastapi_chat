from fastapi import FastAPI
import uvicorn
from starlette.middleware.sessions import SessionMiddleware

from api.auth import auth_router
from api.social_auth import social_router
from api.chat import chat_router
from api.groups import router as groups_router
from api.members import router as members_router
from api.user import router as user_router
from config import SECRET_KEY

app = FastAPI(
    title="FastAPI Chat",
    description="Простой чат с группами на FastAPI + WebSocket",
    version="1.0.0"
)

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.include_router(auth_router)
app.include_router(social_router)
app.include_router(chat_router)
app.include_router(groups_router)
app.include_router(members_router)
app.include_router(user_router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
