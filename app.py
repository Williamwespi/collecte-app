import os
import secrets

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from database import init_db
from routes.publiek import router

app = FastAPI(title="Collecteteller Diaconie")

session_secret = os.getenv("SESSION_SECRET") or secrets.token_urlsafe(48)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.middleware("http")
async def login_required(request: Request, call_next):
    public_paths = {"/login"}
    if request.url.path.startswith("/static/") or request.url.path in public_paths:
        return await call_next(request)

    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)

    return await call_next(request)


app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    same_site="lax",
    https_only=os.getenv("COOKIE_HTTPS_ONLY", "1") == "1",
    max_age=60 * 60 * 12,
)

app.include_router(router)


@app.on_event("startup")
def startup():
    init_db()
