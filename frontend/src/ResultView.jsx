import { useState } from "react";

const fmt = (n) =>
  n === null || n === undefined ? "n/a" : Number(n).toLocaleString();
const money = (n) =>
  n === null || n === undefined ? "n/a" : "$" + Number(n).toFixed(4);

function Stat({ label, value }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

function PlatformCard({ p, best }) {
  const unavailable = p.input_tokens === null || p.input_tokens === undefined;
  return (
    <div className={"pcard" + (best ? " best" : "")}>
      <div className="pcard-top">
        <span className="pname">{p.name}</span>
        {best && <span className="badge">Best fit</span>}
      </div>
      <div className="pmodel muted small">{p.model}</div>
      {unavailable ? (
        <div className="pcost small">Token count unavailable right now</div>
      ) : (
        <>
          <div className="pcost">{money(p.est_cost_usd)}</div>
          <div className="small muted">
            {fmt(p.input_tokens)} input tokens
            {p.approximate_tokens ? " (approx.)" : ""}
          </div>
          <div className="small muted">
            about {fmt(p.est_output_tokens)} output tokens
          </div>
        </>
      )}
      <div className="small muted tier">{p.free_tier}</div>
      <div className="small muted">{p.paid_tier}</div>
      <a
        className="plink"
        href={p.url}
        target="_blank"
        rel="noopener noreferrer"
      >
        Open {p.name} ↗
      </a>
    </div>
  );
}

export default function ResultView({ view }) {
  const [copied, setCopied] = useState(false);
  const rec = view.recommended;
  const promptTok = rec ? view.promptTokens[rec] : null;
  const totalTok = rec ? view.totals[rec] : null;
  const fileTok =
    promptTok !== null &&
    promptTok !== undefined &&
    totalTok !== null &&
    totalTok !== undefined
      ? totalTok - promptTok
      : null;
  const comp = view.compression || {};
  const hasPrompt = view.userMessage.text.trim().length > 0;

  async function copyCompressed() {
    const text = comp.compressed || "";
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

  return (
    <div className="thread">
      <div className="user-bubble">
        {hasPrompt && <div className="user-text">{view.userMessage.text}</div>}
        {view.userMessage.files.length > 0 && (
          <div className="chips">
            {view.userMessage.files.map((f, i) => (
              <span className="chip static" key={f.filename + i}>
                {f.filename}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="answer">
        <p className="lead">{view.reason}</p>

        <div className="stats">
          <Stat label="Prompt tokens" value={fmt(promptTok)} />
          <Stat label="File tokens" value={fmt(fileTok)} />
          <Stat
            label="Saved by compression"
            value={(comp.percent || 0) + "%"}
          />
        </div>

        <div className="pgrid">
          {view.platforms.map((p) => (
            <PlatformCard key={p.platform} p={p} best={p.platform === rec} />
          ))}
        </div>

        {hasPrompt && (
          <div className="panel">
            <div className="panel-head">
              <span className="panel-title">Compressed prompt</span>
              <button className="ghost" onClick={copyCompressed}>
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
            <div className="panel-body">{comp.compressed}</div>
            <div className="small muted">
              {comp.saved_tokens > 0
                ? "Saves " +
                  comp.saved_tokens +
                  (comp.saved_tokens === 1 ? " token (" : " tokens (") +
                  comp.percent +
                  "%) on the prompt."
                : "This prompt is already concise."}
            </div>
          </div>
        )}

        {view.files.length > 0 && (
          <div className="panel">
            <div className="panel-title">Files</div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>File</th>
                    <th>ChatGPT</th>
                    <th>Claude</th>
                    <th>Gemini</th>
                  </tr>
                </thead>
                <tbody>
                  {view.files.map((f, i) => (
                    <tr key={f.filename + i}>
                      <td>
                        {f.filename}
                        {f.warning && (
                          <div className="small warn">{f.warning}</div>
                        )}
                      </td>
                      <td>{fmt(f.tokens && f.tokens.chatgpt)}</td>
                      <td>{fmt(f.tokens && f.tokens.claude)}</td>
                      <td>{fmt(f.tokens && f.tokens.gemini)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <div className="panel">
          <div className="panel-title">Summary</div>
          <div className="panel-body">{view.summary}</div>
        </div>

        <p className="small muted">
          {view.pricingLastVerified
            ? "Prices last verified " + view.pricingLastVerified + "."
            : "Costs use the prices in pricing_config.json. Verify them before relying on the numbers."}
          {view.saved ? "" : " This estimate was not saved to history."}
        </p>
      </div>
    </div>
  );
}
