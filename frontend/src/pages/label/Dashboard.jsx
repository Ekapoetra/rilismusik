import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import { LABEL_DASHBOARD } from "@/constants/testIds";
import StatusBadge from "@/components/shared/StatusBadge";
import { LabelAnalyticsOverview } from "@/components/label/LabelAnalyticsOverview";
import { useLabelAnalytics } from "@/hooks/useLabelAnalytics";
import { Disc3, Users, Wallet, AlertCircle, Receipt, Crown, ShieldCheck, Play } from "lucide-react";

function fmtIDR(n) {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
}

export default function LabelDashboardHome() {
  const [data, setData] = useState(null);
  const [releases, setReleases] = useState([]);
  const analytics = useLabelAnalytics();

  useEffect(() => {
    api.get("/label/dashboard").then((r) => setData(r.data)).catch(() => {});
    api.get("/releases/").then((r) => setReleases(r.data.slice(0, 5))).catch(() => {});
  }, []);

  if (!data) return <div className="text-zinc-500">Memuat…</div>;
  const { stats, label } = data;
  const totalUnwithdrawn = stats.balance_available_idr + stats.balance_pending_idr + stats.balance_withdraw_requested_idr;

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Dashboard</div>
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
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatCard testId={LABEL_DASHBOARD.balanceAvailable} label="Saldo Tersedia" value={fmtIDR(stats.balance_available_idr)} icon={Wallet} accent="emerald" />
        <StatCard testId={LABEL_DASHBOARD.balancePending} label="Saldo Pending" value={fmtIDR(stats.balance_pending_idr)} icon={Receipt} accent="amber" />
        <StatCard testId="label-dashboard-withdraw-processing" label="Withdraw Diproses" value={fmtIDR(stats.balance_withdraw_requested_idr)} icon={Receipt} accent="blue" />
        <StatCard testId="label-dashboard-unwithdrawn-total" label="Belum Ditarik" value={fmtIDR(totalUnwithdrawn)} icon={Wallet} accent="rose" />
        <StatCard testId="label-dashboard-latest-streams" label="Stream Terbaru" value={(analytics.data?.latest_report?.streams || 0).toLocaleString("id-ID")} sub={analytics.data?.latest_period} icon={Play} accent="blue" />
        <StatCard testId="label-dashboard-latest-revenue" label="Pendapatan Terbaru" value={fmtIDR(analytics.data?.latest_report?.revenue_idr)} sub={analytics.data?.latest_period} icon={Disc3} accent="emerald" />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard testId={LABEL_DASHBOARD.totalReleases} label="Total Rilisan Aktif" value={stats.active_releases} icon={Disc3} mini />
        <StatCard label="Total Track" value={stats.total_tracks} icon={Disc3} mini />
        <StatCard testId={LABEL_DASHBOARD.totalArtists} label="Total Artist" value={stats.total_artists} icon={Users} mini />
        <StatCard label="Tiket Aktif" value={stats.active_tickets} icon={AlertCircle} mini />
      </div>

      <LabelAnalyticsOverview analytics={analytics} />

      {/* Recent releases */}
      <div className="rm-card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-display font-bold text-lg tracking-tight">Rilisan Terbaru</h3>
          <Link to="/label/releases" className="text-sm font-semibold rm-gradient-text">Lihat semua →</Link>
        </div>
        {releases.length === 0 ? (
          <div className="text-center py-8 text-zinc-500 text-sm">
            Belum ada rilisan. <Link to="/label/releases/upload" className="font-semibold rm-gradient-text">Upload sekarang</Link>
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            {releases.map((r) => (
              <div key={r.id} className="py-3 flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-[#FF1F8E] to-[#A24EFF] grid place-items-center text-white">
                    <Disc3 className="w-5 h-5" />
                  </div>
                  <div className="min-w-0">
                    <div className="font-semibold text-sm truncate">{r.release_title}</div>
                    <div className="text-xs text-zinc-500">{r.artist_name} • {r.release_date}</div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={r.status} />
                  <Link to={`/label/releases/${r.id}`} className="text-xs font-semibold text-zinc-200 hover:rm-gradient-text">Detail →</Link>
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
    emerald: "from-emerald-500/15 to-emerald-500/5 text-emerald-300",
    amber: "from-amber-500/15 to-amber-500/5 text-amber-300",
    blue: "from-sky-500/15 to-sky-500/5 text-sky-300",
    rose: "from-rose-500/15 to-rose-500/5 text-rose-300",
  };
  const cl = colors[accent] || "from-slate-50 to-slate-100 text-zinc-400";
  return (
    <div className={`rm-card ${mini ? "p-4" : "p-5"}`} data-testid={testId}>
      <div className="flex items-center justify-between">
        <div className="text-[11px] uppercase tracking-widest font-bold text-zinc-500">{label}</div>
        {Icon && (
          <div className={`w-8 h-8 rounded-xl bg-gradient-to-br ${cl} grid place-items-center`}>
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>
      <div className={`font-display font-extrabold tracking-tighter ${mini ? "text-2xl" : "text-2xl md:text-3xl"} mt-2`}>{value}</div>
      {sub && <div className="text-xs text-zinc-500 mt-1">{sub}</div>}
    </div>
  );
}

function StatusPill({ icon: Icon, label, active, warn }) {
  let cls = "bg-white/[0.06] text-zinc-400";
  if (active) cls = "bg-emerald-500/15 text-emerald-300";
  if (warn) cls = "bg-amber-500/100/15 text-amber-300";
  return (
    <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold ${cls}`}>
      <Icon className="w-3.5 h-3.5" />
      {label}
    </div>
  );
}
