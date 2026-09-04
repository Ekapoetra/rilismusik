import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api, formatApiError } from "@/api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null until loaded
  const [profile, setProfile] = useState(null); // label or artist record
  const [loading, setLoading] = useState(true);

  const acceptAuthPayload = useCallback((data) => {
    setUser(data.user);
    setProfile(data.label || data.artist || null);
    return data;
  }, []);

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data.user);
      setProfile(data.label || data.artist || null);
    } catch (_e) {
      setUser(false);
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (window.location.hash?.includes("session_id=")) {
      setLoading(false);
      return;
    }
    refresh();
  }, [refresh]);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    return acceptAuthPayload(data);
  };

  const register = async (payload) => {
    const { data } = await api.post("/auth/register", payload);
    return acceptAuthPayload(data);
  };

  const exchangeGoogleSession = useCallback(async (sessionId) => {
    const { data } = await api.post("/auth/google/session", { session_id: sessionId });
    return acceptAuthPayload(data);
  }, [acceptAuthPayload]);

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch (_e) { /* ignore */ }
    setUser(false);
    setProfile(null);
  };

  const hasPermission = useCallback((permission) => {
    if (user?.role === "super_admin") return true;
    const permissions = new Set(user?.permissions || []);
    const impliedBy = { "access.users.view": "access.users.manage", "access.roles.view": "access.roles.manage", "ui.settings.view": "ui.settings.manage" };
    return permissions.has(permission) || permissions.has(impliedBy[permission]);
  }, [user]);
  const isAdmin = Boolean(user?.is_admin || ["super_admin", "admin_release", "admin_finance", "admin_support", "admin_content", "admin_marketing", "admin_ui", "admin_custom"].includes(user?.role));

  return (
    <AuthContext.Provider value={{ user, profile, loading, refresh, login, register, exchangeGoogleSession, logout, hasPermission, isAdmin }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export { formatApiError };
