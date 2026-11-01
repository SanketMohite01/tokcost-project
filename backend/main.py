import logging
import os
from typing import Dict, List, Optional
from uuid import UUID

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

import auth
import cost_engine
import database
import estimator
from prompt_compressor import compress_prompt
from token_counter import count_tokens_gpt

load_dotenv()
logger = logging.getLogger("tokcost")

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_FILES = 5
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

app = FastAPI(title="TokCost API", version="0.3.0")

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",
    https_only=False,
)

_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]
_extra = os.getenv("FRONTEND_URL", "").rstrip("/")
if _extra and _extra not in _origins:
    _origins.append(_extra)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

auth.configure_oauth()


class FileIn(BaseModel):
    filename: str
    file_type: str
    size_bytes: Optional[int] = None
    tokens: Optional[Dict[str, int]] = None


class ResultIn(BaseModel):
    platform: str
    input_tokens: int
    est_output_tokens: Optional[int] = None
    est_cost_usd: Optional[float] = None


class SessionIn(BaseModel):
    prompt_text: str
    compressed_prompt: Optional[str] = None
    recommended_platform: Optional[str] = None
    summary: Optional[str] = None
    title: Optional[str] = None
    files: List[FileIn] = []
    results: List[ResultIn] = []


class SessionUpdateIn(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=120)
    pinned: Optional[bool] = None


class RoleUpdateIn(BaseModel):
    role: str = Field(..., pattern="^(user|admin)$")


def process_files(files):
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Attach at most {MAX_FILES} files")

    results = []
    for f in files:
        data = f.file.read()
        if len(data) > MAX_FILE_BYTES:
            raise HTTPException(status_code=400, detail=f"{f.filename} is larger than 10 MB")
        try:
            counted = estimator.count_upload(f.filename, data)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception:
            raise HTTPException(status_code=400, detail=f"Could not read {f.filename}")

        results.append({
            "filename": f.filename,
            "file_type": f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else "",
            "size_bytes": len(data),
            "tokens": counted["tokens"],
            "warning": counted["warning"],
        })
    return results


@app.get("/")
def root():
    return {"app": "TokCost API", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/auth/me")
def auth_me(request: Request):
    user = auth.get_optional_user(request)
    if user is None:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "id": str(user["id"]),
        "email": user["email"],
        "role": user["role"],
    }


@app.get("/auth/google/login")
async def auth_google_login(request: Request, pick_account: bool = False):
    if request.query_params.get("pick_account") in ("1", "true", "yes"):
        pick_account = True
    return await auth.google_login(request, pick_account=pick_account)


@app.get("/auth/google/callback")
async def auth_google_callback(request: Request):
    return await auth.google_callback(request)


@app.post("/auth/logout")
def auth_logout(request: Request):
    return auth.logout(request)


@app.post("/count-tokens")
def count_tokens(
    prompt: str = Form(""),
    files: List[UploadFile] = File(default=[]),
):
    prompt_tokens = estimator.count_text(prompt)
    file_results = process_files(files)
    totals = estimator.add_totals(prompt_tokens, *[r["tokens"] for r in file_results])
    return {"prompt": {"tokens": prompt_tokens}, "files": file_results, "totals": totals}


