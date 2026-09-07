import React, { useMemo, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import * as Icons from "lucide-react";
import { ChevronDown, LogOut, Menu, PanelLeftClose, PanelLeftOpen, X } from "lucide-react";
import { useAuth } from "@/api/AuthContext";
import LogoMark from "@/components/shared/LogoMark";
import NotificationBell from "@/components/shared/NotificationBell";
import AdminChatWidget from "@/components/chat/AdminChatWidget";
import { AdminNavigationProvider, useAdminNavigation } from "@/contexts/AdminNavigationContext";

const iconFor = (name) => Icons[name] || Icons.Circle;

const AdminSidebar = ({ instance, collapsed, onCollapse, onNavigate }) => {
  const { user, logout } = useAuth();
  const { items, locale, setLocale, labelFor } = useAdminNavigation();
  const location = useLocation();
  const [openGroups, setOpenGroups] = useState({});
  const byKey = useMemo(() => Object.fromEntries(items.map((item) => [item.key, item])), [items]);
  const roots = items.filter((item) => !item.parent_key || !byKey[item.parent_key]);
  const childrenFor = (key) => items.filter((item) => item.parent_key === key);

  return <div className="flex h-full flex-col bg-[#090909]" data-testid={`admin-sidebar-${instance}`}>
    <div className={`flex h-16 items-center border-b border-white/10 ${collapsed ? "justify-center px-2" : "justify-between px-5"}`}>
      <NavLink to="/admin/dashboard" onClick={onNavigate} className="flex items-center gap-3" data-testid={`admin-sidebar-brand-${instance}`}><LogoMark className="h-8 w-8" />{!collapsed && <span className="font-display text-sm font-black tracking-wide">RILIS MUSIK</span>}</NavLink>
      {instance === "desktop" && <button type="button" onClick={onCollapse} title={collapsed ? "Bentangkan sidebar" : "Ciutkan sidebar"} className="rounded-md p-2 text-zinc-500 transition-colors hover:bg-white/5 hover:text-white" data-testid="admin-sidebar-collapse-button">{collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}</button>}
      {instance === "mobile" && <button type="button" onClick={onNavigate} className="rounded-md p-2 text-zinc-400" data-testid="admin-sidebar-mobile-close"><X className="h-5 w-5" /></button>}
    </div>
    <nav className="flex-1 overflow-y-auto px-2 py-4" data-testid={`admin-navigation-${instance}`}>{roots.map((item) => {
      const Icon = iconFor(item.icon); const children = childrenFor(item.key);
      const active = location.pathname === item.route || location.pathname.startsWith(`${item.route}/`) || children.some((child) => location.pathname === child.route || location.pathname.startsWith(`${child.route}/`));
      const expanded = openGroups[item.key] ?? active;
      return <div className="group relative mb-1" key={item.key}>
        <div className="flex items-center"><NavLink to={item.route} onClick={onNavigate} title={collapsed ? labelFor(item) : undefined} className={({ isActive }) => `flex min-w-0 flex-1 items-center rounded-md py-2.5 transition-colors ${collapsed ? "justify-center px-2" : "gap-3 px-3"} ${isActive || active ? "bg-white text-black" : "text-zinc-400 hover:bg-white/[0.06] hover:text-white"}`} data-testid={`admin-nav-${item.key}-${instance}`}><Icon className="h-4 w-4 shrink-0" />{!collapsed && <span className="truncate text-sm font-semibold">{labelFor(item)}</span>}</NavLink>{children.length > 0 && !collapsed && <button type="button" onClick={() => setOpenGroups((current) => ({ ...current, [item.key]: !expanded }))} className="ml-1 rounded-md p-2 text-zinc-500 hover:bg-white/5 hover:text-white" data-testid={`admin-nav-${item.key}-subtabs-toggle-${instance}`}><ChevronDown className={`h-3.5 w-3.5 transition-transform ${expanded ? "rotate-180" : ""}`} /></button>}</div>
        {children.length > 0 && !collapsed && expanded && <div className="ml-5 mt-1 space-y-1 border-l border-white/10 pl-3" data-testid={`admin-nav-${item.key}-subtabs-${instance}`}>{children.map((child) => { const ChildIcon = iconFor(child.icon); return <NavLink key={child.key} to={child.route} onClick={onNavigate} className={({ isActive }) => `flex items-center gap-2 rounded-md px-3 py-2 text-xs font-semibold transition-colors ${isActive ? "bg-white/10 text-white" : "text-zinc-500 hover:bg-white/5 hover:text-zinc-200"}`} data-testid={`admin-nav-${child.key}-${instance}`}><ChildIcon className="h-3.5 w-3.5" />{labelFor(child)}</NavLink>; })}</div>}
        {children.length > 0 && collapsed && <div className="invisible absolute left-full top-0 z-50 ml-2 w-56 rounded-md border border-white/10 bg-[#111] p-2 opacity-0 shadow-2xl transition-opacity group-hover:visible group-hover:opacity-100"><div className="px-2 py-1 text-xs font-bold text-zinc-400">{labelFor(item)}</div>{children.map((child) => <NavLink key={child.key} to={child.route} onClick={onNavigate} className="block rounded px-2 py-2 text-xs text-zinc-300 hover:bg-white/10" data-testid={`admin-nav-${child.key}-${instance}`}>{labelFor(child)}</NavLink>)}</div>}
      </div>;
    })}</nav>
    <div className="space-y-3 border-t border-white/10 p-3"><button type="button" onClick={() => setLocale(locale === "id" ? "en" : "id")} className="rounded-md border border-white/10 px-2.5 py-1.5 text-[11px] font-bold uppercase text-zinc-300 hover:bg-white/5" data-testid={`admin-locale-toggle-${instance}`}>{locale === "id" ? "ID" : "EN"}</button>{!collapsed && <div><div className="truncate text-xs font-bold text-zinc-200" data-testid={`admin-current-user-name-${instance}`}>{user?.name}</div><div className="truncate text-[11px] text-zinc-600" data-testid={`admin-current-role-name-${instance}`}>{user?.role_name || user?.role}</div></div>}<button type="button" onClick={logout} title="Keluar" className={`flex w-full items-center rounded-md py-2 text-sm font-semibold text-red-300 hover:bg-red-500/10 ${collapsed ? "justify-center px-2" : "gap-2 px-3"}`} data-testid={`admin-logout-${instance}`}><LogOut className="h-4 w-4" />{!collapsed && "Keluar"}</button></div>
  </div>;
};

const AdminLayoutInner = () => {
  const [collapsed, setCollapsed] = useState(localStorage.getItem("admin-sidebar-collapsed") === "true");
  const [mobileOpen, setMobileOpen] = useState(false);
  const toggleCollapsed = () => setCollapsed((current) => { localStorage.setItem("admin-sidebar-collapsed", String(!current)); return !current; });
  return <div className="min-h-screen bg-[#070707] text-white md:flex" data-testid="admin-layout"><aside className={`fixed inset-y-0 left-0 z-40 hidden border-r border-white/10 transition-[width] duration-300 md:block ${collapsed ? "w-[72px]" : "w-64"}`}><AdminSidebar instance="desktop" collapsed={collapsed} onCollapse={toggleCollapsed} /></aside><div className={`fixed inset-0 z-50 md:hidden ${mobileOpen ? "pointer-events-auto" : "pointer-events-none"}`} aria-hidden={!mobileOpen}><button type="button" aria-label="Tutup menu" onClick={() => setMobileOpen(false)} className={`absolute inset-0 bg-black/70 transition-opacity ${mobileOpen ? "opacity-100" : "opacity-0"}`} data-testid="admin-mobile-sidebar-backdrop" /><aside className={`absolute inset-y-0 left-0 w-[min(86vw,320px)] border-r border-white/10 transition-transform duration-300 ${mobileOpen ? "translate-x-0" : "-translate-x-full"}`}><AdminSidebar instance="mobile" collapsed={false} onNavigate={() => setMobileOpen(false)} /></aside></div><div className={`min-w-0 flex-1 transition-[margin] duration-300 ${collapsed ? "md:ml-[72px]" : "md:ml-64"}`}><header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-white/10 bg-[#080808]/95 px-4 backdrop-blur-xl sm:px-6 lg:px-8" data-testid="admin-topbar"><div className="flex items-center gap-3"><button type="button" onClick={() => setMobileOpen(true)} className="rounded-md p-2 text-zinc-300 md:hidden" data-testid="admin-mobile-sidebar-open"><Menu className="h-5 w-5" /></button><LogoMark className="h-7 w-7 md:hidden" /><div className="hidden md:block"><div className="text-[10px] font-bold uppercase tracking-widest text-zinc-600">RILIS MUSIK</div><div className="text-sm font-bold text-zinc-300">Admin Console</div></div></div><NotificationBell instance="admin-header" historyPath="/admin/notifications" /></header><main className="min-h-[calc(100vh-4rem)] p-4 sm:p-6 lg:p-8"><Outlet /></main></div><AdminChatWidget /></div>;
};

export default function AdminLayout() { return <AdminNavigationProvider><AdminLayoutInner /></AdminNavigationProvider>; }