import json
import re
from collections import Counter

CODE_FENCE = re.compile(r"(```.*?```)", re.DOTALL)
WORD = re.compile(r"[A-Za-z0-9']+")
NUMBER = re.compile(r"\d+(?:[-\u2013.,]\d+)*")

REPLACEMENTS = [
    (r"\bin order to\b", "to"),
    (r"\bdue to the fact that\b", "because"),
    (r"\bwith regard to\b", "about"),
    (r"\bat this point in time\b", "now"),
]

FILLERS = [
    r"\bi would appreciate it if you could\b",
    r"\bit would be great if you could\b",
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
    r"\bplease note that\b",
    r"\bfeel free to\b",
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
MIN_REPEAT_WORDS = 6
MAX_REPEAT_WORDS = 14
MAX_WORDS_SCANNED = 3000


def _compress_plain(segment, removed):
    for pattern, replacement in REPLACEMENTS:
        def swap(m, replacement=replacement):
            removed.append(f"{m.group(0).lower()} \u2192 {replacement}")
            return replacement
        segment = re.sub(pattern, swap, segment, flags=re.IGNORECASE)

    for pattern in FILLERS:
        def drop(m):
            removed.append(m.group(0).strip().lower())
            return ""
        segment = re.sub(pattern, drop, segment, flags=re.IGNORECASE)

    # Only collapse repeated *letters-only* words ("the the"), never numbers.
    segment = re.sub(r"\b([A-Za-z]+)(\s+\1\b)+", r"\1", segment, flags=re.IGNORECASE)
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
    removed = []
    parts = CODE_FENCE.split(text)
    out = []
    for part in parts:
        if part.startswith("```"):
            out.append(part)
        else:
            out.append(_compress_plain(part, removed))
    return "".join(out).strip(), removed


def _safe_count(count_fn, text):
    try:
        return count_fn(text)
    except Exception:
        return len(text.split())


def _numbers_preserved(original, compressed):
    need = Counter(NUMBER.findall(original))
    have = Counter(NUMBER.findall(compressed))
    return all(have[k] >= v for k, v in need.items())


def _unique(items):
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _find_repeated_phrases(text, limit=3):
    """Find phrases of 6+ words that appear at least twice (outside code blocks).
    These are reported as suggestions only. They are never removed automatically,
    because a repeated phrase can mean something different each time."""
    plain = CODE_FENCE.sub(lambda m: " " * len(m.group(0)), text)
    toks = [(m.group(0).lower(), m.start(), m.end()) for m in WORD.finditer(plain)]
    toks = toks[:MAX_WORDS_SCANNED]
    words = [t[0] for t in toks]
    taken = [False] * len(words)
    found = []

    top = min(MAX_REPEAT_WORDS, len(words) // 2)
    for n in range(top, MIN_REPEAT_WORDS - 1, -1):
        seen = {}
        for i in range(len(words) - n + 1):
            seen.setdefault(tuple(words[i:i + n]), []).append(i)
        for positions in seen.values():
            keep = []
            for p in positions:
                if any(taken[p:p + n]):
                    continue
                if not keep or p >= keep[-1] + n:
                    keep.append(p)
            if len(keep) >= 2:
                for p in keep:
                    for j in range(p, p + n):
                        taken[j] = True
                start, end = toks[keep[0]][1], toks[keep[0] + n - 1][2]
                found.append((n, text[start:end], len(keep)))

    found.sort(key=lambda x: -x[0])
    out = []
    for _, phrase, count in found[:limit]:
        phrase = phrase.strip()
        if phrase.count("(") > phrase.count(")"):
            phrase += ")"
        if len(phrase) > 90:
            phrase = phrase[:87].rstrip() + "..."
        out.append({"phrase": phrase, "times": count})
    return out


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
                chunks.append(line[:remain] + "\u2026")
            break
        chunks.append(line)
        total += len(line)
    return "\n".join(chunks)


def _retained_notes(context_messages, prompt):
    notes = []
    if context_messages:
        notes.append(f"{len(context_messages)} earlier message(s) from this session are shown for reference only.")
    if "```" in prompt:
        notes.append("Code blocks in the prompt were left exactly as written.")
    numbers = _unique(NUMBER.findall(prompt))
    if numbers:
        shown = ", ".join(numbers[:6]) + (" ..." if len(numbers) > 6 else "")
        notes.append(f"Numbers and limits left exactly as written: {shown}")
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
        "suggestions": [],
    }
    if not text or not text.strip():
        return empty

    context_messages = _parse_context(context_json)
    context_block = _bounded_context_text(context_messages)
    retained_notes = _retained_notes(context_messages, text)
    suggestions = _find_repeated_phrases(text)

    raw_tokens = _safe_count(count_fn, text)
    compressed, removed = _compress(text)
    compressed_tokens = _safe_count(count_fn, compressed)

    unsafe = not _numbers_preserved(text, compressed)
    if unsafe or not compressed.strip() or compressed_tokens >= raw_tokens:
        compressed, compressed_tokens, removed = text, raw_tokens, []

    saved = raw_tokens - compressed_tokens
    percent = round(saved / raw_tokens * 100, 1) if raw_tokens else 0.0

    parts = []
    if saved > 0:
        shown = ", ".join('"' + r + '"' for r in _unique(removed)[:5])
        parts.append(f"Shortened by {saved} token(s) ({percent}%).")
        if shown:
            parts.append(f"Removed: {shown}.")
    else:
        parts.append(
            "No filler words or repeated words were found, so the rules changed nothing. "
            "The prompt is already direct."
        )
    for s in suggestions:
        parts.append(
            f'Possible repetition (left unchanged): "{s["phrase"]}" appears {s["times"]} times. '
            "If both mean the same thing, say it once."
        )
    if context_block:
        parts.append("Earlier messages did not change this result.")

    return {
        "compressed": compressed,
        "raw_tokens": raw_tokens,
        "compressed_tokens": compressed_tokens,
        "saved_tokens": saved,
        "percent": percent,
        "summary": " ".join(parts),
        "context_messages_used": len(context_messages),
        "retained_notes": retained_notes,
        "context_preview": context_block[:500] if context_block else "",
        "suggestions": suggestions,
    }