import React, { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate, Outlet } from "react-router-dom";
import { useAuth } from "@/api/AuthContext";
import { LABEL_NAV } from "@/constants/testIds";
import { api } from "@/api/client";
import NotificationBell from "./NotificationBell";
import LabelSwitcher from "./LabelSwitcher";
import { DashboardBrand } from "./DashboardBrand";
import { HeaderPreferences } from "./HeaderPreferences";
import { KycGate } from "./KycGate";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import LabelChatWidget from "@/components/chat/LabelChatWidget";
import { LayoutDashboard, Disc3, UploadCloud, Users, BarChart3, Wallet, LifeBuoy, FileText, FileSignature, Music, Settings, LogOut, Menu, X, LockKeyhole, ChevronLeft, ChevronRight } from "lucide-react";

const NAV = [
  { to: "/label/dashboard", label: "Dashboard", icon: LayoutDashboard, tid: LABEL_NAV.dashboard, kycFree: true },
  { to: "/label/releases/upload", label: "Ajukan Rilisan", icon: UploadCloud, tid: LABEL_NAV.uploadRelease },
  { to: "/label/releases", label: "Rilisan", icon: Disc3, tid: LABEL_NAV.releases },
  { to: "/label/artists", label: "Artis", icon: Users, tid: LABEL_NAV.artists },
  { to: "/label/royalty", label: "Royalti", icon: BarChart3, tid: LABEL_NAV.royalty },
  { to: "/label/withdraw", label: "Penarikan Dana", icon: Wallet, tid: LABEL_NAV.withdraw },
  { to: "/label/wami", label: "WAMI", icon: Music, tid: "label-nav-wami" },
  { to: "/label/support", label: "Bantuan", icon: LifeBuoy, tid: LABEL_NAV.support },
  { to: "/label/contract", label: "Kontrak", icon: FileSignature, tid: "label-nav-contract", kycFree: true },
  { to: "/label/invoices", label: "Tagihan", icon: FileText, tid: LABEL_NAV.invoices },
  { to: "/label/profile", label: "Profil & Rekening", icon: Settings, tid: LABEL_NAV.profile, kycFree: true },
];
const isKycFreePath = (path) => ["/label/dashboard", "/label/profile", "/label/contract"].some((allowed) => path === allowed || path.startsWith(`${allowed}/`));

