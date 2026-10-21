import { Link, Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../AuthContext.jsx";
import ThemeToggle from "../ThemeToggle.jsx";

export default function AdminLayout() {
  const { user, loading, logout, isAdmin } = useAuth();

  if (loading) {
    return <div className="admin-page muted pad">Loading…</div>;
  }
  if (!user) {
    return <Navigate to="/" replace />;
  }
  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="admin-shell">
      <header className="admin-topbar">
        <div className="admin-brand">
          <Link to="/">← TokCost</Link>
          <span className="admin-title">Admin</span>
        </div>
        <div className="admin-topbar-actions">
          <ThemeToggle />
          <span className="small muted">{user.email}</span>
          <button type="button" className="ghost" onClick={logout}>Sign out</button>
        </div>
      </header>
      <nav className="admin-nav">
        <Link to="/admin">Dashboard</Link>
      </nav>
      <main className="admin-main">
        <Outlet />
      </main>
    </div>
  );
}
