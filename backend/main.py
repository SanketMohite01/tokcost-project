from typing import Dict, List, Optional
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database

app = FastAPI(title="TokCost API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/")
def root():
    return {"app": "TokCost API", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/sessions")
def create_session(body: SessionIn, x_owner_id: str = Header(...)):
    session_id = database.save_session(
        owner_id=x_owner_id,
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
def get_sessions(x_owner_id: str = Header(...)):
    return database.list_sessions(x_owner_id)


@app.get("/sessions/{session_id}")
def get_one_session(session_id: UUID, x_owner_id: str = Header(...)):
    session = database.get_session(str(session_id), x_owner_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.delete("/sessions/{session_id}")
def remove_session(session_id: UUID, x_owner_id: str = Header(...)):
    if not database.delete_session(str(session_id), x_owner_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True}