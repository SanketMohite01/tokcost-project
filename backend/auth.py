import os
from typing import Optional

from authlib.integrations.base_client.errors import MismatchingStateError
from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, HTTPException, Request
from starlette.responses import RedirectResponse

import database

oauth = OAuth()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
def oauth_callback_uri(request: Request) -> str:
    """Must match the URI registered in Google Cloud and the host used to start login."""
    configured = os.getenv("OAUTH_REDIRECT_URI", "").strip()
    if configured:
        return configured
    base = str(request.base_url).rstrip("/")
    return f"{base}/auth/google/callback"


def configure_oauth():
    if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
        oauth.register(
            name="google",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )


def _admin_emails():
    raw = os.getenv("ADMIN_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


async def google_login(request: Request, pick_account: bool = False):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured on the server.")
    redirect_uri = oauth_callback_uri(request)
    extra = {"prompt": "select_account"} if pick_account else {}
    return await oauth.google.authorize_redirect(request, redirect_uri, **extra)


async def google_callback(request: Request):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured on the server.")
    redirect_uri = oauth_callback_uri(request)
    try:
        # redirect_uri is already stored in session from authorize_redirect; do not pass again.
        token = await oauth.google.authorize_access_token(request)
    except MismatchingStateError as e:
        raise HTTPException(
            status_code=400,
            detail=(
                "OAuth session expired or host mismatch. Use the same hostname for the "
                "API everywhere (either localhost or 127.0.0.1, not both). Start sign-in "
                "from the app, and ensure OAUTH_REDIRECT_URI and Google Console redirect "
                f"URI match exactly (currently: {redirect_uri})."
            ),
        ) from e
    userinfo = token.get("userinfo")
    if not userinfo:
        userinfo = await oauth.google.parse_id_token(request, token)
    google_sub = userinfo.get("sub")
    email = (userinfo.get("email") or "").lower()
    if not google_sub or not email:
        raise HTTPException(status_code=400, detail="Google account missing required profile fields.")

    role = "admin" if email in _admin_emails() else "user"
    user = database.upsert_google_user(google_sub, email, bootstrap_role=role)
    request.session["user_id"] = str(user["id"])
    return RedirectResponse(url=FRONTEND_URL + "/?login=success")


def logout(request: Request):
    request.session.clear()
    return {"ok": True}


def get_optional_user(request: Request) -> Optional[dict]:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return database.get_user_by_id(user_id)


def get_current_user(request: Request) -> dict:
    user = get_optional_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user
