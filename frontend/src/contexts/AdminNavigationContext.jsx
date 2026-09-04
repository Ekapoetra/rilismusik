import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "@/api/client";
import { useAuth } from "@/api/AuthContext";

const AdminNavigationContext = createContext(null);

const FALLBACK_ITEMS = [
  ["dashboard", "/admin/dashboard", "LayoutDashboard", "dashboard.view", "Dashboard", "Dashboard"],
  ["labels", "/admin/labels", "Building2", "labels.view", "Manajemen Label", "Label Management"],
  ["releases", "/admin/releases", "Disc3", "releases.view", "Manajemen Rilisan", "Release Management"],
  ["royalty", "/admin/royalty", "FileSpreadsheet", "royalty.view", "Impor Royalti", "Royalty Import"],
  ["ui_settings", "/admin/ui-settings", "PanelLeft", "ui.settings.view", "Pengaturan UI", "UI Settings"],
].map(([key, route, icon, permission, id, en], order) => ({ key, route, icon, permission, labels: { id, en }, order, visible: true, parent_key: null }));

export const AdminNavigationProvider = ({ children }) => {
  const { hasPermission } = useAuth();
  const [items, setItems] = useState([]);
  const [locale, setLocaleState] = useState(localStorage.getItem("admin-ui-locale") || "id");
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/admin/navigation");
      setItems(data.items || []);
      if (!localStorage.getItem("admin-ui-locale")) setLocaleState(data.default_locale || "id");
    } catch {
      setItems(FALLBACK_ITEMS.filter((item) => hasPermission(item.permission)));
    } finally { setLoading(false); }
  }, [hasPermission]);
  useEffect(() => { load(); }, [load]);
  const setLocale = (next) => { setLocaleState(next); localStorage.setItem("admin-ui-locale", next); };
  const value = useMemo(() => ({ items, locale, setLocale, loading, reload: load, labelFor: (item) => item.labels?.[locale] || item.labels?.id || item.key }), [items, locale, loading, load]);
  return <AdminNavigationContext.Provider value={value}>{children}</AdminNavigationContext.Provider>;
};

export const useAdminNavigation = () => {
  const context = useContext(AdminNavigationContext);
  if (!context) throw new Error("useAdminNavigation must be used within AdminNavigationProvider");
  return context;
};