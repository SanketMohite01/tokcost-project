import logging
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import cost_engine
import database
import estimator
from prompt_compressor import compress_prompt
from token_counter import count_tokens_gpt

logger = logging.getLogger("tokcost")

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_FILES = 5

app = FastAPI(title="TokCost API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
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
    prompt: str = Form(""),
    files: List[UploadFile] = File(default=[]),
    x_owner_id: str = Header(...),
):
    prompt = prompt.strip()
    if not prompt and not files:
        raise HTTPException(status_code=400, detail="Enter a prompt or attach a file")

    prompt_tokens = estimator.count_text(prompt)
    file_results = process_files(files)
    totals = estimator.add_totals(prompt_tokens, *[r["tokens"] for r in file_results])

    compression = compress_prompt(prompt, count_tokens_gpt)
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
        "task_type": analysis["task_type"],
        "pricing_last_verified": analysis["pricing_last_verified"],
    }

    session_id = None
    try:
        session_id = database.save_session(
            owner_id=x_owner_id,
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
                for p in analysis["platforms"] if p["input_tokens"] is not None
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
        "summary": summary,
        "pricing_last_verified": analysis["pricing_last_verified"],
    }


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