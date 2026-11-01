import json
import os
from pathlib import Path

CONFIG = json.loads(Path(__file__).with_name("pricing_config.json").read_text(encoding="utf-8"))
PLATFORM_ORDER = ["chatgpt", "claude", "gemini"]

CODE_TYPES = {"py", "java", "js", "cpp", "c", "html", "css"}
IMAGE_TYPES = {"png", "jpg", "jpeg", "webp", "gif"}
CODE_WORDS = ("code", "debug", "function", "bug", "refactor", "error", "script", "implement", "typescript", "python")
SUMMARY_WORDS = ("summar", "tl;dr", "brief", "key points", "overview")
REASONING_WORDS = (
    "analyze", "reason", "logic", "prove", "step by step", "compare", "evaluate",
    "trade-off", "architecture", "complex", "math", "theorem",
)
CREATIVE_WORDS = (
    "story", "poem", "creative", "brainstorm", "marketing", "slogan", "fiction",
    "narrative", "write a", "blog post",
)

# task type: (output as a share of input tokens, minimum output, maximum output)
OUTPUT_RULES = {
    "summary": (0.10, 150, 800),
    "code": (0.50, 300, 2000),
    "image": (0.00, 250, 600),
    "reasoning": (0.35, 250, 1800),
    "creative": (0.40, 200, 1600),
    "general": (0.30, 200, 1500),
}

# Higher weight = better fit for task (deterministic, config-bound platforms only)
TASK_FIT = {
    "code": {"chatgpt": 92, "claude": 90, "gemini": 78},
    "summary": {"chatgpt": 85, "claude": 86, "gemini": 84},
    "image": {"chatgpt": 88, "claude": 82, "gemini": 86},
    "reasoning": {"chatgpt": 86, "claude": 92, "gemini": 80},
    "creative": {"chatgpt": 90, "claude": 88, "gemini": 76},
    "general": {"chatgpt": 84, "claude": 84, "gemini": 80},
}

FIT_TIE_BAND = 5


def _gemini_configured():
    return bool(os.getenv("GOOGLE_API_KEY", "").strip())


def detect_task(prompt, file_types):
    lower = (prompt or "").lower()
    types = {t.lower() for t in file_types}
    if types & CODE_TYPES or any(w in lower for w in CODE_WORDS):
        return "code"
    if any(w in lower for w in SUMMARY_WORDS):
        return "summary"
    if types & IMAGE_TYPES:
        return "image"
    if any(w in lower for w in REASONING_WORDS):
        return "reasoning"
    if any(w in lower for w in CREATIVE_WORDS):
        return "creative"
    return "general"


def estimate_output_tokens(input_tokens, task):
    ratio, low, high = OUTPUT_RULES.get(task, OUTPUT_RULES["general"])
    return int(min(high, max(low, input_tokens * ratio)))


def platform_cost(platform, input_tokens, output_tokens):
    p = CONFIG["platforms"][platform]
    cost = (input_tokens / 1_000_000) * p["input_per_million"]
    cost += (output_tokens / 1_000_000) * p["output_per_million"]
    return round(cost, 6)


def _platform_available(platform, tokens):
    return tokens is not None


def _fit_score(platform, task):
    return TASK_FIT.get(task, TASK_FIT["general"]).get(platform, 70)


def _pick_recommendation(priced_rows, task):
    if not priced_rows:
        return None, "No platform could be priced for this input.", []

    max_fit = max(r["fit_score"] for r in priced_rows)
    top_fit = [r for r in priced_rows if r["fit_score"] >= max_fit - FIT_TIE_BAND]

    # Among similarly suitable providers, prefer lower estimated cost.
    ranked = sorted(top_fit, key=lambda r: (r["est_cost_usd"], -r["fit_score"]))
    best = ranked[0]
    name = best["name"]
    reason = (
        f"{name} ({best['model']}) is a strong fit for this {task} task and has the "
        f"lowest estimated cost among suitable options (${best['est_cost_usd']:.4f})."
    )

    alternatives = []
    for r in ranked[1:3]:
        note = (
            f"Also suitable for {task}; estimated cost {r['est_cost_usd']:.4f} USD "
            f"vs {best['est_cost_usd']:.4f} for {name}."
        )
        alternatives.append({"platform": r["platform"], "reason": note})

    if len(ranked) > 1 and ranked[1]["fit_score"] == best["fit_score"]:
        cheaper = min(ranked[:3], key=lambda r: r["est_cost_usd"])
        if cheaper["platform"] != best["platform"] and cheaper["est_cost_usd"] < best["est_cost_usd"]:
            alternatives.insert(
                0,
                {
                    "platform": cheaper["platform"],
                    "reason": (
                        f"Similar fit for {task} with lower estimated cost "
                        f"(${cheaper['est_cost_usd']:.4f})."
                    ),
                },
            )

    return best["platform"], reason, alternatives


def analyze(totals, prompt, file_types):
    task = detect_task(prompt, file_types)
    rows = []
    priced_candidates = []

    for key in PLATFORM_ORDER:
        info = CONFIG["platforms"][key]
        tokens = totals.get(key)
        available = _platform_available(key, tokens)
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
            "available": available,
            "fit_score": _fit_score(key, task) if available else None,
        }
        if available:
            out = estimate_output_tokens(tokens, task)
            row["est_output_tokens"] = out
            row["est_cost_usd"] = platform_cost(key, tokens, out)
            priced_candidates.append(row)
        elif tokens is None:
            row["unavailable_reason"] = "Token count unavailable for this provider right now."
        elif key == "gemini" and not _gemini_configured():
            row["unavailable_reason"] = "Gemini token counting is not configured (missing GOOGLE_API_KEY)."
        rows.append(row)

    recommended, reason, alternatives = _pick_recommendation(priced_candidates, task)

    return {
        "task_type": task,
        "platforms": rows,
        "recommended": recommended,
        "reason": reason,
        "alternatives": alternatives,
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
            f"Recommended: {best['name']} ({best['model']}) for this {analysis['task_type']} task, "
            f"about {best['input_tokens']:,} input tokens, estimated ${best['est_cost_usd']:.4f}."
        )
    return " ".join(parts)
