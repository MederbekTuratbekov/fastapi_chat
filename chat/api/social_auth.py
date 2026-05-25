from fastapi import APIRouter
from starlette.requests import Request
from authlib.integrations.starlette_client import OAuth
from ..config import settings


social_router = APIRouter(prefix='/oauth', tags=['Social Auth'])

# github --------------------------------------------------------------

oauth = OAuth()
oauth.register(
    name='github',
    client_id=settings.GITHUB_CLIENT_ID,
    secter_key=settings.GITHUB_KEY,
    authorize_url='https://github.com/login/oauth/authorize'
)

@social_router.get('/github')
async def login_github(request: Request):
    redirect_uri = settings.GITHUB_URL
    return await oauth.github.authorize_redirect(request, redirect_uri)

# google --------------------------------------------------------------

oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    secter_key=settings.GOOGLE_KEY,
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    client_kwargs={"scope": "openid profile email"},)

@social_router.get('/google')
async def login_google(request: Request):
    redirect_uri = settings.GOOGLE_URL
    return await oauth.google.authorize_redirect(request, redirect_uri)