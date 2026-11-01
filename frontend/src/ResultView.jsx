import PlatformCard from "./PlatformCard.jsx";
import CompressionCard from "./CompressionCard.jsx";

const fmt = (n) =>
  n === null || n === undefined ? "n/a" : Number(n).toLocaleString();

function Stat({ label, value }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

export default function ResultView({ view, onUsePrompt }) {
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

  const altMap = {};
  (view.alternatives || []).forEach((a) => {
    altMap[a.platform] = a.reason;
  });

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

        {(view.alternatives || []).length > 0 && (
          <div className="alternatives panel">
            <div className="panel-title">Alternatives</div>
            <ul className="small muted">
              {view.alternatives.map((a) => (
                <li key={a.platform}>{a.reason}</li>
              ))}
            </ul>
          </div>
        )}

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
            <PlatformCard
              key={p.platform}
              p={p}
              best={p.platform === rec}
              reason={p.platform === rec ? view.reason : undefined}
              alternativeReason={altMap[p.platform]}
            />
          ))}
        </div>

        {hasPrompt && (
          <CompressionCard compression={comp} onUsePrompt={onUsePrompt} />
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
          {view.saved === false && " This estimate was not saved (sign in to save history)."}
        </p>
      </div>
    </div>
  );
}
