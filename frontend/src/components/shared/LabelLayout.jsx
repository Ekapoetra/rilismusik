import React, { Suspense, useState } from "react";
import { Link, useLocation, useNavigate, Outlet } from "react-router-dom";
import { useAuth } from "@/api/AuthContext";
import { LABEL_NAV } from "@/constants/testIds";
import { LabelKycProvider, useLabelKyc } from "@/contexts/LabelKycContext";
import NotificationBell from "./NotificationBell";
import LabelSwitcher from "./LabelSwitcher";
import { HeaderPreferences } from "./HeaderPreferences";
import { KycGate } from "./KycGate";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import LabelChatWidget from "@/components/chat/LabelChatWidget";
import { LanguageToggle, Masthead, MastheadProvider, ThemeSwitch, useV13Document } from "@/components/v13/Masthead";
import { V13Sidebar } from "@/components/v13/V13Sidebar";
import { PlanChip } from "@/components/v13/Plans";
import { LayoutDashboard, Disc3, UploadCloud, Users, BarChart3, Wallet, LifeBuoy, FileText, FileSignature, Music, Settings, LogOut } from "lucide-react";

// V13 label menu order and names; Artis and Kontrak stay because production uses them.
const NAV = [
  { to: "/label/dashboard", label: "Dashboard", icon: LayoutDashboard, tid: LABEL_NAV.dashboard, kycFree: true },
  { to: "/label/releases", label: "Rilisan", icon: Disc3, tid: LABEL_NAV.releases },
  { to: "/label/royalty", label: "Royalti", icon: BarChart3, tid: LABEL_NAV.royalty },
  { to: "/label/withdraw", label: "Penarikan", icon: Wallet, tid: LABEL_NAV.withdraw },
  { to: "/label/invoices", label: "Transaksi", icon: FileText, tid: LABEL_NAV.invoices },
  { to: "/label/wami", label: "Registrasi WAMI", icon: Music, tid: "label-nav-wami" },
  { to: "/label/support", label: "Tiket Bantuan", icon: LifeBuoy, tid: LABEL_NAV.support },
  { to: "/label/profile", label: "Profil Label", icon: Settings, tid: LABEL_NAV.profile, kycFree: true },
  { to: "/label/artists", label: "Artis", icon: Users, tid: LABEL_NAV.artists },
  { to: "/label/contract", label: "Kontrak", icon: FileSignature, tid: "label-nav-contract", kycFree: true },
];
const UPLOAD_NAV = { to: "/label/releases/upload", label: "Ajukan", icon: UploadCloud, tid: LABEL_NAV.uploadRelease };
const BOTTOM_NAV = [NAV[0], UPLOAD_NAV, NAV[1], NAV[2], NAV[3]];
const isKycFreePath = (path) => ["/label/dashboard", "/label/profile", "/label/contract"].some((allowed) => path === allowed || path.startsWith(`${allowed}/`));

export default function LabelLayout() {
  return <LabelKycProvider><LabelShell /></LabelKycProvider>;
}
function LabelShell() {
  useV13Document();
  const { user, profile, logout } = useAuth();
  const { t } = useAppPreferences();
  const loc = useLocation(); const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(localStorage.getItem("label-sidebar-collapsed") === "true");
  const { kyc, loading: kycLoading } = useLabelKyc();
  const locked = !isKycFreePath(loc.pathname) && (kycLoading || !kyc?.is_verified);
  const onLogout = async () => { await logout(); navigate("/login"); };
  const toggle = () => setCollapsed((value) => { localStorage.setItem("label-sidebar-collapsed", String(!value)); return !value; });
  const isActive = (item) => loc.pathname === item.to || (item.to !== "/label/dashboard" && loc.pathname.startsWith(`${item.to}/`));
  const links = NAV.map((item) => ({ key: item.to, to: item.to, label: t(item.label), icon: item.icon, active: isActive(item), locked: !item.kycFree && !kyc?.is_verified, testId: item.tid }));
  const name = profile?.label_name || user?.name || "Label";
  const footer = { name, sub: user?.email };
  const tools = <><PlanChip /><LabelSwitcher /><ThemeSwitch /><LanguageToggle /><span className="v13-optional"><HeaderPreferences instance="label" show={["sound"]} /></span><NotificationBell instance="label-header" /><button type="button" onClick={onLogout} title={t("Keluar")} aria-label={t("Keluar")} className="ui-icon-button" data-testid="label-logout-button-desktop"><LogOut className="h-4 w-4" /></button></>;
  return <MastheadProvider><div className="app-shell v13-shell" data-testid="label-layout">
    <Masthead name={name} home={loc.pathname === "/label/dashboard"} searchItems={links.map((link) => ({ to: link.to, label: link.label }))} tools={tools} brandTo="/label/dashboard" onMenu={() => setOpen(true)} />
    {open && <div className="v13-drawer md:hidden" data-testid="label-mobile-sidebar"><button type="button" onClick={() => setOpen(false)} aria-label={t("Tutup menu")} data-testid="label-mobile-menu-backdrop" /><aside><V13Sidebar instance="mobile" links={links} onNavigate={() => setOpen(false)} footer={footer} /><button type="button" onClick={onLogout} className="mt-4 flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-red-500" data-testid="label-logout-button"><LogOut className="h-4 w-4" />{t("Keluar")}</button></aside></div>}
    <div style={{ "--rm-dock-left": collapsed ? "88px" : "272px" }} className={`v13-body ${collapsed ? "has-collapsed-side" : ""}`}>
      <V13Sidebar links={links} collapsed={collapsed} onToggle={toggle} footer={footer} />
      <main className="label-page-content v13-main relative min-w-0"><div className={locked ? "pointer-events-none select-none blur-md opacity-35" : ""} aria-hidden={locked || undefined} data-testid="label-route-content"><Suspense fallback={<div role="status" className="p-8 text-center text-[var(--ui-muted)]">Memuat halaman…</div>}><Outlet /></Suspense></div>{locked && <KycGate status={kyc?.status} loading={kycLoading} />}</main>
    </div>
    <LabelChatWidget />
    <nav className="dashboard-header fixed inset-x-0 bottom-0 z-30 border-t md:hidden" data-testid="label-bottom-navigation"><div className="grid grid-cols-5 gap-1 p-2">{BOTTOM_NAV.map((item) => { const Icon = item.icon; const active = item === NAV[1] ? loc.pathname.startsWith(item.to) && !loc.pathname.startsWith(UPLOAD_NAV.to) : loc.pathname.startsWith(item.to); return <Link key={item.to} to={item.to} data-testid={`${item.tid}-bottom`} className={`flex min-w-0 flex-col items-center gap-1 rounded-md py-2 text-[10px] font-semibold ${active ? "bg-[var(--ui-hover)] text-[var(--ui-text)]" : "text-[var(--ui-muted)]"}`}><Icon className="h-4 w-4" /><span className="max-w-full truncate">{t(item.label).split(" ")[0]}</span></Link>; })}</div></nav>
  </div></MastheadProvider>;
}
