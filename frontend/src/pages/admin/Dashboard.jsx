import React, { useEffect, useState } from "react";
import { api } from "@/api/client";
import { ADMIN_DASHBOARD } from "@/constants/testIds";
import { Building2, Users2, Disc3, FileSpreadsheet, CreditCard, Banknote, MessageSquare, Crown, ShieldOff, Activity, BarChart3 } from "lucide-react";

function fmtIDR(n) {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
}

export default function AdminDashboard() {
  const [m, setM] = useState(null);

  useEffect(() => { api.get("/admin/dashboard").then(r => setM(r.data)); }, []);

  if (!m) return <div className="text-slate-500">Memuat metrik admin…</div>;

  return (
    <div className="space-y-6">
      <div>
        <div className="text-xs uppercase tracking-widest text-slate-500 font-bold">Overview</div>
        <h1 className="font-display text-3xl md:text-4xl font-extrabold tracking-tighter">Admin Dashboard</h1>
        <p className="text-sm text-slate-600 mt-1">Metrik operasional platform RILIS MUSIK.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <Stat testId={ADMIN_DASHBOARD.totalLabels} label="Total Label" value={m.total_labels} icon={Building2} accent="rose" />
        <Stat label="Total Artist" value={m.total_artists} icon={Users2} accent="indigo" />
        <Stat testId={ADMIN_DASHBOARD.totalReleases} label="Total Rilisan" value={m.total_releases} icon={Disc3} accent="amber" />
        <Stat testId={ADMIN_DASHBOARD.pendingReview} label="Antrian Review" value={m.pending_review} icon={Activity} accent="orange" />

        <Stat label="Delivered" value={m.delivered} icon={Disc3} accent="indigo" />
        <Stat label="Live di DSP" value={m.live} icon={BarChart3} accent="emerald" />
        <Stat label="Subscription Aktif" value={m.active_subscriptions} icon={Crown} accent="amber" />
        <Stat label="Label Suspended" value={m.suspended_labels} icon={ShieldOff} accent="rose" />

        <Stat testId={ADMIN_DASHBOARD.pendingInvoices} label="Invoice Pending" value={m.pending_invoices} icon={CreditCard} accent="orange" />
        <Stat label="Invoice Paid" value={m.paid_invoices} icon={CreditCard} accent="emerald" />
        <Stat label="Withdraw Pending" value={m.pending_withdraws} icon={Banknote} accent="amber" />
        <Stat label="Tiket Aktif" value={m.active_tickets} icon={MessageSquare} accent="indigo" />
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="rm-card p-5">
          <div className="text-xs uppercase tracking-widest font-bold text-slate-500 mb-3 flex items-center gap-2"><FileSpreadsheet className="w-4 h-4" /> Royalti</div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-slate-500">Total Revenue EUR</div>
              <div className="font-display text-2xl font-extrabold tracking-tight">€ {(m.total_revenue_eur || 0).toLocaleString("en-US", { maximumFractionDigits: 2 })}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Total Revenue IDR</div>
              <div className="font-display text-2xl font-extrabold tracking-tight">{fmtIDR(m.total_revenue_idr)}</div>
            </div>
          </div>
          <div className="mt-4 text-xs text-slate-500">
            CSV terakhir: {m.last_csv_import ? `${m.last_csv_import.period} • ${m.last_csv_import.created_at?.slice(0, 10)}` : "Belum ada"}
          </div>
        </div>
        <div className="rm-card p-5">
          <div className="text-xs uppercase tracking-widest font-bold text-slate-500 mb-3">Quick Tips</div>
          <ul className="text-sm text-slate-700 space-y-2 leading-relaxed">
            <li>📦 Review rilisan di menu <b>Release Management</b>.</li>
            <li>💳 Verifikasi pembayaran Xendit (MOCK) di menu <b>Xendit Payments</b>.</li>
            <li>🎨 Atur konten landing page di menu <b>Landing Page CMS</b>.</li>
            <li>👥 Tambah admin user (multi-role) di menu <b>Admin Users</b>.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, icon: Icon, accent, testId }) {
  const c = {
    rose: "from-rose-50 to-rose-100 text-rose-600",
    indigo: "from-indigo-50 to-indigo-100 text-indigo-600",
    amber: "from-amber-50 to-amber-100 text-amber-600",
    orange: "from-orange-50 to-orange-100 text-orange-600",
    emerald: "from-emerald-50 to-emerald-100 text-emerald-600",
  }[accent] || "from-slate-50 to-slate-100 text-slate-600";
  return (
    <div className="rm-card p-5" data-testid={testId}>
      <div className="flex items-center justify-between">
        <div className="text-[11px] uppercase tracking-widest font-bold text-slate-500">{label}</div>
        <div className={`w-8 h-8 rounded-xl bg-gradient-to-br ${c} grid place-items-center`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="font-display font-extrabold tracking-tighter text-3xl mt-2">{value}</div>
    </div>
  );
}
