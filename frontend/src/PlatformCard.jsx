import ProviderIcon from "./ProviderIcon.jsx";

const fmt = (n) =>
  n === null || n === undefined ? "n/a" : Number(n).toLocaleString();
const money = (n) =>
  n === null || n === undefined ? "n/a" : "$" + Number(n).toFixed(4);

export default function PlatformCard({ p, best, reason, alternativeReason }) {
  const unavailable = !p.available || p.input_tokens === null || p.input_tokens === undefined;

  return (
    <div className={"pcard" + (best ? " best" : "")}>
      <div className="pcard-top">
        <div className="pcard-brand">
          <ProviderIcon platform={p.platform} />
          <div>
            <span className="pname">{p.name}</span>
            <div className="pmodel muted small">{p.model}</div>
          </div>
        </div>
        {best && <span className="badge">Recommended</span>}
      </div>

      {unavailable ? (
        <div className="pcost small warn-text">
          {p.unavailable_reason || "Token count unavailable right now"}
        </div>
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

      {best && reason && <p className="small card-reason">{reason}</p>}
      {!best && alternativeReason && (
        <p className="small muted card-reason">{alternativeReason}</p>
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
