import React from "react";
import { Link, useLocation, useNavigate, Outlet } from "react-router-dom";
import { useAuth } from "@/api/AuthContext";
import { ADMIN_NAV } from "@/constants/testIds";
import { BrandInline } from "@/components/shared/Brand";
import NotificationBell from "@/components/shared/NotificationBell";
import {
  LayoutDashboard, Building2, UserSquare, Disc3, CreditCard, FileSpreadsheet,
  Banknote, MessageSquare, LayoutTemplate, FileSignature, Music, Users2, ScrollText, LogOut, DatabaseZap, BarChart3
} from "lucide-react";

const NAV = [
  { to: "/admin/dashboard", label: "Dashboard", icon: LayoutDashboard, tid: ADMIN_NAV.dashboard, roles: ["super_admin", "admin_release", "admin_finance", "admin_support", "admin_content", "admin_marketing"] },
  { to: "/admin/analytics", label: "Analytics Royalti", icon: BarChart3, tid: "admin-nav-analytics", roles: ["super_admin", "admin_finance"] },
  { to: "/admin/labels", label: "Label Management", icon: Building2, tid: ADMIN_NAV.labels, roles: ["super_admin", "admin_release", "admin_finance", "admin_support"] },
  { to: "/admin/artists", label: "Artist Management", icon: UserSquare, tid: ADMIN_NAV.artists, roles: ["super_admin", "admin_release", "admin_finance", "admin_support"] },
  { to: "/admin/releases", label: "Release Management", icon: Disc3, tid: ADMIN_NAV.releases, roles: ["super_admin", "admin_release"] },
  { to: "/admin/payments", label: "Xendit Payments", icon: CreditCard, tid: ADMIN_NAV.payments, roles: ["super_admin", "admin_finance"] },
  { to: "/admin/royalty", label: "Royalty Import", icon: FileSpreadsheet, tid: ADMIN_NAV.royaltyImport, roles: ["super_admin", "admin_finance"] },
  { to: "/admin/withdraw", label: "Withdraw", icon: Banknote, tid: ADMIN_NAV.withdraw, roles: ["super_admin", "admin_finance"] },
  { to: "/admin/wami", label: "WAMI Registrations", icon: Music, tid: "admin-nav-wami", roles: ["super_admin", "admin_release"] },
  { to: "/admin/tickets", label: "Support Tickets", icon: MessageSquare, tid: ADMIN_NAV.tickets, roles: ["super_admin", "admin_support"] },
  { to: "/admin/cms", label: "Landing Page CMS", icon: LayoutTemplate, tid: ADMIN_NAV.cms, roles: ["super_admin", "admin_content"] },
  { to: "/admin/contracts", label: "Contracts", icon: FileSignature, tid: ADMIN_NAV.contracts, roles: ["super_admin", "admin_release"] },
  { to: "/admin/admin-users", label: "Admin Users", icon: Users2, tid: ADMIN_NAV.adminUsers, roles: ["super_admin"] },
  { to: "/admin/migrate", label: "Klaim Akun", icon: DatabaseZap, tid: "admin-nav-migrate", roles: ["super_admin"] },
  { to: "/admin/activity-logs", label: "Activity Logs", icon: ScrollText, tid: ADMIN_NAV.activityLogs, roles: ["super_admin", "admin_finance", "admin_release"] },
];

const ROLE_LABELS = {
  super_admin: "Super Admin",
  admin_release: "Admin Release",
  admin_finance: "Admin Finance",
  admin_support: "Admin Support",
  admin_content: "Admin Content/CMS",
  admin_marketing: "Admin Marketing",
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
    <div className="min-h-screen bg-[#08070D] text-white flex">
      {/* Sidebar */}
      <aside className="hidden md:flex flex-col w-72 min-h-screen sticky top-0 bg-[#0B0915] border-r border-white/5 text-zinc-300 p-5">
        <Link to="/admin/dashboard" className="mb-8">
          <BrandInline size={38} subtitle="Admin Console" />
        </Link>

        <div className="text-[11px] uppercase tracking-widest text-zinc-500 font-semibold mb-2 px-2">Operations</div>
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
                  active ? "text-white shadow-md" : "text-zinc-300 hover:bg-white/5"
                }`}
                style={active ? { background: "linear-gradient(135deg, #FF1F8E, #A24EFF)" } : {}}
              >
                <Icon className="w-4 h-4" />
                <span>{n.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto pt-6 border-t border-white/5">
          <div className="text-xs text-zinc-500">Login as</div>
          <div className="font-semibold text-sm text-white truncate">{user?.name}</div>
          <div className="text-xs text-zinc-500 truncate">{ROLE_LABELS[user?.role] || user?.role}</div>
          <button onClick={onLogout} className="mt-3 w-full flex items-center gap-2 text-sm text-zinc-300 hover:text-white p-2 rounded-lg hover:bg-white/5" data-testid="admin-logout-button">
            <LogOut className="w-4 h-4" /> Logout
          </button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-40 bg-[#0B0915] border-b border-white/5 text-white p-4 flex justify-between items-center">
        <Link to="/admin/dashboard"><BrandInline size={30} /></Link>
        <div className="flex items-center gap-2">
          <NotificationBell />
          <button onClick={onLogout} className="text-sm text-zinc-300" data-testid="admin-logout-mobile">Logout</button>
        </div>
      </div>

      <main className="flex-1 p-4 md:p-8 mt-16 md:mt-0 max-w-full overflow-x-hidden text-zinc-100 relative">
        <div className="hidden md:flex absolute top-4 right-6 z-30">
          <NotificationBell />
        </div>
        <Outlet />
      </main>
    </div>
  );
}
