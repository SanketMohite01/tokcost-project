import { useCallback, useEffect, useState } from "react";
import Sidebar from "./Sidebar.jsx";
import Composer from "./Composer.jsx";
import ResultView from "./ResultView.jsx";
import {
  getOwnerId,
  estimate,
  listSessions,
  getSession,
  deleteSession,
  viewFromEstimate,
  viewFromSession,
} from "./api.js";

export default function App() {
  const [ownerId] = useState(getOwnerId);
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [view, setView] = useState(null);
  const [pending, setPending] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setSessions(await listSessions(ownerId));
    } catch (e) {
      setError(e.message);
    }
  }, [ownerId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  function newEstimate() {
    setView(null);
    setPending(null);
    setActiveId(null);
    setError("");
    setSidebarOpen(false);
  }

  async function submit(prompt, files) {
    setError("");
    setView(null);
    setActiveId(null);
    setPending({ text: prompt, files: files.map((f) => f.name) });
    setLoading(true);
    try {
      const data = await estimate(ownerId, prompt, files);
      setView(viewFromEstimate(data, prompt, files));
      setActiveId(data.session_id);
      setPending(null);
      refresh();
      return true;
    } catch (e) {
      setError(e.message);
      setPending(null);
      return false;
    } finally {
      setLoading(false);
    }
  }

  async function openSession(id) {
    setError("");
    setPending(null);
    try {
      const s = await getSession(ownerId, id);
      setView(viewFromSession(s));
      setActiveId(id);
    } catch (e) {
      setError(e.message);
    }
  }

  async function removeSession(id) {
    if (!window.confirm("Delete this estimate?")) return;
    try {
      await deleteSession(ownerId, id);
      if (id === activeId) {
        setView(null);
        setActiveId(null);
      }
      refresh();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="app">
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        onNew={newEstimate}
        onSelect={openSession}
        onDelete={removeSession}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      {sidebarOpen && (
        <div className="scrim" onClick={() => setSidebarOpen(false)} />
      )}

      <main className="main">
        <header className="topbar">
          <button
            className="menu-btn"
            aria-label="Open history"
            onClick={() => setSidebarOpen(true)}
          >
            ☰
          </button>
          <span className="topbar-title">TokCost</span>
        </header>

        <div className="scroll">
          {!view && !pending && (
            <div className="empty">
              <h1>Know your tokens before you ask</h1>
              <p className="muted">
                Add a prompt and any files. TokCost compares token counts and
                cost across ChatGPT, Claude, and Gemini.
              </p>
            </div>
          )}

          {pending && (
            <div className="thread">
              <div className="user-bubble">
                {pending.text.trim() && (
                  <div className="user-text">{pending.text}</div>
                )}
                {pending.files.length > 0 && (
                  <div className="chips">
                    {pending.files.map((n, i) => (
                      <span className="chip static" key={n + i}>
                        {n}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div className="answer">
                <p className="lead muted">
                  Counting tokens across three platforms…
                </p>
              </div>
            </div>
          )}

          {view && <ResultView view={view} />}
        </div>

        <div className="bottom">
          {error && <div className="error">{error}</div>}
          <Composer onSubmit={submit} loading={loading} />
        </div>
      </main>
    </div>
  );
}