export default function LabelLayout() {
  const { user, profile, logout } = useAuth();
  const { t } = useAppPreferences();
  const loc = useLocation(); const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(localStorage.getItem("label-sidebar-collapsed") === "true");
  const [kyc, setKyc] = useState(profile?.kyc || null); const [kycLoading, setKycLoading] = useState(true);
  const loadKyc = useCallback(async () => { setKycLoading(true); try { const { data } = await api.get("/label/kyc"); setKyc(data); } catch { setKyc({ status: "incomplete", is_verified: false }); } finally { setKycLoading(false); } }, []);
  useEffect(() => { loadKyc(); }, [loadKyc, loc.pathname]);
  useEffect(() => { const update = (event) => setKyc(event.detail); window.addEventListener("rilismusik:kyc-updated", update); return () => window.removeEventListener("rilismusik:kyc-updated", update); }, []);
  const locked = !isKycFreePath(loc.pathname) && (kycLoading || !kyc?.is_verified);
  const onLogout = async () => { await logout(); navigate("/login"); };
  const toggle = () => setCollapsed((value) => { localStorage.setItem("label-sidebar-collapsed", String(!value)); return !value; });
  return <div className="app-shell" data-testid="label-layout">
    <aside className={`dashboard-sidebar fixed inset-y-0 left-0 z-40 hidden flex-col border-r transition-[width] duration-300 md:flex ${collapsed ? "w-[72px]" : "w-64"}`} data-testid="label-sidebar-desktop">
      <Link to="/label/dashboard" className={`flex h-16 shrink-0 items-center border-b border-[var(--ui-border)] ${collapsed ? "justify-center" : "px-5"}`} data-testid="label-sidebar-brand"><DashboardBrand compact={collapsed} testId="label-brand-desktop" /></Link>
      <button type="button" className="sidebar-divider-toggle" title={t(collapsed ? "Bentangkan sidebar" : "Ciutkan sidebar")} aria-label={t(collapsed ? "Bentangkan sidebar" : "Ciutkan sidebar")} aria-expanded={!collapsed} onClick={toggle} data-testid="label-sidebar-collapse-button">{collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}</button>
      <div className="min-h-0 flex-1 overflow-y-auto px-2 py-4"><NavList currentPath={loc.pathname} onPick={() => {}} kycVerified={kyc?.is_verified} collapsed={collapsed} /></div>
      <div className="border-t border-[var(--ui-border)] p-3">{!collapsed && <div className="mb-3 min-w-0" translate="no"><div className="truncate text-xs font-semibold" data-testid="label-current-name">{profile?.label_name || user?.name}</div><div className="truncate text-[11px] text-[var(--ui-muted)]" data-testid="label-current-email">{user?.email}</div></div>}<button type="button" onClick={onLogout} title={t("Keluar")} className={`flex w-full items-center rounded-md py-2 text-sm text-red-400 hover:bg-red-500/10 ${collapsed ? "justify-center" : "gap-2 px-3"}`} data-testid="label-logout-button-desktop"><LogOut className="h-4 w-4" />{!collapsed && t("Keluar")}</button></div>
    </aside>
    {open && <div className="fixed inset-0 z-50 md:hidden" data-testid="label-mobile-sidebar"><button type="button" onClick={() => setOpen(false)} aria-label={t("Tutup menu")} className="absolute inset-0 bg-black/70" data-testid="label-mobile-menu-backdrop" /><aside className="dashboard-sidebar absolute inset-y-0 left-0 flex w-[min(86vw,320px)] flex-col border-r"><div className="flex h-16 shrink-0 items-center justify-between border-b border-[var(--ui-border)] px-4"><DashboardBrand testId="label-brand-mobile" /><button type="button" className="ui-icon-button" onClick={() => setOpen(false)} aria-label={t("Tutup")} data-testid="label-mobile-menu-close"><X className="h-4 w-4" /></button></div><div className="min-h-0 flex-1 overflow-y-auto px-2 py-4"><NavList instance="mobile" currentPath={loc.pathname} onPick={() => setOpen(false)} kycVerified={kyc?.is_verified} /></div><button type="button" onClick={onLogout} className="m-3 flex items-center gap-2 p-3 text-sm text-red-400" data-testid="label-logout-button"><LogOut className="h-4 w-4" />{t("Keluar")}</button></aside></div>}
    <div className={`min-w-0 transition-[margin] duration-300 ${collapsed ? "md:ml-[72px]" : "md:ml-64"}`}>
      <header className="dashboard-header sticky top-0 z-30 flex h-16 items-center justify-between gap-2 border-b px-3 sm:px-6 lg:px-8" data-testid="label-topbar"><div className="flex min-w-0 items-center gap-2"><button type="button" className="ui-icon-button md:hidden" onClick={() => setOpen(true)} aria-label={t("Buka menu")} data-testid="label-mobile-menu-button"><Menu className="h-5 w-5" /></button><div className="md:hidden"><DashboardBrand compact testId="label-header-brand" /></div><div className="hidden min-w-0 md:block"><div className="text-[10px] font-bold text-[var(--ui-muted)]" translate="no">RILIS MUSIK</div><div className="text-sm font-bold">{t("Label Dashboard")}</div></div></div><div className="flex shrink-0 items-center gap-1.5"><LabelSwitcher /><HeaderPreferences instance="label" /><NotificationBell instance="label-header" /></div></header>
      <main className="label-page-content relative min-w-0 p-4 pb-24 md:p-8"><div className={locked ? "pointer-events-none select-none blur-md opacity-35" : ""} aria-hidden={locked || undefined} data-testid="label-route-content"><Outlet /></div>{locked && <KycGate status={kyc?.status} loading={kycLoading} />}</main>
    </div>
    <LabelChatWidget />
    <nav className="dashboard-header fixed inset-x-0 bottom-0 z-30 border-t md:hidden" data-testid="label-bottom-navigation"><div className="grid grid-cols-5 gap-1 p-2">{[NAV[0], NAV[1], NAV[3], NAV[4], NAV[8]].map((item) => { const Icon = item.icon; const active = loc.pathname.startsWith(item.to); return <Link key={item.to} to={item.to} data-testid={`${item.tid}-bottom`} className={`flex min-w-0 flex-col items-center gap-1 rounded-md py-2 text-[10px] font-semibold ${active ? "bg-[var(--ui-hover)] text-[var(--ui-text)]" : "text-[var(--ui-muted)]"}`}><Icon className="h-4 w-4" /><span className="max-w-full truncate">{t(item.label).split(" ")[0]}</span></Link>; })}</div></nav>
  </div>;
}
function NavList({ currentPath, onPick, kycVerified, collapsed = false, instance = "desktop" }) {
  const { t } = useAppPreferences();
  return <nav className="space-y-1">{NAV.map((item) => { const Icon = item.icon; const active = currentPath === item.to || (item.to !== "/label/dashboard" && currentPath.startsWith(item.to)); const testId = instance === "desktop" ? item.tid : `${item.tid}-${instance}`; return <Link key={item.to} to={item.to} data-testid={testId} onClick={onPick} title={collapsed ? t(item.label) : undefined} className={`dashboard-nav-link relative flex items-center rounded-md py-2.5 ${collapsed ? "justify-center px-2" : "gap-3 px-3"} ${active ? "is-active" : ""}`}><Icon className="h-4 w-4 shrink-0" />{!collapsed && <span className="min-w-0 truncate text-sm font-semibold">{t(item.label)}</span>}{!item.kycFree && !kycVerified && !collapsed && <LockKeyhole className="ml-auto h-3.5 w-3.5 shrink-0 opacity-60" data-testid={`${testId}-lock`} />}</Link>; })}</nav>;
}