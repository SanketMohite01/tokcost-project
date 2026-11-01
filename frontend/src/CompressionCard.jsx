import { useState } from "react";

export default function CompressionCard({ compression, onUsePrompt }) {
  const [copied, setCopied] = useState(false);
  const [open, setOpen] = useState(false);
  const comp = compression || {};

  async function copyPrompt() {
    const text = comp.compressed || "";
    if (!text) return;
    let ok = false;
    try {
      await navigator.clipboard.writeText(text);
      ok = true;
    } catch (e) {
      try {
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        ok = document.execCommand("copy");
        document.body.removeChild(ta);
      } catch (e2) {
        ok = false;
      }
    }
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  }

  function usePrompt() {
    if (comp.compressed && onUsePrompt) onUsePrompt(comp.compressed);
  }

  return (
    <div className="panel compression-card">
      <div className="panel-head">
        <span className="panel-title">Compressed prompt</span>
        <div className="panel-actions">
          <button type="button" className="ghost" onClick={copyPrompt}>
            {copied ? "Copied" : "Copy Prompt"}
          </button>
          <button type="button" className="ghost" onClick={usePrompt}>
            Use Prompt
          </button>
          <button
            type="button"
            className="ghost"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
          >
            {open ? "Hide" : "Show"} full text
          </button>
        </div>
      </div>

      <p className="small compression-summary">{comp.summary || "Compression complete."}</p>

      {comp.context_messages_used > 0 && (
        <p className="small muted">
          Context from {comp.context_messages_used} earlier message(s) in this session was
          considered.
        </p>
      )}

      {(comp.retained_notes || []).length > 0 && (
        <ul className="retained-notes small muted">
          {comp.retained_notes.map((n, i) => (
            <li key={i}>{n}</li>
          ))}
        </ul>
      )}

      {open && <div className="panel-body compression-body">{comp.compressed}</div>}

      <div className="small muted">
        {comp.saved_tokens > 0
          ? `Saves ${comp.saved_tokens} token(s) (${comp.percent}%) on the current prompt.`
          : "This prompt is already concise."}
      </div>
    </div>
  );
}
