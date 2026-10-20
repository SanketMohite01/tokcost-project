function groupLabel(iso) {
  const d = new Date(iso);
  const start = (x) =>
    new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const days = Math.round((start(new Date()) - start(d)) / 86400000);
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return "Previous 7 days";
  return "Older";
}

export default function Sidebar({
  sessions,
  activeId,
  onNew,
  onSelect,
  onDelete,
  open,
  onClose,
}) {
  const groups = [];
  sessions.forEach((s) => {
    const label = groupLabel(s.created_at);
    let g = groups.find((x) => x.label === label);
    if (!g) {
      g = { label, items: [] };
      groups.push(g);
    }
    g.items.push(s);
  });

  return (
    <aside className={"sidebar" + (open ? " open" : "")}>
      <div className="brand">
        <span className="brand-mark">T</span>
        <span className="brand-name">TokCost</span>
      </div>

      <button className="new-btn" onClick={onNew}>
        <span aria-hidden="true">+</span> New estimate
      </button>

      <div className="history">
        {sessions.length === 0 && (
          <p className="muted small pad">Your estimates will appear here.</p>
        )}
        {groups.map((g) => (
          <div key={g.label}>
            <div className="group-label">{g.label}</div>
            {g.items.map((s) => (
              <div
                key={s.id}
                className={
                  "history-item" + (s.id === activeId ? " active" : "")
                }
                onClick={() => {
                  onSelect(s.id);
                  onClose();
                }}
              >
                <span className="history-title">{s.title || "Untitled"}</span>
                <button
                  className="del"
                  aria-label="Delete estimate"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(s.id);
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        ))}
      </div>
    </aside>
  );
}
