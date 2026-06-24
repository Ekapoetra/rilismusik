import React from "react";
import { Link, useLocation, useNavigate, Outlet } from "react-router-dom";
import { useAuth } from "@/api/AuthContext";
import { ADMIN_NAV } from "@/constants/testIds";
import {
  LayoutDashboard, Building2, UserSquare, Disc3, CreditCard, FileSpreadsheet,
  Banknote, MessageSquare, LayoutTemplate, FileSignature, ShieldAlert, Users2, ScrollText, LogOut
} from "lucide-react";

const NAV = [
  { to: "/admin/dashboard", label: "Dashboard", icon: LayoutDashboard, tid: ADMIN_NAV.dashboard, roles: ["super_admin", "admin_release", "admin_finance", "admin_support", "admin_content"] },
  { to: "/admin/labels", label: "Label Management", icon: Building2, tid: ADMIN_NAV.labels, roles: ["super_admin", "admin_release", "admin_finance", "admin_support"] },
  { to: "/admin/artists", label: "Artist Management", icon: UserSquare, tid: ADMIN_NAV.artists, roles: ["super_admin", "admin_release", "admin_finance", "admin_support"] },
  { to: "/admin/releases", label: "Release Management", icon: Disc3, tid: ADMIN_NAV.releases, roles: ["super_admin", "admin_release"] },
  { to: "/admin/payments", label: "Xendit Payments", icon: CreditCard, tid: ADMIN_NAV.payments, roles: ["super_admin", "admin_finance"] },
  { to: "/admin/royalty", label: "Royalty Import", icon: FileSpreadsheet, tid: ADMIN_NAV.royaltyImport, roles: ["super_admin", "admin_finance"] },
  { to: "/admin/withdraw", label: "Withdraw", icon: Banknote, tid: ADMIN_NAV.withdraw, roles: ["super_admin", "admin_finance"] },
  { to: "/admin/tickets", label: "Support Tickets", icon: MessageSquare, tid: ADMIN_NAV.tickets, roles: ["super_admin", "admin_support"] },
  { to: "/admin/cms", label: "Landing Page CMS", icon: LayoutTemplate, tid: ADMIN_NAV.cms, roles: ["super_admin", "admin_content"] },
  { to: "/admin/contracts", label: "Contracts", icon: FileSignature, tid: ADMIN_NAV.contracts, roles: ["super_admin", "admin_release"] },
  { to: "/admin/admin-users", label: "Admin Users", icon: Users2, tid: ADMIN_NAV.adminUsers, roles: ["super_admin"] },
  { to: "/admin/activity-logs", label: "Activity Logs", icon: ScrollText, tid: ADMIN_NAV.activityLogs, roles: ["super_admin", "admin_finance", "admin_release"] },
];

const ROLE_LABELS = {
  super_admin: "Super Admin",
  admin_release: "Admin Release",
  admin_finance: "Admin Finance",
  admin_support: "Admin Support",
  admin_content: "Admin Content/CMS",
};

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const loc = useLocation();
  const navigate = useNavigate();
  const items = NAV.filter((n) => !user || n.roles.includes(user.role));

  const onLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-[#F4F5F7] flex">
      {/* Sidebar */}
      <aside className="hidden md:flex flex-col w-72 min-h-screen sticky top-0 bg-[#0B0B0F] text-slate-200 p-5">
        <Link to="/admin/dashboard" className="flex items-center gap-2 mb-8">
          <div className="w-10 h-10 rounded-2xl bg-[#FF3B30] text-white grid place-items-center font-bold text-xl">R</div>
          <div>
            <div className="font-display font-extrabold tracking-tight text-lg leading-none text-white">RILIS MUSIK</div>
            <div className="text-xs text-slate-400 mt-1">Admin Console</div>
          </div>
        </Link>

        <div className="text-[11px] uppercase tracking-widest text-slate-500 font-semibold mb-2 px-2">Operations</div>
        <nav className="space-y-1">
          {items.map((n) => {
            const Icon = n.icon;
            const active = loc.pathname.startsWith(n.to);
            return (
              <Link
                key={n.to}
                to={n.to}
                data-testid={n.tid}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all text-sm font-semibold ${
                  active ? "bg-[#FF3B30] text-white shadow-md" : "text-slate-300 hover:bg-white/5"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{n.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto pt-6 border-t border-white/10">
          <div className="text-xs text-slate-500">Login as</div>
          <div className="font-semibold text-sm text-white truncate">{user?.name}</div>
          <div className="text-xs text-slate-400 truncate">{ROLE_LABELS[user?.role] || user?.role}</div>
          <button onClick={onLogout} className="mt-3 w-full flex items-center gap-2 text-sm text-slate-300 hover:text-white p-2 rounded-lg hover:bg-white/5" data-testid="admin-logout-button">
            <LogOut className="w-4 h-4" /> Logout
          </button>
        </div>
      </aside>

      {/* Mobile top bar - admin is desktop first, mobile is minimal */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-40 bg-[#0B0B0F] text-white p-4 flex justify-between items-center">
        <Link to="/admin/dashboard" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-[#FF3B30] grid place-items-center font-bold">R</div>
          <span className="font-display font-extrabold">RILIS Admin</span>
        </Link>
        <button onClick={onLogout} className="text-sm text-slate-300" data-testid="admin-logout-mobile">Logout</button>
      </div>

      <main className="flex-1 p-4 md:p-8 mt-16 md:mt-0 max-w-full overflow-x-hidden">
        <Outlet />
      </main>
    </div>
  );
}
