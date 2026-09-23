import React, { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import * as Icons from "lucide-react";
import { ChevronDown, ChevronLeft, ChevronRight, LogOut, Menu, X } from "lucide-react";
import { useAuth } from "@/api/AuthContext";
import NotificationBell from "./NotificationBell";
import { DashboardBrand } from "./DashboardBrand";
import { HeaderPreferences } from "./HeaderPreferences";
import { StatusMenu } from "./StatusMenu";
import { QuickChatButton } from "./QuickChatButton";
import { ProfileMenu } from "./ProfileMenu";
import AdminChatWidget from "@/components/chat/AdminChatWidget";
import { AdminNavigationProvider, useAdminNavigation } from "@/contexts/AdminNavigationContext";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { workspaceForRoute, workspaceItems, staffHome } from "@/components/admin/v7/workspaceNavigation";
import "@/styles/prototype-v7.css";
import V7MenuSearch from "@/components/admin/v7/V7MenuSearch";

const iconFor = (name) => Icons[name] || Icons.Circle;

// Shared with the isolated role preview: presentation only, no API or permission mutation.
export const AdminSidebarView = ({ instance, collapsed, onCollapse, onNavigate, items, groups = [], user, logout, preview = false, mode, platformRoute }) => {
  const { locale, t } = useAppPreferences();
  const { pathname } = useLocation();
  const [openGroups, setOpenGroups] = useState({});
  const byKey = useMemo(() => Object.fromEntries(items.map((item) => [item.key, item])), [items]);
  const roots = items.filter((item) => !item.parent_key || !byKey[item.parent_key]);
  const labelFor = (item) => item.labels?.[locale] || item.labels?.id || item.key;

  const renderItem = (item) => {
    const Icon = iconFor(item.icon);
    const children = items.filter((child) => child.parent_key === item.key);
    const active = pathname === item.route || pathname.startsWith(`${item.route}/`) || children.some((child) => pathname === child.route);
    const expanded = openGroups[item.key] ?? active;
    return <div className="mb-1" key={item.key}>
      <div className="flex items-center"><NavLink to={item.route} onClick={onNavigate} title={collapsed ? labelFor(item) : undefined} className={`dashboard-nav-link flex min-w-0 flex-1 items-center rounded-md py-2.5 ${collapsed ? "justify-center px-2" : "gap-3 px-3"} ${active ? "is-active" : ""}`} data-testid={`admin-nav-${item.key}-${instance}`}><Icon className="h-4 w-4 shrink-0" />{!collapsed && <span className="truncate text-sm font-semibold">{labelFor(item)}</span>}</NavLink>{children.length > 0 && !collapsed && <button type="button" aria-label={labelFor(item)} aria-expanded={expanded} onClick={() => setOpenGroups((current) => ({ ...current, [item.key]: !expanded }))} className="ml-1 rounded-md p-2 text-[var(--ui-muted)] hover:bg-[var(--ui-hover)]" data-testid={`admin-nav-${item.key}-subtabs-toggle-${instance}`}><ChevronDown className={`h-3.5 w-3.5 transition-transform ${expanded ? "rotate-180" : ""}`} /></button>}</div>
      {children.length > 0 && ((expanded && !collapsed) || collapsed) && <div className={collapsed ? "mt-1 space-y-1" : "ml-5 mt-1 space-y-1 border-l border-[var(--ui-border)] pl-3"} data-testid={`admin-nav-${item.key}-subtabs-${instance}`}>{children.map((child) => { const ChildIcon = iconFor(child.icon); return <NavLink key={child.key} to={child.route} onClick={onNavigate} title={collapsed ? labelFor(child) : undefined} className={`dashboard-nav-link flex items-center rounded-md py-2 text-xs font-semibold ${collapsed ? "justify-center px-2" : "gap-2 px-3"} ${pathname === child.route ? "is-active" : ""}`} data-testid={`admin-nav-${child.key}-${instance}`}><ChildIcon className="h-3.5 w-3.5 shrink-0" />{!collapsed && labelFor(child)}</NavLink>; })}</div>}
    </div>;
  };

  const orderedGroups = [...groups].sort((a, b) => (a.order || 0) - (b.order || 0));
  const groupLabel = (g) => g.labels?.[locale] || g.labels?.id || g.id;

  return <div className="dashboard-sidebar relative flex h-full flex-col" data-testid={`admin-sidebar-${instance}`}>
    <div className={`flex h-16 shrink-0 items-center border-b border-[var(--ui-border)] ${collapsed ? "justify-center px-2" : "justify-between px-5"}`}>
      <NavLink to={items[0]?.route || "/admin/dashboard"} onClick={onNavigate} data-testid={`admin-sidebar-brand-${instance}`}><DashboardBrand compact={collapsed} testId={`admin-brand-${instance}`} /></NavLink>
      {instance === "mobile" && <button type="button" onClick={onNavigate} aria-label={t("Tutup")} className="ui-icon-button" data-testid="admin-sidebar-mobile-close"><X className="h-4 w-4" /></button>}
    </div>
    {mode && !collapsed && <div className="v7-mode-switch" aria-label="Workspace"><NavLink to={platformRoute || "/admin/workspace"} onClick={onNavigate} className={mode === "platform" ? "is-active" : ""} aria-current={mode === "platform" ? "page" : undefined}>Platform</NavLink><NavLink to="/admin/workspace" onClick={onNavigate} className={mode === "staff" ? "is-active" : ""} aria-current={mode === "staff" ? "page" : undefined}>Staff</NavLink></div>}
    {instance !== "mobile" && <button type="button" onClick={onCollapse} title={t(collapsed ? "Bentangkan sidebar" : "Ciutkan sidebar")} aria-label={t(collapsed ? "Bentangkan sidebar" : "Ciutkan sidebar")} aria-expanded={!collapsed} className="sidebar-divider-toggle" data-testid={preview ? "role-preview-sidebar-collapse" : "admin-sidebar-collapse-button"}>{collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}</button>}
    <nav className="min-h-0 flex-1 overflow-y-auto px-2 py-4" data-testid={`admin-navigation-${instance}`}>
      {orderedGroups.length === 0
        ? roots.map(renderItem)
        : orderedGroups.map((g) => {
            const groupRoots = roots.filter((item) => item.group_id === g.id);
            if (!groupRoots.length) return null;
            return <div key={g.id} className="mb-3" data-testid={`admin-nav-group-${g.id}-${instance}`}>
              {!collapsed && <div className="px-3 pb-1 pt-1 text-[10px] font-bold uppercase tracking-widest text-[var(--ui-muted)]" data-testid={`admin-nav-group-label-${g.id}`}>{groupLabel(g)}</div>}
              {collapsed && <div className="mx-3 mb-1 border-t border-[var(--ui-border)]" />}
              {groupRoots.map(renderItem)}
            </div>;
          })}
      {orderedGroups.length > 0 && roots.filter(item => !orderedGroups.some(group => group.id === item.group_id)).map(renderItem)}
    </nav>
    <div className="space-y-3 border-t border-[var(--ui-border)] p-3">{!collapsed && <div translate="no"><div className="truncate text-xs font-bold" data-testid={`admin-current-user-name-${instance}`}>{user?.name}</div><div className="truncate text-[11px] text-[var(--ui-muted)]" data-testid={`admin-current-role-name-${instance}`}>{user?.role_name || user?.role}</div></div>}<button type="button" disabled={preview} onClick={logout} title={t("Keluar")} className={`flex w-full items-center rounded-md py-2 text-sm font-semibold text-red-400 hover:bg-red-500/10 disabled:opacity-40 ${collapsed ? "justify-center px-2" : "gap-2 px-3"}`} data-testid={`admin-logout-${instance}`}><LogOut className="h-4 w-4" />{!collapsed && t("Keluar")}</button></div>
  </div>;
};

const AdminLayoutInner = () => {
  const { user, logout } = useAuth();
  const { items, groups } = useAdminNavigation();
  const { t } = useAppPreferences();
  const { pathname } = useLocation();
  const mode = workspaceForRoute(pathname);
  const platformItems = workspaceItems(items, "platform");
  const platformRoute = platformItems.find(item => item.key === "dashboard")?.route || platformItems[0]?.route;
  const visibleItems = mode === "staff" ? [staffHome, ...workspaceItems(items, "staff")] : platformItems;
  const visibleGroups = groups.length ? [{ id: "v7_home", order: -1, labels: { id: "Workspace", en: "Workspace" } }, ...groups] : [];
  const [collapsed, setCollapsed] = useState(localStorage.getItem("admin-sidebar-collapsed") === "true");
  const [mobileOpen, setMobileOpen] = useState(false);
  useEffect(() => { setMobileOpen(false); window.scrollTo(0, 0); }, [pathname]);
  useEffect(() => { if (!mobileOpen) return; const close = (event) => { if (event.key === "Escape") setMobileOpen(false); }; window.addEventListener("keydown", close); return () => window.removeEventListener("keydown", close); }, [mobileOpen]);
  const toggle = () => setCollapsed((current) => { localStorage.setItem("admin-sidebar-collapsed", String(!current)); return !current; });
  return <div className="app-shell rm-v7 md:flex" data-testid="admin-layout">
    <a href="#v7-main" className="v7-skip-link">Lewati navigasi</a>
    <aside className={`dashboard-sidebar fixed inset-y-0 left-0 z-40 hidden border-r transition-[width] duration-300 md:block ${collapsed ? "w-[72px]" : "w-[232px]"}`}><AdminSidebarView instance="desktop" collapsed={collapsed} onCollapse={toggle} items={visibleItems} groups={visibleGroups} user={user} logout={logout} mode={mode} platformRoute={platformRoute} /></aside>
    {mobileOpen && <div className="fixed inset-0 z-50 md:hidden" data-testid="admin-mobile-sidebar"><button type="button" aria-label={t("Tutup menu")} onClick={() => setMobileOpen(false)} className="absolute inset-0 bg-black/70" data-testid="admin-mobile-sidebar-backdrop" /><aside className="dashboard-sidebar absolute inset-y-0 left-0 w-[min(86vw,320px)] border-r"><AdminSidebarView instance="mobile" collapsed={false} onNavigate={() => setMobileOpen(false)} items={visibleItems} groups={visibleGroups} user={user} logout={logout} mode={mode} platformRoute={platformRoute} /></aside></div>}
    <div style={{ "--rm-dock-left": collapsed ? "72px" : "232px" }} className={`min-w-0 flex-1 transition-[margin] duration-300 ${collapsed ? "md:ml-[72px]" : "md:ml-[232px]"}`}>
      <header className="dashboard-header sticky top-0 z-30 flex h-16 items-center justify-between gap-2 border-b px-3 sm:px-6 lg:px-8" data-testid="admin-topbar"><div className="flex min-w-0 items-center gap-2"><button type="button" onClick={() => setMobileOpen(true)} aria-label={t("Buka menu")} className="ui-icon-button md:hidden" data-testid="admin-mobile-sidebar-open"><Menu className="h-5 w-5" /></button><div className="md:hidden"><DashboardBrand compact testId="admin-header-brand" /></div><div className="hidden min-w-0 md:block"><V7MenuSearch /></div></div><div className="flex shrink-0 items-center gap-1.5"><HeaderPreferences instance="admin" /><StatusMenu instance="admin" /><NotificationBell instance="admin-header" historyPath="/admin/notifications" /><QuickChatButton instance="admin" /><ProfileMenu user={user} logout={logout} instance="admin" /></div></header>
      <div className="v7-workspace-strip"><span>Workspace</span><NavLink to={platformRoute || "/admin/workspace"} className={mode === "platform" ? "is-active" : ""}>Platform</NavLink><NavLink to="/admin/workspace" className={mode === "staff" ? "is-active" : ""}>Staff</NavLink></div>
      <main id="v7-main" tabIndex={-1} className="v7-main min-h-[calc(100vh-4rem)] p-4 pb-[calc(var(--audio-player-height,0px)+2rem)] sm:p-6 lg:p-8"><Outlet /></main>
    </div><AdminChatWidget />
  </div>;
};
export default function AdminLayout() { return <AdminNavigationProvider><AdminLayoutInner /></AdminNavigationProvider>; }
