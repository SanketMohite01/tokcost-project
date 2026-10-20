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


def compress_prompt(text, count_fn):
    if not text or not text.strip():
        return {"compressed": text, "raw_tokens": 0, "compressed_tokens": 0,
                "saved_tokens": 0, "percent": 0.0}

    raw_tokens = _safe_count(count_fn, text)
    compressed = _compress(text)
    compressed_tokens = _safe_count(count_fn, compressed)

    if not compressed.strip() or compressed_tokens >= raw_tokens:
        compressed, compressed_tokens = text, raw_tokens

    saved = raw_tokens - compressed_tokens
    percent = round(saved / raw_tokens * 100, 1) if raw_tokens else 0.0
    return {"compressed": compressed, "raw_tokens": raw_tokens,
            "compressed_tokens": compressed_tokens, "saved_tokens": saved, "percent": percent}