import React, { useEffect, useState } from "react";
import { api } from "@/api/client";
import { ADMIN_DASHBOARD } from "@/constants/testIds";
import { Building2, Users2, Disc3, FileSpreadsheet, CreditCard, Banknote, MessageSquare, Crown, ShieldOff, Activity, BarChart3, AlertTriangle, X } from "lucide-react";

function fmtIDR(n) {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
}

const PRODUCTION_BANNERS = [
  {
    id: "storage-ephemeral",
    severity: "warn",
    title: "Cloud storage belum aktif — upload file akan ephemeral",
    body: "WAV audio, cover image, dan PDF contract yang baru di-upload TIDAK persisten saat pod restart. Tunda upload audio/cover untuk label aktif sampai integrasi cloud storage (S3/Cloudinary) selesai. MDA PDF aman karena bisa di-regenerate dari CMS.",
  },
  {
    id: "email-mock",
    severity: "info",
    title: "Email notifikasi belum live — token verify & forgot password hanya di backend log",
    body: "Untuk reset password / verify email, cek backend log: tail -n 200 /var/log/supervisor/backend.err.log",
  },
];

function DismissibleBanner({ b, onDismiss }) {
  const color = b.severity === "warn"
    ? "bg-amber-500/10 border-amber-500/30 text-amber-100"
    : "bg-indigo-500/10 border-indigo-500/30 text-indigo-100";
  return (
    <div className={`rounded-2xl border ${color} p-4 flex items-start gap-3`} data-testid={`admin-banner-${b.id}`}>
      <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
      <div className="flex-1">
        <div className="font-semibold text-sm">{b.title}</div>
        <div className="text-xs opacity-80 mt-1 leading-relaxed">{b.body}</div>
      </div>
      <button
        onClick={() => onDismiss(b.id)}
        className="opacity-60 hover:opacity-100 transition flex-shrink-0"
        aria-label="dismiss"
        data-testid={`admin-banner-dismiss-${b.id}`}
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

export default function AdminDashboard() {
  const [m, setM] = useState(null);
  const [dismissed, setDismissed] = useState(() => {
    try { return JSON.parse(localStorage.getItem("rm-admin-banners-dismissed") || "[]"); }
    catch { return []; }
  });

  useEffect(() => { api.get("/admin/dashboard").then(r => setM(r.data)); }, []);

  const dismiss = (id) => {
    const next = [...new Set([...dismissed, id])];
    setDismissed(next);
    localStorage.setItem("rm-admin-banners-dismissed", JSON.stringify(next));
  };
  const visibleBanners = PRODUCTION_BANNERS.filter(b => !dismissed.includes(b.id));

  if (!m) return <div className="text-zinc-500">Memuat metrik admin…</div>;

  return (
    <div className="space-y-6">
      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Overview</div>
        <h1 className="font-display text-3xl md:text-4xl font-extrabold tracking-tighter">Admin Dashboard</h1>
        <p className="text-sm text-zinc-400 mt-1">Metrik operasional platform RILIS MUSIK.</p>
      </div>

      {visibleBanners.length > 0 && (
        <div className="space-y-2" data-testid="admin-production-banners">
          {visibleBanners.map(b => <DismissibleBanner key={b.id} b={b} onDismiss={dismiss} />)}
        </div>
      )}

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
          <div className="text-xs uppercase tracking-widest font-bold text-zinc-500 mb-3 flex items-center gap-2"><FileSpreadsheet className="w-4 h-4" /> Royalti</div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-zinc-500">Pendapatan Kotor EUR</div>
              <div className="font-display text-2xl font-extrabold tracking-tight">€ {(m.total_revenue_eur || 0).toLocaleString("en-US", { maximumFractionDigits: 2 })}</div>
            </div>
            <div>
              <div className="text-xs text-zinc-500">Total Bagian Label IDR</div>
              <div className="font-display text-2xl font-extrabold tracking-tight">{fmtIDR(m.total_revenue_idr)}</div>
            </div>
          </div>
          <div className="mt-4 text-xs text-zinc-500">
            CSV terakhir: {m.last_csv_import ? `${m.last_csv_import.period} • ${m.last_csv_import.created_at?.slice(0, 10)}` : "Belum ada"}
          </div>
        </div>
        <div className="rm-card p-5">
          <div className="text-xs uppercase tracking-widest font-bold text-zinc-500 mb-3">Quick Tips</div>
          <ul className="text-sm text-zinc-200 space-y-2 leading-relaxed">
            <li>📦 Review rilisan di menu <b>Release Management</b>.</li>
            <li>💳 Pantau dan sinkronkan pembayaran production di menu <b>Xendit Payments</b>.</li>
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
    rose: "from-rose-500/15 to-rose-500/5 text-rose-300",
    indigo: "from-indigo-500/15 to-indigo-500/5 text-indigo-300",
    amber: "from-amber-500/15 to-amber-500/5 text-amber-300",
    orange: "from-pink-500/15 to-purple-500/15 text-pink-300",
    emerald: "from-emerald-500/15 to-emerald-500/5 text-emerald-300",
  }[accent] || "from-slate-50 to-slate-100 text-zinc-400";
  return (
    <div className="rm-card p-5" data-testid={testId}>
      <div className="flex items-center justify-between">
        <div className="text-[11px] uppercase tracking-widest font-bold text-zinc-500">{label}</div>
        <div className={`w-8 h-8 rounded-xl bg-gradient-to-br ${c} grid place-items-center`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="font-display font-extrabold tracking-tighter text-3xl mt-2">{value}</div>
    </div>
  );
}
