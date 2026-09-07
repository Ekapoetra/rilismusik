import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import { LABEL_DASHBOARD } from "@/constants/testIds";
import StatusBadge from "@/components/shared/StatusBadge";
import { LabelAnalyticsOverview } from "@/components/label/LabelAnalyticsOverview";
import { useLabelAnalytics } from "@/hooks/useLabelAnalytics";
import { Disc3, Users, Wallet, AlertCircle, Receipt, Crown, ShieldCheck, Play, Lock, ArrowRight, Sparkles, CheckCircle2, Circle } from "lucide-react";
import { LabelLogo } from "@/components/shared/LabelLogo";

function fmtIDR(n) {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
}

export default function LabelDashboardHome() {
  const [data, setData] = useState(null);
  const [releases, setReleases] = useState([]);
  const [kyc, setKyc] = useState(null);
  const analytics = useLabelAnalytics();

  useEffect(() => {
    api.get("/label/dashboard").then((r) => setData(r.data)).catch(() => {});
    api.get("/releases/").then((r) => setReleases(r.data.slice(0, 5))).catch(() => {});
    api.get("/label/kyc").then((r) => setKyc(r.data)).catch(() => setKyc({ is_verified: true, checks: [] }));
  }, []);

  if (!data) return <div className="text-zinc-500">Memuat…</div>;
  const { stats, label } = data;
  const totalUnwithdrawn = stats.balance_available_idr + stats.balance_pending_idr + stats.balance_withdraw_requested_idr;
  const locked = kyc ? !kyc.is_verified : false;
  const checks = kyc?.checks || [];
  const stepsDone = checks.filter((c) => c.complete).length;
  const stepsTotal = checks.length || 1;
  const showOnboarding = (stats.active_releases || 0) === 0 && releases.length === 0;

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-4 min-w-0">
          <LabelLogo src={label.logo_url} labelName={label.label_name} className="h-16 w-16 md:h-20 md:w-20" testId="label-dashboard-logo" />
          <div className="min-w-0">
            <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Dashboard</div>
            <h1 className="font-display text-3xl md:text-4xl font-extrabold tracking-tighter truncate" data-testid="label-dashboard-name">Halo, {label.label_name}</h1>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Link to="/label/releases/upload" data-testid={LABEL_DASHBOARD.uploadReleaseButton} className="rm-btn-primary">+ Submit Rilisan</Link>
          <Link to="/label/withdraw" data-testid={LABEL_DASHBOARD.withdrawButton} className="rm-btn-ghost">Withdraw</Link>
        </div>
      </div>

      {/* Mobile summary card */}
      <div className="md:hidden rm-card p-5" data-testid="label-dashboard-mobile-summary">
        <div className="flex items-center justify-between">
          <div className="text-[11px] uppercase tracking-widest font-bold text-zinc-500">Total Belum Ditarik</div>
          <div className={`grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br ${locked ? "from-zinc-500/15 to-zinc-500/5 text-zinc-500" : "from-emerald-500/15 to-emerald-500/5 text-emerald-300"}`}>{locked ? <Lock className="h-4 w-4" /> : <Wallet className="h-4 w-4" />}</div>
        </div>
        {locked ? (
          <div className="mt-1 flex items-center gap-2"><span className="font-display text-3xl font-extrabold tracking-tight tabular-nums blur-[6px] select-none" data-testid="label-dashboard-mobile-summary-locked">{fmtIDR(totalUnwithdrawn || 1234567)}</span><Lock className="h-5 w-5 text-zinc-500" /></div>
        ) : (
          <div className="mt-1 font-display text-3xl font-extrabold tracking-tight tabular-nums break-words">{fmtIDR(totalUnwithdrawn)}</div>
        )}
      </div>

      {locked && (
        <div className="rounded-lg border border-amber-400/40 bg-amber-400/[0.08] p-5" data-testid="label-dashboard-verify-warning">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-amber-400/15 text-amber-300"><ShieldCheck className="h-5 w-5" /></div>
              <div>
                <h2 className="font-display text-lg font-bold text-amber-100">Verifikasi Akun Diperlukan</h2>
                <p className="mt-0.5 text-sm text-amber-200/80">Selesaikan Verifikasi Akun untuk membuka saldo dan melihat jumlah royalti Anda.</p>
              </div>
            </div>
            <Link to="/label/profile" className="rm-btn-primary inline-flex shrink-0 items-center justify-center gap-2" data-testid="label-dashboard-verify-cta">Verifikasi Sekarang <ArrowRight className="h-4 w-4" /></Link>
          </div>
          <div className="mt-4">
            <div className="mb-1 flex items-center justify-between text-xs font-semibold text-amber-200/90"><span data-testid="label-dashboard-verify-progress-text">{stepsDone} dari {stepsTotal} langkah selesai</span><span>{Math.round((stepsDone / stepsTotal) * 100)}%</span></div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-amber-400/15"><div className="h-full rounded-full bg-gradient-to-r from-amber-400 to-[#FF1F8E] transition-all" style={{ width: `${Math.round((stepsDone / stepsTotal) * 100)}%` }} data-testid="label-dashboard-verify-progress-bar" /></div>
          </div>
        </div>
      )}

      {showOnboarding && (
        <div className="rm-card p-5" data-testid="label-dashboard-onboarding">
          <div className="flex items-center gap-2"><Sparkles className="h-5 w-5 text-[#FF1F8E]" /><h2 className="font-display text-xl font-bold tracking-tight">Selamat datang di RILIS MUSIK!</h2></div>
          <p className="mt-1 text-sm text-zinc-400">Ikuti langkah singkat berikut sampai rilisan pertama Anda tayang.</p>
          <div className="mt-4 space-y-2">
            <OnboardStep n={1} title="Lengkapi profil, logo & rekening" done={!!kyc?.prerequisites_complete} to="/label/profile" cta="Lengkapi" />
            <OnboardStep n={2} title="Selesaikan Verifikasi Akun" done={!!kyc?.is_verified} to="/label/profile" cta="Verifikasi" locked={!kyc?.prerequisites_complete} />
            <OnboardStep n={3} title="Submit rilisan pertama Anda" done={(stats.active_releases || 0) > 0} to="/label/releases/upload" cta="Submit" locked={!kyc?.is_verified} />
          </div>
        </div>
      )}

      {/* Status row */}
      <div className="flex flex-wrap gap-2">
        <StatusPill icon={Crown} label={`Subscription: ${stats.subscription_status === "active" ? "Aktif" : "Tidak Aktif"}`} active={stats.subscription_status === "active"} />
        <StatusPill icon={ShieldCheck} label={`Kontrak: ${stats.contract_status === "contract_active" ? "Aktif" : stats.contract_status?.replace("_", " ") || "—"}`} active={stats.contract_status === "contract_active"} />
        <StatusPill icon={Receipt} label={`Tipe: ${stats.payment_type === "annual_subscription" ? "Annual" : "Pay Per Release"}`} active />
        {!stats.bank_verified && <StatusPill icon={AlertCircle} label="Rekening belum diverifikasi" warn />}
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3 sm:gap-4">
        <StatCard testId={LABEL_DASHBOARD.balanceAvailable} label="Saldo Tersedia" value={fmtIDR(stats.balance_available_idr)} icon={Wallet} accent="emerald" locked={locked} />
        <StatCard testId={LABEL_DASHBOARD.balancePending} label="Saldo Pending" value={fmtIDR(stats.balance_pending_idr)} icon={Receipt} accent="amber" locked={locked} />
        <StatCard testId="label-dashboard-withdraw-processing" label="Withdraw Diproses" value={fmtIDR(stats.balance_withdraw_requested_idr)} icon={Receipt} accent="blue" locked={locked} />
        <StatCard testId="label-dashboard-unwithdrawn-total" label="Belum Ditarik" value={fmtIDR(totalUnwithdrawn)} icon={Wallet} accent="rose" locked={locked} />
        <StatCard testId="label-dashboard-latest-streams" label="Stream Terbaru" value={(analytics.data?.latest_report?.streams || 0).toLocaleString("id-ID")} sub={analytics.data?.latest_period} icon={Play} accent="blue" />
        <StatCard testId="label-dashboard-latest-revenue" label="Pendapatan Terbaru" value={fmtIDR(analytics.data?.latest_report?.revenue_idr)} sub={analytics.data?.latest_period} icon={Disc3} accent="emerald" locked={locked} />
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

function StatCard({ label, value, sub, icon: Icon, accent, mini, testId, locked }) {
  const colors = {
    emerald: "from-emerald-500/15 to-emerald-500/5 text-emerald-300",
    amber: "from-amber-500/15 to-amber-500/5 text-amber-300",
    blue: "from-sky-500/15 to-sky-500/5 text-sky-300",
    rose: "from-rose-500/15 to-rose-500/5 text-rose-300",
  };
  const cl = colors[accent] || "from-slate-50 to-slate-100 text-zinc-400";
  return (
    <div className={`rm-card min-w-0 ${mini ? "p-4" : "p-4 sm:p-5"}`} data-testid={testId}>
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0 truncate text-[10px] sm:text-[11px] uppercase tracking-widest font-bold text-zinc-500">{label}</div>
        <div className={`w-8 h-8 shrink-0 rounded-xl bg-gradient-to-br ${locked ? "from-zinc-500/15 to-zinc-500/5 text-zinc-500" : cl} grid place-items-center`}>
          {locked ? <Lock className="w-4 h-4" /> : (Icon && <Icon className="w-4 h-4" />)}
        </div>
      </div>
      {locked ? (
        <div className="mt-2 flex items-center gap-2" data-testid={testId ? `${testId}-locked` : undefined}>
          <span className={`font-display font-extrabold tracking-tight leading-tight tabular-nums blur-[6px] select-none ${mini ? "text-2xl" : "text-lg sm:text-xl md:text-2xl"}`}>{value}</span>
          <Lock className="h-4 w-4 shrink-0 text-zinc-500" />
        </div>
      ) : (
        <div className={`font-display font-extrabold tracking-tight leading-tight tabular-nums break-words mt-2 ${mini ? "text-2xl" : "text-lg sm:text-xl md:text-2xl"}`}>{value}</div>
      )}
      {sub && !locked && <div className="text-xs text-zinc-500 mt-1 truncate">{sub}</div>}
    </div>
  );
}

function OnboardStep({ n, title, done, to, cta, locked }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-white/10 bg-white/[0.02] p-3" data-testid={`label-onboard-step-${n}`}>
      {done ? <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" /> : locked ? <Lock className="h-5 w-5 shrink-0 text-zinc-600" /> : <Circle className="h-5 w-5 shrink-0 text-[#FF1F8E]" />}
      <span className={`flex-1 text-sm font-semibold ${done ? "text-zinc-400 line-through" : locked ? "text-zinc-500" : "text-white"}`}>{title}</span>
      {!done && !locked && <Link to={to} className="rm-btn-ghost shrink-0 text-xs py-1.5" data-testid={`label-onboard-cta-${n}`}>{cta}</Link>}
    </div>
  );
}

function StatusPill({ icon: Icon, label, active, warn }) {
  let cls = "bg-white/[0.06] text-zinc-400";
  if (active) cls = "bg-emerald-500/15 text-emerald-300";
  if (warn) cls = "bg-amber-500/15 text-amber-300";
  return (
    <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold ${cls}`}>
      <Icon className="w-3.5 h-3.5" />
      {label}
    </div>
  );
}
