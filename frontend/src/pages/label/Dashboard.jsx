import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import { LABEL_DASHBOARD } from "@/constants/testIds";
import StatusBadge from "@/components/shared/StatusBadge";
import { Disc3, Users, Wallet, AlertCircle, Receipt, Crown, ShieldCheck } from "lucide-react";

function fmtIDR(n) {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
}

export default function LabelDashboardHome() {
  const [data, setData] = useState(null);
  const [releases, setReleases] = useState([]);

  useEffect(() => {
    api.get("/label/dashboard").then((r) => setData(r.data)).catch(() => {});
    api.get("/releases/").then((r) => setReleases(r.data.slice(0, 5))).catch(() => {});
  }, []);

  if (!data) return <div className="text-slate-500">Memuat…</div>;
  const { stats, label } = data;

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-slate-500 font-bold">Dashboard</div>
          <h1 className="font-display text-3xl md:text-4xl font-extrabold tracking-tighter">Halo, {label.label_name}</h1>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Link to="/label/releases/upload" data-testid={LABEL_DASHBOARD.uploadReleaseButton} className="rm-btn-primary">+ Submit Rilisan</Link>
          <Link to="/label/withdraw" data-testid={LABEL_DASHBOARD.withdrawButton} className="rm-btn-ghost">Withdraw</Link>
        </div>
      </div>

      {/* Status row */}
      <div className="flex flex-wrap gap-2">
        <StatusPill icon={Crown} label={`Subscription: ${stats.subscription_status === "active" ? "Aktif" : "Tidak Aktif"}`} active={stats.subscription_status === "active"} />
        <StatusPill icon={ShieldCheck} label={`Kontrak: ${stats.contract_status === "contract_active" ? "Aktif" : stats.contract_status?.replace("_", " ") || "—"}`} active={stats.contract_status === "contract_active"} />
        <StatusPill icon={Receipt} label={`Tipe: ${stats.payment_type === "annual_subscription" ? "Annual" : "Pay Per Release"}`} active />
        {!stats.bank_verified && <StatusPill icon={AlertCircle} label="Rekening belum diverifikasi" warn />}
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard testId={LABEL_DASHBOARD.balanceAvailable} label="Saldo Tersedia" value={fmtIDR(stats.balance_available_idr)} icon={Wallet} accent="emerald" />
        <StatCard testId={LABEL_DASHBOARD.balancePending} label="Saldo Pending" value={fmtIDR(stats.balance_pending_idr)} icon={Receipt} accent="amber" />
        <StatCard label="Withdraw Diproses" value={fmtIDR(stats.balance_withdraw_requested_idr)} icon={Receipt} accent="blue" />
        <StatCard label="Revenue Bulan Lalu" value={fmtIDR(stats.last_month_revenue_idr)} sub={stats.last_month_period} icon={Disc3} accent="rose" />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard testId={LABEL_DASHBOARD.totalReleases} label="Total Rilisan Aktif" value={stats.active_releases} icon={Disc3} mini />
        <StatCard label="Total Track" value={stats.total_tracks} icon={Disc3} mini />
        <StatCard testId={LABEL_DASHBOARD.totalArtists} label="Total Artist" value={stats.total_artists} icon={Users} mini />
        <StatCard label="Tiket Aktif" value={stats.active_tickets} icon={AlertCircle} mini />
      </div>

      {/* Recent releases */}
      <div className="rm-card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-display font-bold text-lg tracking-tight">Rilisan Terbaru</h3>
          <Link to="/label/releases" className="text-sm font-semibold text-[#FF3B30]">Lihat semua →</Link>
        </div>
        {releases.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-sm">
            Belum ada rilisan. <Link to="/label/releases/upload" className="font-semibold text-[#FF3B30]">Upload sekarang</Link>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {releases.map((r) => (
              <div key={r.id} className="py-3 flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-orange-400 to-pink-500 grid place-items-center text-white">
                    <Disc3 className="w-5 h-5" />
                  </div>
                  <div className="min-w-0">
                    <div className="font-semibold text-sm truncate">{r.release_title}</div>
                    <div className="text-xs text-slate-500">{r.artist_name} • {r.release_date}</div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={r.status} />
                  <Link to={`/label/releases/${r.id}`} className="text-xs font-semibold text-slate-700 hover:text-[#FF3B30]">Detail →</Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, sub, icon: Icon, accent, mini, testId }) {
  const colors = {
    emerald: "from-emerald-50 to-emerald-100 text-emerald-600",
    amber: "from-amber-50 to-amber-100 text-amber-600",
    blue: "from-sky-50 to-sky-100 text-sky-600",
    rose: "from-rose-50 to-rose-100 text-rose-600",
  };
  const cl = colors[accent] || "from-slate-50 to-slate-100 text-slate-600";
  return (
    <div className={`rm-card ${mini ? "p-4" : "p-5"}`} data-testid={testId}>
      <div className="flex items-center justify-between">
        <div className="text-[11px] uppercase tracking-widest font-bold text-slate-500">{label}</div>
        {Icon && (
          <div className={`w-8 h-8 rounded-xl bg-gradient-to-br ${cl} grid place-items-center`}>
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>
      <div className={`font-display font-extrabold tracking-tighter ${mini ? "text-2xl" : "text-2xl md:text-3xl"} mt-2`}>{value}</div>
      {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
    </div>
  );
}

function StatusPill({ icon: Icon, label, active, warn }) {
  let cls = "bg-slate-100 text-slate-600";
  if (active) cls = "bg-emerald-50 text-emerald-700";
  if (warn) cls = "bg-amber-50 text-amber-700";
  return (
    <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold ${cls}`}>
      <Icon className="w-3.5 h-3.5" />
      {label}
    </div>
  );
}
