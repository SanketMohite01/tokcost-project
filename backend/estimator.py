import tempfile
from pathlib import Path

from token_counter import count_tokens_gpt, count_tokens_claude, count_tokens_gemini
from file_parser import extract_text_from_file, count_image_tokens

PLATFORMS = ("chatgpt", "claude", "gemini")
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
TEXT_EXT = {".pdf", ".docx", ".txt", ".py", ".java", ".js", ".cpp", ".c", ".html", ".css"}

_COUNTERS = {
    "chatgpt": count_tokens_gpt,
    "claude": count_tokens_claude,
    "gemini": count_tokens_gemini,
}


def count_text(text):
    if not text or not text.strip():
        return {p: 0 for p in PLATFORMS}
    result = {}
    for name, fn in _COUNTERS.items():
        try:
            result[name] = fn(text)
        except Exception:
            result[name] = None
    return result


def count_upload(filename, data):
    ext = Path(filename).suffix.lower()
    if ext not in IMAGE_EXT and ext not in TEXT_EXT:
        raise ValueError(f"Unsupported file type: {ext or 'none'}")

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"upload{ext}"
        path.write_bytes(data)

        if ext in IMAGE_EXT:
            return {"tokens": count_image_tokens(str(path)), "warning": None}

        text = extract_text_from_file(str(path))
        warning = None if text.strip() else "No readable text found in this file"
        return {"tokens": count_text(text), "warning": warning}


def add_totals(*token_dicts):
    totals = {}
    for p in PLATFORMS:
        values = [d[p] for d in token_dicts]
        totals[p] = None if any(v is None for v in values) else sum(values)
    return totals