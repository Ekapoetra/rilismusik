import React, { Suspense, useMemo, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import * as Icons from "lucide-react";
import { ChevronDown, ChevronLeft, ChevronRight, LogOut, X } from "lucide-react";
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
import { LanguageToggle, Masthead, MastheadProvider, ThemeSwitch, useV13Document } from "@/components/v13/Masthead";
import { V13Sidebar } from "@/components/v13/V13Sidebar";
import { ADMIN_AREAS, DEDICATED_AREAS, FINANCE_MONITOR_ITEMS, V13_LABELS, areaForKey, areaForPath, arrangeV13, itemsByArea, matchNavItem } from "@/components/v13/adminAreas";

const iconFor = (name) => Icons[name] || Icons.Circle;

// Shared with the isolated role preview: presentation only, no API or permission mutation.
export const AdminSidebarView = ({ instance, collapsed, onCollapse, onNavigate, items, groups = [], user, logout, preview = false }) => {
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
    </nav>
    <div className="space-y-3 border-t border-[var(--ui-border)] p-3">{!collapsed && <div translate="no"><div className="truncate text-xs font-bold" data-testid={`admin-current-user-name-${instance}`}>{user?.name}</div><div className="truncate text-[11px] text-[var(--ui-muted)]" data-testid={`admin-current-role-name-${instance}`}>{user?.role_name || user?.role}</div></div>}<button type="button" disabled={preview} onClick={logout} title={t("Keluar")} className={`flex w-full items-center rounded-md py-2 text-sm font-semibold text-red-400 hover:bg-red-500/10 disabled:opacity-40 ${collapsed ? "justify-center px-2" : "gap-2 px-3"}`} data-testid={`admin-logout-${instance}`}><LogOut className="h-4 w-4" />{!collapsed && t("Keluar")}</button></div>
  </div>;
};

const AdminLayoutInner = () => {
  useV13Document();
  const { user, logout } = useAuth();
  const { items: navItems } = useAdminNavigation();
  const { locale, t } = useAppPreferences();
  const items = useMemo(() => {
    if (user?.role !== "super_admin") return navItems;
    // Super Admin-only V13 pages: finance tabs lead their area, settings tabs follow the server ones.
    const finance = FINANCE_MONITOR_ITEMS.filter((item) => item.key.startsWith("finance_"));
    const settings = FINANCE_MONITOR_ITEMS.filter((item) => !item.key.startsWith("finance_"));
    return [...finance, ...navItems, ...settings];
  }, [user?.role, navItems]);
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(localStorage.getItem("admin-sidebar-collapsed") === "true");
  const [mobileOpen, setMobileOpen] = useState(false);
  const toggle = () => setCollapsed((current) => { localStorage.setItem("admin-sidebar-collapsed", String(!current)); return !current; });
  const labelFor = (item) => V13_LABELS[item.key]?.[locale] || item.labels?.[locale] || item.labels?.id || item.key;
  const grouped = useMemo(() => itemsByArea(items), [items]);
  const current = matchNavItem(items, pathname);
  const area = areaForPath(items, pathname);
  const mode = area === "staff" ? "staff" : "platform";
  const dedicated = DEDICATED_AREAS.has(area);
  const firstRoute = (list, fallback) => list[0]?.route || fallback;
  const linksFor = (list) => arrangeV13(list).map((item) => ({ key: item.key, to: item.route, label: labelFor(item), icon: iconFor(item.icon), child: item.v13Child, active: current?.key === item.key, testId: `admin-nav-${item.key}` }));
  const sideLinks = linksFor(mode === "staff" ? grouped.staff : grouped.platform);
  const areas = ADMIN_AREAS.filter((entry) => entry.id === "platform" || grouped[entry.id].length)
    .map((entry) => ({ ...entry, to: entry.id === "platform" ? firstRoute(grouped.platform, "/admin/dashboard") : firstRoute(grouped[entry.id], "/admin/dashboard"), active: entry.id === "platform" ? !dedicated : entry.id === area }));
  const searchItems = items.map((item) => ({ to: item.route, label: labelFor(item), hint: t(ADMIN_AREAS.find((entry) => entry.id === areaForKey(item.key))?.label || "Staff") }));
  const switcher = grouped.staff.length && grouped.platform.length ? { mode, onChange: (next) => { setMobileOpen(false); if (next !== mode) navigate(firstRoute(next === "staff" ? grouped.staff : grouped.platform, "/admin/dashboard")); } } : null;
  const footer = { name: user?.name || user?.email || "Admin", sub: user?.role_name || user?.role };
  const home = pathname === "/admin/dashboard" || pathname === "/admin/status";
  const areaMeta = ADMIN_AREAS.find((entry) => entry.id === area);
  const tools = <><span className="v13-optional"><StatusMenu instance="admin" /></span><ThemeSwitch /><LanguageToggle /><span className="v13-optional"><HeaderPreferences instance="admin" show={["sound"]} /></span><NotificationBell instance="admin-header" historyPath="/admin/notifications" /><QuickChatButton instance="admin" /><ProfileMenu user={user} logout={logout} instance="admin" /></>;
  return <MastheadProvider><div className="app-shell v13-shell" data-testid="admin-layout">
    <Masthead name={user?.name || "Admin"} home={home} areas={areas} searchItems={searchItems} tools={tools} brandTo={firstRoute(grouped.platform, "/admin/dashboard")} onMenu={() => setMobileOpen(true)} />
    {mobileOpen && <div className="v13-drawer md:hidden" data-testid="admin-mobile-sidebar"><button type="button" aria-label={t("Tutup menu")} onClick={() => setMobileOpen(false)} data-testid="admin-mobile-sidebar-backdrop" /><aside><V13Sidebar instance="mobile" switcher={switcher} links={[...sideLinks, ...ADMIN_AREAS.filter((entry) => entry.id !== "platform" && grouped[entry.id].length).flatMap((entry) => [{ key: `group-${entry.id}`, group: t(entry.label) }, ...linksFor(grouped[entry.id])])]} onNavigate={() => setMobileOpen(false)} footer={footer} /><button type="button" onClick={logout} className="mt-4 flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-red-500" data-testid="admin-logout-mobile"><LogOut className="h-4 w-4" />{t("Keluar")}</button></aside></div>}
    <div style={{ "--rm-dock-left": dedicated ? "24px" : collapsed ? "88px" : "272px" }} className={`v13-body ${dedicated ? "is-wide" : ""} ${!dedicated && collapsed ? "has-collapsed-side" : ""}`}>
      {!dedicated && <V13Sidebar switcher={switcher} links={sideLinks} collapsed={collapsed} onToggle={toggle} footer={footer} />}
      <main className="v13-main" data-testid="admin-main">
        {dedicated && <div className="v13-areahead" data-testid={`v13-areahead-${area}`}><h1>{t(areaMeta.label)}</h1>{grouped[area].length > 1 && <nav className="v13-tabs" aria-label={t(areaMeta.label)}>{grouped[area].map((item) => <Link key={item.key} to={item.route} aria-current={current?.key === item.key ? "page" : undefined} className={current?.key === item.key ? "is-active" : ""} data-testid={`admin-nav-${item.key}`}>{labelFor(item)}</Link>)}</nav>}</div>}
        <Suspense fallback={<div role="status" className="p-8 text-center text-[var(--ui-muted)]">Memuat halaman…</div>}><Outlet /></Suspense>
      </main>
    </div><AdminChatWidget />
  </div></MastheadProvider>;
};
export default function AdminLayout() { return <AdminNavigationProvider><AdminLayoutInner /></AdminNavigationProvider>; }