@app.post("/estimate")
def estimate(
    request: Request,
    prompt: str = Form(""),
    files: List[UploadFile] = File(default=[]),
    context_json: str = Form(""),
):
    prompt = prompt.strip()
    if not prompt and not files:
        raise HTTPException(status_code=400, detail="Enter a prompt or attach a file")

    user = auth.get_optional_user(request)

    prompt_tokens = estimator.count_text(prompt)
    file_results = process_files(files)
    totals = estimator.add_totals(prompt_tokens, *[r["tokens"] for r in file_results])

    compression = compress_prompt(prompt, count_tokens_gpt, context_json=context_json)
    analysis = cost_engine.analyze(totals, prompt, [r["file_type"] for r in file_results])
    summary = cost_engine.build_summary(
        prompt, [r["filename"] for r in file_results], totals, analysis
    )

    meta = {
        "prompt_tokens": prompt_tokens,
        "compression": compression,
        "totals": totals,
        "platforms": analysis["platforms"],
        "reason": analysis["reason"],
        "alternatives": analysis.get("alternatives", []),
        "task_type": analysis["task_type"],
        "pricing_last_verified": analysis["pricing_last_verified"],
    }

    session_id = None
    if user is not None:
        try:
            session_id = database.save_session(
                owner_id=str(user["id"]),
                prompt_text=prompt or "(files only)",
                compressed_prompt=compression["compressed"],
                recommended_platform=analysis["recommended"],
                summary=summary,
                title=(prompt or file_results[0]["filename"])[:60],
                files=[
                    {"filename": r["filename"], "file_type": r["file_type"],
                     "size_bytes": r["size_bytes"], "tokens": r["tokens"]}
                    for r in file_results
                ],
                results=[
                    {"platform": p["platform"], "input_tokens": p["input_tokens"],
                     "est_output_tokens": p["est_output_tokens"], "est_cost_usd": p["est_cost_usd"]}
                    for p in analysis["platforms"] if p.get("available") and p["input_tokens"] is not None
                ],
                meta=meta,
            )
        except Exception:
            logger.exception("Could not save session")

    return {
        "session_id": session_id,
        "saved": session_id is not None,
        "prompt": {"text": prompt, "tokens": prompt_tokens},
        "compression": compression,
        "files": file_results,
        "totals": totals,
        "task_type": analysis["task_type"],
        "platforms": analysis["platforms"],
        "recommended": analysis["recommended"],
        "reason": analysis["reason"],
        "alternatives": analysis.get("alternatives", []),
        "summary": summary,
        "pricing_last_verified": analysis["pricing_last_verified"],
    }


@app.post("/sessions")
def create_session(body: SessionIn, user: dict = Depends(auth.get_current_user)):
    session_id = database.save_session(
        owner_id=str(user["id"]),
        prompt_text=body.prompt_text,
        compressed_prompt=body.compressed_prompt,
        recommended_platform=body.recommended_platform,
        summary=body.summary,
        title=body.title,
        files=[f.model_dump() for f in body.files],
        results=[r.model_dump() for r in body.results],
    )
    return {"id": session_id}


@app.get("/sessions")
def get_sessions(user: dict = Depends(auth.get_current_user)):
    return database.list_sessions(str(user["id"]))


@app.get("/sessions/{session_id}")
def get_one_session(session_id: UUID, user: dict = Depends(auth.get_current_user)):
    session = database.get_session(str(session_id), str(user["id"]))
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.patch("/sessions/{session_id}")
def update_session(
    session_id: UUID,
    body: SessionUpdateIn,
    user: dict = Depends(auth.get_current_user),
):
    owner = str(user["id"])
    sid = str(session_id)
    row = None
    if body.title is not None:
        try:
            row = database.update_session_title(sid, owner, body.title)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    if body.pinned is not None:
        row = database.update_session_pinned(sid, owner, body.pinned)
    if body.title is None and body.pinned is None:
        raise HTTPException(status_code=400, detail="No updates provided.")
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return row


@app.delete("/sessions/{session_id}")
def remove_session(session_id: UUID, user: dict = Depends(auth.get_current_user)):
    if not database.soft_delete_session(str(session_id), str(user["id"])):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True, "soft": True}


@app.get("/admin/stats")
def admin_stats(_admin: dict = Depends(auth.require_admin)):
    return database.admin_stats()


@app.get("/admin/users")
def admin_users(_admin: dict = Depends(auth.require_admin)):
    return database.list_users()


@app.patch("/admin/users/{user_id}")
def admin_set_role(
    user_id: UUID,
    body: RoleUpdateIn,
    admin_user: dict = Depends(auth.require_admin),
):
    if str(user_id) == str(admin_user["id"]) and body.role != "admin":
        raise HTTPException(status_code=400, detail="You cannot remove your own admin role.")
    updated = database.update_user_role(str(user_id), body.role)
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    return updated
