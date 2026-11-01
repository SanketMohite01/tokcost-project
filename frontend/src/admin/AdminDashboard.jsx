import { useEffect, useState } from "react";
import { adminListUsers, adminSetRole, adminStats } from "../api.js";
import { useAuth } from "../AuthContext.jsx";

export default function AdminDashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  async function load() {
    setError("");
    try {
      const [s, u] = await Promise.all([adminStats(), adminListUsers()]);
      setStats(s);
      setUsers(u);
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function changeRole(targetId, role) {
    setBusy(targetId);
    setError("");
    try {
      await adminSetRole(targetId, role);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="admin-page">
      <h1>Admin dashboard</h1>
      {error && <div className="error">{error}</div>}

      {stats && (
        <div className="stats admin-stats">
          <div className="stat">
            <div className="stat-label">Users</div>
            <div className="stat-value">{stats.users}</div>
          </div>
          <div className="stat">
            <div className="stat-label">Active sessions</div>
            <div className="stat-value">{stats.active_sessions}</div>
          </div>
          <div className="stat">
            <div className="stat-label">Soft-deleted sessions</div>
            <div className="stat-value">{stats.soft_deleted_sessions}</div>
          </div>
        </div>
      )}

      <div className="panel">
        <div className="panel-title">Users & roles</div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Email</th>
                <th>Role</th>
                <th>Joined</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.email}</td>
                  <td>{u.role}</td>
                  <td>{new Date(u.created_at).toLocaleString()}</td>
                  <td>
                    {u.id === user.id ? (
                      <span className="small muted">You</span>
                    ) : u.role === "admin" ? (
                      <button
                        type="button"
                        className="ghost"
                        disabled={busy === u.id}
                        onClick={() => changeRole(u.id, "user")}
                      >
                        Make user
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="ghost"
                        disabled={busy === u.id}
                        onClick={() => changeRole(u.id, "admin")}
                      >
                        Make admin
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <p className="small muted">
        Legacy anonymous sessions (saved under browser-generated IDs before Google login) remain in
        the database but are not linked to user accounts.
      </p>
    </div>
  );
}
