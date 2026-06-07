from fastapi import APIRouter
from starlette.requests import Request
from authlib.integrations.starlette_client import OAuth
from chat.config import settings

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
    client_kwargs={'scope': 'openid profile email'},
)


@social_router.get('/github')
async def login_github(request: Request):
    return await oauth.github.authorize_redirect(request, settings.GITHUB_URL)


@social_router.get('/google')
async def login_google(request: Request):
    return await oauth.google.authorize_redirect(request, settings.GOOGLE_URL)