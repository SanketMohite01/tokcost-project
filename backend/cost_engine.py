import json
from pathlib import Path

CONFIG = json.loads(Path(__file__).with_name("pricing_config.json").read_text(encoding="utf-8"))
PLATFORM_ORDER = ["chatgpt", "claude", "gemini"]

CODE_TYPES = {"py", "java", "js", "cpp", "c", "html", "css"}
IMAGE_TYPES = {"png", "jpg", "jpeg", "webp", "gif"}
CODE_WORDS = ("code", "debug", "function", "bug", "refactor", "error", "script")
SUMMARY_WORDS = ("summar", "tl;dr", "brief", "key points", "overview")

# task type: (output as a share of input tokens, minimum output, maximum output)
OUTPUT_RULES = {
    "summary": (0.10, 150, 800),
    "code": (0.50, 300, 2000),
    "image": (0.00, 250, 600),
    "general": (0.30, 200, 1500),
}


def detect_task(prompt, file_types):
    lower = (prompt or "").lower()
    types = {t.lower() for t in file_types}
    if types & CODE_TYPES or any(w in lower for w in CODE_WORDS):
        return "code"
    if any(w in lower for w in SUMMARY_WORDS):
        return "summary"
    if types & IMAGE_TYPES:
        return "image"
    return "general"


def estimate_output_tokens(input_tokens, task):
    ratio, low, high = OUTPUT_RULES[task]
    return int(min(high, max(low, input_tokens * ratio)))


def platform_cost(platform, input_tokens, output_tokens):
    p = CONFIG["platforms"][platform]
    cost = (input_tokens / 1_000_000) * p["input_per_million"]
    cost += (output_tokens / 1_000_000) * p["output_per_million"]
    return round(cost, 6)


def analyze(totals, prompt, file_types):
    task = detect_task(prompt, file_types)
    rows = []
    for key in PLATFORM_ORDER:
        info = CONFIG["platforms"][key]
        tokens = totals.get(key)
        row = {
            "platform": key,
            "name": info["name"],
            "model": info["model"],
            "approximate_tokens": info["approximate_tokens"],
            "free_tier": info["free_tier"],
            "paid_tier": info["paid_tier"],
            "url": info["url"],
            "input_tokens": tokens,
            "est_output_tokens": None,
            "est_cost_usd": None,
        }
        if tokens is not None:
            out = estimate_output_tokens(tokens, task)
            row["est_output_tokens"] = out
            row["est_cost_usd"] = platform_cost(key, tokens, out)
        rows.append(row)

    priced = [r for r in rows if r["est_cost_usd"] is not None]
    recommended, reason = None, "No platform could be priced for this input."
    if priced:
        best = min(priced, key=lambda r: r["est_cost_usd"])
        recommended = best["platform"]
        reason = f"{best['name']} has the lowest estimated cost for this {task} task."

    return {
        "task_type": task,
        "platforms": rows,
        "recommended": recommended,
        "reason": reason,
        "pricing_last_verified": CONFIG.get("last_verified"),
    }


def build_summary(prompt, file_names, totals, analysis):
    text = (prompt or "").strip().replace("\n", " ")
    if len(text) > 80:
        text = text[:80].rstrip() + "..."
    parts = [f'Prompt: "{text}".' if text else "No text prompt."]
    if file_names:
        parts.append(f"{len(file_names)} file(s) attached: {', '.join(file_names)}.")
    best = next((r for r in analysis["platforms"] if r["platform"] == analysis["recommended"]), None)
    if best:
        parts.append(
            f"Estimated input is about {best['input_tokens']:,} tokens on {best['name']}, "
            f"which is the cheapest option at about ${best['est_cost_usd']:.4f}."
        )
    return " ".join(parts)