import { Link } from "react-router-dom";
import ThemeToggle from "./ThemeToggle.jsx";
import { DEFAULTS } from "./settingsStore.js";

export default function SettingsPanel({
  open,
  onClose,
  user,
  authLoading,
  loginUrl,
  logout,
  isAdmin,
  settings,
  onChangeSettings,
  onClearContext,
  switchAccountUrl,
  onSwitchAccount,
}) {
  if (!open) return null;

  function set(key, value) {
    onChangeSettings({ [key]: value });
  }

  return (
    <>
      <div className="settings-scrim" onClick={onClose} />
      <div className="settings-panel" role="dialog" aria-label="Settings">
        <div className="settings-head">
          <h2>Settings</h2>
          <button type="button" className="ghost" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <section className="settings-section">
          <h3 className="settings-label">Appearance</h3>
          <div className="settings-row">
            <span>Theme</span>
            <ThemeToggle />
          </div>
          <label className="settings-check">
            <input
              type="checkbox"
              checked={settings.sidebarHidden}
              onChange={(e) => set("sidebarHidden", e.target.checked)}
            />
            Hide sidebar (more space for estimates)
          </label>
        </section>

        <section className="settings-section">
          <h3 className="settings-label">Account</h3>
          {authLoading ? (
            <p className="small muted">Loading…</p>
          ) : user ? (
            <>
              <p className="small">{user.email}</p>
              <p className="small muted">Role: {user.role}</p>
              {isAdmin && (
                <Link className="settings-link" to="/admin" onClick={onClose}>
                  Open admin dashboard
                </Link>
              )}
              <button type="button" className="settings-btn" onClick={logout}>
                Sign out
              </button>
              <button
                type="button"
                className="settings-btn"
                onClick={onSwitchAccount}
              >
                Sign in with another Google account
              </button>
            </>
          ) : (
            <>
              <p className="small muted">
                Sign in to save history, pin chats, and sync settings across this browser.
              </p>
              <a className="settings-btn primary" href={loginUrl}>
                Sign in with Google
              </a>
              <a className="settings-btn" href={switchAccountUrl}>
                Choose Google account…
              </a>
            </>
          )}
        </section>

        <section className="settings-section">
          <h3 className="settings-label">Context (like Cursor)</h3>
          <label className="settings-check">
            <input
              type="checkbox"
              checked={settings.contextEnabled}
              onChange={(e) => set("contextEnabled", e.target.checked)}
            />
            Use conversation context for compression
          </label>
          <label className="settings-field">
            <span className="small">Max context messages</span>
            <select
              value={settings.maxContextMessages}
              onChange={(e) =>
                set("maxContextMessages", Number(e.target.value))
              }
            >
              {[2, 4, 6, 8].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </label>
          <label className="settings-field">
            <span className="small">Context size budget (chars)</span>
            <select
              value={settings.contextCharBudget}
              onChange={(e) =>
                set("contextCharBudget", Number(e.target.value))
              }
            >
              {[2000, 4000, 6000, 8000].map((n) => (
                <option key={n} value={n}>{n.toLocaleString()}</option>
              ))}
            </select>
          </label>
          <p className="small muted">
            Defaults: {DEFAULTS.maxContextMessages} messages,{" "}
            {DEFAULTS.contextCharBudget.toLocaleString()} chars. Context stays in this
            browser session only.
          </p>
          <button type="button" className="settings-btn" onClick={onClearContext}>
            Clear conversation context
          </button>
        </section>
      </div>
    </>
  );
}
