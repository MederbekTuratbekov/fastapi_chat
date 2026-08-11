from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request
from authlib.integrations.starlette_client import OAuth
import httpx

from chat.config import settings
from chat.db.database import SessionLocal
from chat.db.models import User
from chat.api.auth import create_access_token, create_refresh_token, get_password_hash
import secrets

social_router = APIRouter(prefix='/oauth', tags=['Social Auth'])

oauth = OAuth()

oauth.register(
    name='github',
    client_id=settings.GITHUB_CLIENT_ID,
    client_secret=settings.GITHUB_KEY,
    authorize_url='https://github.com/login/oauth/authorize',
    access_token_url='https://github.com/login/oauth/access_token',
    client_kwargs={'scope': 'user:email'},
)

oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_KEY,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    access_token_url='https://oauth2.googleapis.com/token',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={'scope': 'openid profile email'},
)


def get_or_create_user(db, username: str, email: str) -> User:
    """Найти юзера по email или создать нового"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # username может быть занят — добавляем случайный суффикс
        base_username = username
        while db.query(User).filter(User.username == username).first():
            username = f"{base_username}_{secrets.token_hex(3)}"

        user = User(
            username=username,
            email=email,
            password=get_password_hash(secrets.token_hex(16)),  # случайный пароль
            status="simple"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@social_router.get('/github')
async def login_github(request: Request):
    return await oauth.github.authorize_redirect(request, settings.GITHUB_URL)


@social_router.get('/github/callback')
async def github_callback(request: Request):
    db = SessionLocal()
    try:
        token = await oauth.github.authorize_access_token(request)

        # Получаем данные пользователя
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token['access_token']}"}

            user_resp = await client.get("https://api.github.com/user", headers=headers)
            user_data = user_resp.json()

            email_resp = await client.get("https://api.github.com/user/emails", headers=headers)
            emails = email_resp.json()

        # Берём primary email
        email = next(
            (e["email"] for e in emails if e.get("primary") and e.get("verified")),
            None
        )
        if not email:
            raise HTTPException(status_code=400, detail="GitHub email not available")

        username = user_data.get("login", email.split("@")[0])

        user = get_or_create_user(db, username, email)

        access_token = create_access_token(data={"sub": user.username})
        refresh_token = create_refresh_token(data={"sub": user.username})

        return JSONResponse({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username,
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"GitHub auth failed: {str(e)}")
    finally:
        db.close()


@social_router.get('/google')
async def login_google(request: Request):
    return await oauth.google.authorize_redirect(request, settings.GOOGLE_URL)


@social_router.get('/google/callback')
async def google_callback(request: Request):
    db = SessionLocal()
    try:
        token = await oauth.google.authorize_access_token(request)

        # userinfo уже внутри токена (OpenID Connect)
        user_info = token.get("userinfo")
        if not user_info:
            raise HTTPException(status_code=400, detail="Google user info not available")

        email = user_info.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Google email not available")

        username = user_info.get("name", email.split("@")[0]).replace(" ", "_")

        user = get_or_create_user(db, username, email)

        access_token = create_access_token(data={"sub": user.username})
        refresh_token = create_refresh_token(data={"sub": user.username})

        return JSONResponse({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username,
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Google auth failed: {str(e)}")
    finally:
        db.close()
