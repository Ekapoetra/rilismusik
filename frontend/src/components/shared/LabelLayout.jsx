import React, { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate, Outlet } from "react-router-dom";
import { useAuth } from "@/api/AuthContext";
import { LABEL_NAV } from "@/constants/testIds";
import { api } from "@/api/client";
import { LogoMark, BrandInline } from "@/components/shared/Brand";
import NotificationBell from "@/components/shared/NotificationBell";
import { KycGate } from "@/components/shared/KycGate";
import LabelChatWidget from "@/components/chat/LabelChatWidget";
import {
  LayoutDashboard, Disc3, UploadCloud, Users, BarChart3, Wallet, LifeBuoy, FileText, FileSignature, Music, Settings, LogOut, Menu, X, LockKeyhole
} from "lucide-react";

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
  const loc = useLocation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [kyc, setKyc] = useState(profile?.kyc || null);
  const [kycLoading, setKycLoading] = useState(true);

  const loadKyc = useCallback(async () => {
    setKycLoading(true);
    try { const { data } = await api.get("/label/kyc"); setKyc(data); }
    catch { setKyc({ status: "incomplete", is_verified: false }); }
    finally { setKycLoading(false); }
  }, []);

  useEffect(() => { loadKyc(); }, [loadKyc, loc.pathname]);
  useEffect(() => {
    const update = (event) => setKyc(event.detail);
    window.addEventListener("rilismusik:kyc-updated", update);
    return () => window.removeEventListener("rilismusik:kyc-updated", update);
  }, []);
  const restricted = !isKycFreePath(loc.pathname);
  const locked = restricted && (kycLoading || !kyc?.is_verified);

  const onLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen rm-mesh-dim text-white">
      {/* Mobile top bar */}
      <header className="md:hidden sticky top-0 z-40 px-4 py-3 flex items-center justify-between rm-glass-strong" style={{ borderRadius: 0 }}>
        <Link to="/label/dashboard">
          <BrandInline size={32} />
        </Link>
        <div className="flex items-center gap-1">
          <NotificationBell instance="mobile" />
          <button onClick={() => setOpen(!open)} className="p-2 text-white" data-testid="label-mobile-menu-button">
            {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </header>

      {/* Mobile drawer */}
      {open && (
        <div className="md:hidden fixed inset-0 z-30 bg-black/70" onClick={() => setOpen(false)}>
          <div className="absolute top-14 right-0 w-72 h-[calc(100%-3.5rem)] bg-[#0E0C16] border-l border-white/5 p-4 shadow-2xl rm-fade-up" onClick={(e) => e.stopPropagation()}>
            <NavList currentPath={loc.pathname} onPick={() => setOpen(false)} kycVerified={kyc?.is_verified} />
            <button onClick={onLogout} className="mt-4 w-full text-left flex items-center gap-2 text-sm text-zinc-300 hover:text-white p-3 rounded-xl hover:bg-white/5" data-testid="label-logout-button">
              <LogOut className="w-4 h-4" /> Logout
            </button>
          </div>
        </div>
      )}

      <div className="flex">
        {/* Desktop sidebar */}
        <aside className="hidden md:flex flex-col w-64 min-h-screen sticky top-0 p-5 bg-[#0B0915]/80 backdrop-blur-xl border-r border-white/5">
          <Link to="/label/dashboard" className="mb-8">
            <BrandInline size={38} subtitle="Label Dashboard" />
          </Link>
          <div className="text-[11px] uppercase tracking-widest text-zinc-500 font-semibold mb-2">Menu</div>
          <NavList currentPath={loc.pathname} onPick={() => {}} kycVerified={kyc?.is_verified} />
          <div className="mt-auto pt-4 border-t border-white/5">
            <div className="text-xs text-zinc-500">Login as</div>
            <div className="font-semibold text-sm truncate text-white">{profile?.label_name || user?.name}</div>
            <div className="text-xs text-zinc-500 truncate">{user?.email}</div>
            <button onClick={onLogout} className="mt-3 w-full flex items-center gap-2 text-sm text-zinc-300 hover:text-white p-2 rounded-lg hover:bg-white/5" data-testid="label-logout-button-desktop">
              <LogOut className="w-4 h-4" /> Logout
            </button>
          </div>
        </aside>

        <main className="flex-1 p-4 md:p-8 pb-24 md:pb-8 overflow-x-hidden relative">
          {/* Floating bell - desktop only */}
          <div className="hidden md:flex absolute top-4 right-6 z-30">
            <NotificationBell instance="desktop" />
          </div>
          <div className={locked ? "pointer-events-none select-none blur-md opacity-35" : ""} aria-hidden={locked || undefined} data-testid="label-route-content"><Outlet /></div>
          {locked && <KycGate status={kyc?.status} loading={kycLoading} />}
        </main>
      </div>
      <LabelChatWidget />

      {/* Mobile bottom nav */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-30 rm-glass-strong border-t border-white/5" style={{ borderRadius: 0 }}>
        <div className="grid grid-cols-5 px-2 py-2">
          {[NAV[0], NAV[1], NAV[3], NAV[4], NAV[8]].map((n) => {
            const Active = loc.pathname.startsWith(n.to);
            const Icon = n.icon;
            return (
              <Link
                key={n.to}
                to={n.to}
                data-testid={n.tid}
                className={`relative flex flex-col items-center gap-1 py-2 ${Active ? "text-white" : "text-zinc-500"}`}
              >
                {Active ? (
                  <span className="w-9 h-9 rounded-xl grid place-items-center" style={{ background: "linear-gradient(135deg, #FF1F8E, #A24EFF)" }}>
                    <Icon className="w-4 h-4" />
                  </span>
                ) : (
                  <Icon className="w-5 h-5" />
                )}
                <span className="text-[10px] font-semibold">{n.label.split(" ")[0]}</span>
                {!n.kycFree && !kyc?.is_verified && <LockKeyhole className="absolute right-2 top-2 h-3 w-3" data-testid={`${n.tid}-lock`} />}
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}

function NavList({ currentPath, onPick, kycVerified }) {
  return (
    <nav className="space-y-1">
      {NAV.map((n) => {
        const Icon = n.icon;
        const active = currentPath === n.to || (n.to !== "/label/dashboard" && currentPath.startsWith(n.to));
        return (
          <Link
            key={n.to}
            to={n.to}
            data-testid={n.tid}
            onClick={onPick}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all ${
              active
                ? "text-white shadow-md"
                : "text-zinc-300 hover:bg-white/5"
            }`}
            style={active ? { background: "linear-gradient(135deg, #FF1F8E, #A24EFF)" } : {}}
          >
            <Icon className="w-4 h-4" />
            <span className="text-sm font-semibold">{n.label}</span>
            {!n.kycFree && !kycVerified && <LockKeyhole className="ml-auto h-3.5 w-3.5 text-zinc-500" data-testid={`${n.tid}-lock`} />}
          </Link>
        );
      })}
    </nav>
  );
}
