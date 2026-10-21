/** Cursor-style context meter for in-session conversation memory. */

export function estimateContextChars(messages, draftText) {
  let total = 0;
  (messages || []).forEach((m) => {
    total += String(m.content || "").length + 20;
  });
  if (draftText && draftText.trim()) {
    total += draftText.length;
  }
  return total;
}

export function approxTokensFromChars(chars) {
  return Math.max(0, Math.ceil(chars / 4));
}

export default function ContextUsage({
  messages,
  draftText,
  enabled,
  charBudget,
  maxMessages,
}) {
  if (!enabled) {
    return (
      <div className="context-usage muted small">
        Context for compression is off. Enable it in Settings.
      </div>
    );
  }

  const usedChars = estimateContextChars(messages, draftText);
  const pct = Math.min(100, Math.round((usedChars / charBudget) * 100));
  const msgCount = (messages || []).length;
  const tokens = approxTokensFromChars(usedChars);

  let level = "ok";
  if (pct >= 90) level = "high";
  else if (pct >= 70) level = "warn";

  return (
    <div className="context-usage">
      <div className="context-usage-head">
        <span className="small">Context</span>
        <span className="small muted">
          ~{tokens.toLocaleString()} tokens · {msgCount}/{maxMessages} messages
        </span>
      </div>
      <div className="context-meter" aria-hidden="true">
        <div
          className={`context-meter-fill ${level}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="small muted context-usage-note">
        {usedChars.toLocaleString()} / {charBudget.toLocaleString()} chars used for
        context-aware compression (this session only).
      </p>
    </div>
  );
}
