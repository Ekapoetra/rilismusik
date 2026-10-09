import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api, formatApiError } from "@/api/client";
import { getStaffPreview, startStaffPreview, exitStaffPreview, subscribeStaffPreview } from "./staffPreview";

import { resetSharedReads } from "./sharedRead";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null until loaded
  const [profile, setProfile] = useState(null); // label or artist record
  const [loading, setLoading] = useState(true);

  const acceptAuthPayload = useCallback((data) => {
    resetSharedReads();
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

  const loginWithGoogle = useCallback(async (credential) => {
    const { data } = await api.post("/auth/google/id-token", { credential });
    return acceptAuthPayload(data);
  }, [acceptAuthPayload]);

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch (_e) { /* ignore */ }
    resetSharedReads();
    setUser(false);
    setProfile(null);
  };

  // D10 staff preview: reactive mirror of the module-level preview store.
  const [staffPreview, setStaffPreview] = useState(getStaffPreview());
  useEffect(() => subscribeStaffPreview(setStaffPreview), []);

  const enterStaffPreview = useCallback(async (userId) => {
    const { data } = await api.get(`/admin/admin-users/${userId}/preview-context`);
    startStaffPreview(data);
    return data;
  }, []);

  const exitPreview = useCallback(() => exitStaffPreview(), []);

  const hasPermission = useCallback((permission) => {
    const impliedBy = { "access.users.view": "access.users.manage", "access.roles.view": "access.roles.manage", "ui.settings.view": "ui.settings.manage", "labels.rate.request.view": "labels.rate.approve", "labels.package.request.view": "labels.package.approve", "labels.blacklist.request.view": "labels.blacklist.approve" };
    if (staffPreview) {
      // Preview strictly follows the staff member's resolved permissions —
      // the Super Admin wildcard never applies while previewing.
      if (!permission) return true;
      if (staffPreview.admin_role_active === false) return false;
      const previewPerms = new Set(staffPreview.permissions || []);
      return previewPerms.has(permission) || previewPerms.has(impliedBy[permission]);
    }
    if (user?.role === "super_admin") return true;
    const permissions = new Set(user?.permissions || []);
    return permissions.has(permission) || permissions.has(impliedBy[permission]);
  }, [user, staffPreview]);
  const isAdmin = Boolean(user?.is_admin || ["super_admin", "admin_release", "admin_finance", "admin_support", "admin_content", "admin_marketing", "admin_ui", "admin_custom"].includes(user?.role));

  return (
    <AuthContext.Provider value={{ user, profile, loading, refresh, login, register, loginWithGoogle, logout, hasPermission, isAdmin, staffPreview, enterStaffPreview, exitStaffPreview: exitPreview }}>
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
