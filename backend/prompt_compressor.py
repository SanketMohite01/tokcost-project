import json
import re

CODE_FENCE = re.compile(r"(```.*?```)", re.DOTALL)

REPLACEMENTS = [
    (r"\bin order to\b", "to"),
    (r"\bdue to the fact that\b", "because"),
    (r"\bwith regard to\b", "about"),
    (r"\bat this point in time\b", "now"),
]

FILLERS = [
    r"\bi was wondering if you could\b",
    r"\bi would like you to\b",
    r"\bi would like to\b",
    r"\bi want you to\b",
    r"\bi need you to\b",
    r"\bcould you( please)?\b",
    r"\bcan you( please)?\b",
    r"\bwould you( please)?\b",
    r"\bthank you( so much| very much)?[!.]*",
    r"\bthanks( a lot)?[!.]*",
    r"\bif possible\b",
    r"\bif you can\b",
    r"\bplease\b",
    r"\bkindly\b",
    r"\bbasically\b",
    r"\bactually\b",
    r"\breally\b",
    r"\bjust\b",
]

MAX_CONTEXT_MESSAGES = 8
MAX_CONTEXT_CHARS = 4000


def _compress_plain(segment):
    for pattern, replacement in REPLACEMENTS:
        segment = re.sub(pattern, replacement, segment, flags=re.IGNORECASE)
    for pattern in FILLERS:
        segment = re.sub(pattern, "", segment, flags=re.IGNORECASE)

    segment = re.sub(r"\b(\w+)(\s+\1\b)+", r"\1", segment, flags=re.IGNORECASE)
    segment = re.sub(r"[ \t]+", " ", segment)
    segment = re.sub(r"[ \t]+([,.;:!?])", r"\1", segment)
    segment = re.sub(r"([,;:])(\s*[,;:])+", r"\1", segment)
    segment = re.sub(r"(^|\n)[ \t]*[,;:]\s*", r"\1", segment)
    segment = re.sub(r"[ \t]*\n[ \t]*", "\n", segment)
    segment = re.sub(r"(^|\n)[ \t]+", r"\1", segment)
    segment = re.sub(r"\n{3,}", "\n\n", segment)

    lines = segment.split("\n")
    deduped = []
    for line in lines:
        if line.strip() and deduped and line.strip().lower() == deduped[-1].strip().lower():
            continue
        deduped.append(line)
    segment = "\n".join(deduped)

    segment = re.sub(r"(^|\n)([a-z])", lambda m: m.group(1) + m.group(2).upper(), segment)
    segment = re.sub(r"([.!?] +)([a-z])", lambda m: m.group(1) + m.group(2).upper(), segment)
    return segment


def _compress(text):
    parts = CODE_FENCE.split(text)
    out = []
    for part in parts:
        if part.startswith("```"):
            out.append(part)
        else:
            out.append(_compress_plain(part))
    return "".join(out).strip()


def _safe_count(count_fn, text):
    try:
        return count_fn(text)
    except Exception:
        return len(text.split())


def _parse_context(context_json):
    if not context_json or not str(context_json).strip():
        return []
    try:
        data = json.loads(context_json)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    out = []
    for item in data[-MAX_CONTEXT_MESSAGES:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "user")).lower()
        content = str(item.get("content", "")).strip()
        if content:
            out.append({"role": role, "content": content})
    return out


def _bounded_context_text(messages):
    chunks = []
    total = 0
    for msg in messages:
        line = f"[{msg['role']}]: {msg['content']}"
        if total + len(line) > MAX_CONTEXT_CHARS:
            remain = MAX_CONTEXT_CHARS - total
            if remain > 40:
                chunks.append(line[:remain] + "…")
            break
        chunks.append(line)
        total += len(line)
    return "\n".join(chunks)


def _retained_notes(context_messages, prompt):
    notes = []
    if context_messages:
        notes.append(f"Used {len(context_messages)} prior message(s) from this session for context.")
    if "```" in prompt:
        notes.append("Code blocks in the current prompt were preserved.")
    constraint_hits = re.findall(
        r"\b(MUST|REQUIRED|NEVER|ALWAYS|SHALL)\b[^.\n]{0,80}",
        prompt,
        flags=re.IGNORECASE,
    )
    for hit in constraint_hits[:3]:
        notes.append(f"Constraint retained: {hit.strip()[:80]}")
    return notes


def compress_prompt(text, count_fn, context_json=None):
    empty = {
        "compressed": text or "",
        "raw_tokens": 0,
        "compressed_tokens": 0,
        "saved_tokens": 0,
        "percent": 0.0,
        "summary": "No prompt to compress.",
        "context_messages_used": 0,
        "retained_notes": [],
    }
    if not text or not text.strip():
        return empty

    context_messages = _parse_context(context_json)
    context_block = _bounded_context_text(context_messages)
    retained_notes = _retained_notes(context_messages, text)

    raw_tokens = _safe_count(count_fn, text)
    compressed = _compress(text)
    compressed_tokens = _safe_count(count_fn, compressed)

    if not compressed.strip() or compressed_tokens >= raw_tokens:
        compressed, compressed_tokens = text, raw_tokens

    saved = raw_tokens - compressed_tokens
    percent = round(saved / raw_tokens * 100, 1) if raw_tokens else 0.0

    summary_parts = []
    if saved > 0:
        summary_parts.append(
            f"Shortened the current prompt by {saved} token(s) ({percent}%) while keeping meaning."
        )
    else:
        summary_parts.append("The current prompt is already concise; no meaningful reduction.")
    if context_block:
        summary_parts.append("Earlier turns in this session were considered for constraints, not re-compressed.")

    return {
        "compressed": compressed,
        "raw_tokens": raw_tokens,
        "compressed_tokens": compressed_tokens,
        "saved_tokens": saved,
        "percent": percent,
        "summary": " ".join(summary_parts),
        "context_messages_used": len(context_messages),
        "retained_notes": retained_notes,
        "context_preview": context_block[:500] if context_block else "",
    }
