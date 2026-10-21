import { useEffect, useRef, useState } from "react";

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

function HistoryMenu({ session, onRename, onDelete, onPin, onClose }) {
  const ref = useRef(null);

  useEffect(() => {
    function onDoc(e) {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [onClose]);

  const pinned = Boolean(session.pinned_at);

  return (
    <div className="history-menu" ref={ref} onClick={(e) => e.stopPropagation()}>
      <button type="button" onClick={() => { onRename(session); onClose(); }}>
        Rename
      </button>
      <button type="button" onClick={() => { onPin(session.id, !pinned); onClose(); }}>
        {pinned ? "Unpin" : "Pin"}
      </button>
      <button type="button" className="danger" onClick={() => { onDelete(session.id); onClose(); }}>
        Delete
      </button>
    </div>
  );
}

export default function Sidebar({
  sessions,
  activeId,
  authenticated,
  onNew,
  onSelect,
  onDelete,
  onRename,
  onPin,
  onOpenSettings,
  open,
  onClose,
}) {
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const [menuId, setMenuId] = useState(null);

  const pinned = sessions.filter((s) => s.pinned_at);
  const unpinned = sessions.filter((s) => !s.pinned_at);

  function buildGroups(list) {
    const groups = [];
    list.forEach((s) => {
      const label = groupLabel(s.created_at);
      let g = groups.find((x) => x.label === label);
      if (!g) {
        g = { label, items: [] };
        groups.push(g);
      }
      g.items.push(s);
    });
    return groups;
  }

  function startRename(s) {
    setEditingId(s.id);
    setEditTitle(s.title || "Untitled");
    setMenuId(null);
  }

  async function commitRename(id) {
    const title = editTitle.trim();
    if (title) await onRename(id, title);
    setEditingId(null);
  }

  function renderItem(s) {
    return (
      <div
        key={s.id}
        className={"history-item" + (s.id === activeId ? " active" : "")}
        onClick={() => {
          if (editingId !== s.id && menuId !== s.id) {
            onSelect(s.id);
            onClose();
          }
        }}
      >
        {editingId === s.id ? (
          <input
            className="rename-input"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") commitRename(s.id);
              if (e.key === "Escape") setEditingId(null);
            }}
            onBlur={() => commitRename(s.id)}
            autoFocus
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span className="history-title">
            {s.pinned_at && <span className="pin-icon" title="Pinned">📌</span>}
            {s.title || "Untitled"}
          </span>
        )}
        {authenticated && editingId !== s.id && (
          <div className="history-actions">
            <button
              type="button"
              className="kebab"
              aria-label="Chat options"
              aria-expanded={menuId === s.id}
              onClick={(e) => {
                e.stopPropagation();
                setMenuId(menuId === s.id ? null : s.id);
              }}
            >
              ⋮
            </button>
            {menuId === s.id && (
              <HistoryMenu
                session={s}
                onRename={startRename}
                onDelete={onDelete}
                onPin={onPin}
                onClose={() => setMenuId(null)}
              />
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <aside className={"sidebar" + (open ? " open" : "")}>
      <div className="brand">
        <span className="brand-mark">T</span>
        <span className="brand-name">TokCost</span>
      </div>

      <button type="button" className="new-btn" onClick={onNew}>
        <span aria-hidden="true">+</span> New estimate
      </button>

      <div className="history">
        {!authenticated && (
          <p className="muted small pad">
            Sign in with Google to see saved estimates here.
          </p>
        )}
        {authenticated && sessions.length === 0 && (
          <p className="muted small pad">Your estimates will appear here.</p>
        )}
        {pinned.length > 0 && (
          <div>
            <div className="group-label">Pinned</div>
            {pinned.map(renderItem)}
          </div>
        )}
        {buildGroups(unpinned).map((g) => (
          <div key={g.label}>
            <div className="group-label">{g.label}</div>
            {g.items.map(renderItem)}
          </div>
        ))}
      </div>

      <div className="sidebar-footer">
        <button type="button" className="settings-foot-btn" onClick={onOpenSettings}>
          ⚙ Settings
        </button>
      </div>
    </aside>
  );
}
