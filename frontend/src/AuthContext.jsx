import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { authMe, getLoginUrl, logout as apiLogout } from "./api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await authMe();
      setUser(data.authenticated ? data : null);
    } catch (e) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("login") !== "success") return;
    refresh().finally(() => {
      params.delete("login");
      const q = params.toString();
      const next = window.location.pathname + (q ? `?${q}` : "");
      window.history.replaceState({}, "", next);
    });
  }, [refresh]);

  async function logout() {
    await apiLogout();
    setUser(null);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        refresh,
        logout,
        loginUrl: getLoginUrl(),
        isAdmin: user?.role === "admin",
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
