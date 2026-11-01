import { useCallback, useEffect, useState } from "react";
import Sidebar from "./Sidebar.jsx";
import Composer from "./Composer.jsx";
import ResultView from "./ResultView.jsx";
import SettingsPanel from "./SettingsPanel.jsx";
import ContextUsage from "./ContextUsage.jsx";
import { useAuth } from "./AuthContext.jsx";
import { loadSettings, saveSettings } from "./settingsStore.js";
import {
  estimate,
  listSessions,
  getSession,
  deleteSession,
  renameSession,
  pinSession,
  viewFromEstimate,
  viewFromSession,
} from "./api.js";

export default function App() {
  const {
    user,
    loading: authLoading,
    loginUrl,
    switchAccountUrl,
    logout,
    isAdmin,
  } = useAuth();
  const [settings, setSettings] = useState(loadSettings);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [view, setView] = useState(null);
  const [pending, setPending] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [composerText, setComposerText] = useState("");
  const [conversationContext, setConversationContext] = useState([]);

  const maxContextMessages = settings.maxContextMessages;

  const refresh = useCallback(async () => {
    if (!user) {
      setSessions([]);
      return;
    }
    try {
      setSessions(await listSessions());
    } catch (e) {
      setError(e.message);
    }
  }, [user]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  function updateSettings(partial) {
    setSettings(saveSettings(partial));
  }

  function newEstimate() {
    setView(null);
    setPending(null);
    setActiveId(null);
    setError("");
    setSidebarOpen(false);
    setConversationContext([]);
    setComposerText("");
  }

  async function submit(prompt, files) {
    setError("");
    setView(null);
    setActiveId(null);
    setPending({ text: prompt, files: files.map((f) => f.name) });
    setLoading(true);
    try {
      const contextForApi = settings.contextEnabled
        ? conversationContext.slice(-maxContextMessages)
        : [];
      const data = await estimate(prompt, files, contextForApi);
      const nextView = viewFromEstimate(data, prompt, files);
      setView(nextView);
      setActiveId(data.session_id);
      setPending(null);

      setConversationContext((prev) => {
        const next = [
          ...prev,
          { role: "user", content: prompt },
          {
            role: "assistant",
            content: data.summary || data.reason || "Estimate complete.",
          },
        ];
        return next.slice(-maxContextMessages);
      });

      if (user) refresh();
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
    if (!user) {
      setError("Sign in with Google to open saved estimates.");
      return;
    }
    setError("");
    setPending(null);
    try {
      const s = await getSession(id);
      setView(viewFromSession(s));
      setActiveId(id);
      setConversationContext([
        {
          role: "user",
          content: s.prompt_text === "(files only)" ? "" : s.prompt_text,
        },
        { role: "assistant", content: s.summary || "" },
      ]);
    } catch (e) {
      setError(e.message);
    }
  }

  async function removeSession(id) {
    if (!user) return;
    if (!window.confirm("Delete this estimate? It will be hidden from your history.")) return;
    try {
      await deleteSession(id);
      if (id === activeId) {
        setView(null);
        setActiveId(null);
      }
      refresh();
    } catch (e) {
      setError(e.message);
    }
  }

  async function onRenameSession(id, title) {
    if (!user) return;
    try {
      await renameSession(id, title);
      refresh();
    } catch (e) {
      setError(e.message);
    }
  }

  async function onPinSession(id, pinned) {
    if (!user) return;
    try {
      await pinSession(id, pinned);
      refresh();
    } catch (e) {
      setError(e.message);
    }
  }

  function handleUsePrompt(text) {
    setComposerText(text);
    const el = document.querySelector(".composer textarea");
    if (el) el.focus();
  }

  const sidebarHidden = settings.sidebarHidden;

  async function switchGoogleAccount() {
    await logout();
    window.location.href = switchAccountUrl;
  }

  function showSidebar() {
    updateSettings({ sidebarHidden: false });
    setSidebarOpen(true);
  }

  function hideSidebar() {
    updateSettings({ sidebarHidden: true });
    setSidebarOpen(false);
  }

  return (
    <div className={"app" + (sidebarHidden ? " sidebar-collapsed" : "")}>
      {!sidebarHidden && (
        <Sidebar
          sessions={sessions}
          activeId={activeId}
          authenticated={!!user}
          onNew={newEstimate}
          onSelect={openSession}
          onDelete={removeSession}
          onRename={onRenameSession}
          onPin={onPinSession}
          onOpenSettings={() => setSettingsOpen(true)}
          onHideSidebar={hideSidebar}
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />
      )}
      {!sidebarHidden && sidebarOpen && (
        <div className="scrim" onClick={() => setSidebarOpen(false)} />
      )}

      <SettingsPanel
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        user={user}
        authLoading={authLoading}
        loginUrl={loginUrl}
        logout={logout}
        isAdmin={isAdmin}
        settings={settings}
        onChangeSettings={updateSettings}
        onClearContext={() => setConversationContext([])}
        switchAccountUrl={switchAccountUrl}
        onSwitchAccount={switchGoogleAccount}
      />

      <main className="main">
        <header className="topbar">
          <button
            className="menu-btn"
            aria-label={sidebarHidden ? "Show sidebar" : "Open history"}
            onClick={() => (sidebarHidden ? showSidebar() : setSidebarOpen(true))}
          >
            ☰
          </button>
          <span className="topbar-title">TokCost</span>
          {sidebarHidden && (
            <button type="button" className="ghost small" onClick={showSidebar}>
              Show sidebar
            </button>
          )}
        </header>

        <div className="scroll">
          {!view && !pending && (
            <div className="empty">
              <h1>Know your tokens before you ask</h1>
              <p className="muted">
                Add a prompt and any files. TokCost compares token counts and
                cost across ChatGPT, Claude, and Gemini.
              </p>
              {!user && (
                <p className="muted small">
                  Estimates work without signing in. Open <strong>Settings</strong> in the
                  sidebar to sign in and manage context.
                </p>
              )}
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

          {view && (
            <ResultView view={view} onUsePrompt={handleUsePrompt} />
          )}
        </div>

        <div className="bottom">
          {error && <div className="error">{error}</div>}
          <ContextUsage
            messages={conversationContext}
            draftText={composerText}
            enabled={settings.contextEnabled}
            charBudget={settings.contextCharBudget}
            maxMessages={maxContextMessages}
          />
          <Composer
            onSubmit={submit}
            loading={loading}
            value={composerText}
            onChange={setComposerText}
          />
        </div>
      </main>
    </div>
  );
}
