import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fileUrl } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { LABEL_DASHBOARD } from "@/constants/testIds";
import StatusBadge from "@/components/shared/StatusBadge";
import { LabelAnalyticsOverview } from "@/components/label/LabelAnalyticsOverview";
import { LabelHero } from "@/components/label/LabelHero";
import { LiveTodayBanner } from "@/components/label/LiveTodayBanner";
import { LabelAddonOrders } from "@/components/label/LabelAddonOrders";
import { useLabelAnalytics } from "@/hooks/useLabelAnalytics";
import { useRoyaltyBalance } from "@/hooks/useRoyaltyBalance";
import { Disc3, Users, Wallet, AlertCircle, Receipt, Crown, ShieldCheck, Play, Lock, ArrowRight, Sparkles, CheckCircle2, Circle, PartyPopper, TrendingUp, UploadCloud, BarChart3, Ticket, FileSignature, CheckCircle, Layers, ChevronDown } from "lucide-react";
import { SubmissionQuota } from "@/components/label/SubmissionQuota";
import { motion, AnimatePresence } from "framer-motion";
import { AreaChart, Area, XAxis, Tooltip, ResponsiveContainer } from "recharts";

function fmtIDR(n) {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
}
function fmtNum(n) {
  return new Intl.NumberFormat("id-ID").format(n || 0);
}

export default function LabelDashboardHome() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [releases, setReleases] = useState([]);
  const [kyc, setKyc] = useState(null);
  const [hero, setHero] = useState(null);
  const [withdraws, setWithdraws] = useState([]);
  const [account, setAccount] = useState(null);
  const [claimDismissed, setClaimDismissed] = useState(false);
  const analytics = useLabelAnalytics();
  const { balance: liveBalance } = useRoyaltyBalance(Boolean(kyc?.is_verified));

  useEffect(() => {
    api.get("/label/dashboard").then((r) => setData(r.data)).catch(() => {});
    api.get("/releases/").then((r) => setReleases(r.data.slice(0, 5))).catch(() => {});
    api.get("/label/kyc").then((r) => setKyc(r.data)).catch(() => setKyc({ is_verified: true, checks: [] }));
    api.get("/cms/landing").then((r) => setHero(r.data?.label_dashboard_hero || {})).catch(() => setHero({}));
    api.get("/withdraw/label").then((r) => setWithdraws(Array.isArray(r.data) ? r.data : [])).catch(() => {});
    api.get("/label/account").then((r) => setAccount(r.data)).catch(() => {});
  }, []);

  const switchLabel = async (id) => {
    if (!id || id === account?.active_label_id) return;
    try { await api.post("/label/active-label", { label_id: id }); window.location.reload(); }
    catch (_) { /* silent */ }
  };

  const withdrawBatch = async () => {
    try {
      await api.post("/withdraw/label/batch");
      alert("Pencairan gabungan diajukan untuk seluruh label.");
      window.location.reload();
    } catch (e) {
      alert(e?.response?.data?.detail || "Pencairan gabungan gagal.");
    }
  };

  // Persist claim-banner dismissal per label so it never reappears after closing.
  useEffect(() => {
    if (data?.label?.id && localStorage.getItem(`rm:claim_dismissed:${data.label.id}`)) setClaimDismissed(true);
  }, [data?.label?.id]);
  const dismissClaim = () => { if (data?.label?.id) localStorage.setItem(`rm:claim_dismissed:${data.label.id}`, "1"); setClaimDismissed(true); };

  const [trend, setTrend] = useState(null);
  const [celebrate, setCelebrate] = useState(false);
  useEffect(() => {
    if (!kyc?.is_verified) return;
    const params = { window: "6" };
    if (analytics.labelId && analytics.labelId !== "all") params.label_id = analytics.labelId;
    api.get("/label/analytics", { params }).then((r) => setTrend(r.data.monthly || [])).catch(() => setTrend([]));
    const key = `rm:verified_seen:${data?.label?.id || "x"}`;
    if (!localStorage.getItem(key)) setCelebrate(true);
  }, [kyc?.is_verified, data?.label?.id, analytics.labelId]);
  const dismissCelebrate = () => { localStorage.setItem(`rm:verified_seen:${data?.label?.id || "x"}`, "1"); setCelebrate(false); };

  if (!data) return <DashboardSkeleton />;
  const { label } = data;
  const pipeline = data.pipeline || { draft: 0, review: 0, delivered: 0, live: 0 };
  const stats = { ...data.stats, ...(liveBalance || {}) };
  const totalUnwithdrawn = stats.balance_available_idr + stats.balance_pending_idr + stats.balance_withdraw_requested_idr;
  const locked = kyc ? !kyc.is_verified : false;
  const checks = kyc?.checks || [];
  const stepsDone = checks.filter((c) => c.complete).length;
  const stepsTotal = checks.length || 1;
  const showOnboarding = (stats.active_releases || 0) === 0 && releases.length === 0;
  const lastWithdraw = withdraws[0] || null;

  const identitySub = [
    "Label Musik • Indonesia",
    stats.payment_type === "annual_subscription" ? "Annual" : "Pay Per Release",
  ].filter(Boolean).join(" • ");

  // Derive "Yang Perlu Diperhatikan" from existing data only.
  const attention = [];
  if (pipeline.draft > 0) attention.push({ tone: "info", icon: UploadCloud, text: `${pipeline.draft} rilisan draft belum diajukan`, to: "/label/releases", cta: "Lengkapi" });
  if ((stats.pending_invoices || 0) > 0) attention.push({ tone: "warn", icon: Receipt, text: `${stats.pending_invoices} tagihan menunggu pembayaran`, to: "/label/invoices", cta: "Bayar" });
  if (!stats.bank_verified) attention.push({ tone: "warn", icon: AlertCircle, text: "Rekening bank belum diverifikasi", to: "/label/profile", cta: "Verifikasi" });
  if (stats.contract_status && stats.contract_status !== "contract_active") attention.push({ tone: "warn", icon: FileSignature, text: "Kontrak belum aktif", to: "/label/contract", cta: "Lihat" });
  if ((stats.active_tickets || 0) > 0) attention.push({ tone: "info", icon: Ticket, text: `${stats.active_tickets} tiket bantuan aktif`, to: "/label/support", cta: "Buka" });

  return (
    <div className="mx-auto max-w-6xl space-y-6 md:space-y-7">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Dasbor Label</div>
          <h1 className="font-display text-2xl font-extrabold tracking-tight md:text-3xl" data-testid="label-dashboard-name" translate="no">Halo, {label.label_name}</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/label/releases/upload" data-testid={LABEL_DASHBOARD.uploadReleaseButton} className="rm-btn-primary">+ Ajukan Rilisan</Link>
          <Link to="/label/withdraw" data-testid={LABEL_DASHBOARD.withdrawButton} className="rm-btn-ghost">Tarik Dana</Link>
        </div>
      </div>

      {/* Multi Label account bar (switcher + aggregated balance) */}
      {account?.is_multi_label && <MultiLabelBar account={account} onSwitch={switchLabel} onWithdraw={withdrawBatch} analyticsLabel={analytics.labelId} onAnalyticsLabel={analytics.setLabelId} locked={locked} />}

      {/* Hero (CMS-managed) */}
      <LabelHero hero={hero} label={label} verified={kyc?.is_verified} subline={identitySub} />

      <LiveTodayBanner releases={data.live_today || []} />

      {!locked && <SubmissionQuota prefix="label-dashboard" />}

      {/* Status row */}
      <div className="flex flex-wrap gap-2">
        <StatusPill icon={Crown} label={`Subscription: ${stats.subscription_status === "active" ? "Aktif" : "Tidak Aktif"}`} active={stats.subscription_status === "active"} />
        <StatusPill icon={ShieldCheck} label={`Kontrak: ${stats.contract_status === "contract_active" ? "Aktif" : stats.contract_status?.replace("_", " ") || "—"}`} active={stats.contract_status === "contract_active"} />
        <StatusPill icon={Receipt} label={`Tipe: ${stats.payment_type === "annual_subscription" ? "Annual" : "Pay Per Release"}`} active />
        {!stats.bank_verified && <StatusPill icon={AlertCircle} label="Rekening belum diverifikasi" warn />}
      </div>

      {/* Aktivitas & Tindakan */}
      <AnimatePresence>
        {celebrate && (
          <motion.div
            initial={{ opacity: 0, scale: 0.92, y: -8 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }}
            transition={{ type: "spring", stiffness: 260, damping: 20 }}
            className="relative overflow-hidden rounded-xl border border-emerald-400/40 bg-gradient-to-r from-emerald-500/[0.12] to-[#FF1F8E]/[0.1] p-5"
            data-testid="label-dashboard-verified-celebrate"
          >
            <div className="flex items-start gap-3">
              <motion.div animate={{ rotate: [0, -12, 12, -8, 0] }} transition={{ duration: 0.9, repeat: 2 }} className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-emerald-400/20 text-emerald-300"><PartyPopper className="h-6 w-6" /></motion.div>
              <div className="flex-1">
                <h2 className="font-display text-lg font-extrabold tracking-tight text-emerald-100">Selamat! Akun Anda Terverifikasi 🎉</h2>
                <p className="mt-0.5 text-sm text-emerald-200/80">Saldo dan jumlah royalti Anda kini terbuka penuh. Selamat berkarya bersama RILIS MUSIK!</p>
              </div>
              <button onClick={dismissCelebrate} title="Tutup" className="absolute right-3 top-3 text-emerald-200/70 hover:text-white" data-testid="label-dashboard-celebrate-close"><span className="text-lg leading-none">×</span></button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {locked && (
        <div className="rounded-xl border border-amber-400/40 bg-amber-400/[0.08] p-5" data-testid="label-dashboard-verify-warning">
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

      {!claimDismissed && <ClaimBanner claimStatus={user?.claim_status} rejectReason={user?.claim_reject_reason} onDismiss={dismissClaim} />}

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

      {/* KPI primary — mobile 2x2 */}
      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <StatCard testId={LABEL_DASHBOARD.balanceAvailable} label="Saldo Siap Ditarik" value={fmtIDR(stats.balance_available_idr)} icon={Wallet} accent="emerald" locked={locked} />
        <StatCard testId="label-dashboard-latest-revenue" label="Pendapatan Terbaru" value={fmtIDR(analytics.data?.latest_report?.revenue_idr)} sub={analytics.data?.latest_period} icon={Disc3} accent="emerald" locked={locked} />
        <StatCard testId="label-dashboard-latest-streams" label="Stream Terbaru" value={fmtNum(analytics.data?.latest_report?.streams)} sub={analytics.data?.latest_period} icon={Play} accent="blue" />
        <StatCard testId={LABEL_DASHBOARD.totalReleases} label="Rilisan Aktif" value={`${fmtNum(stats.active_releases)}`} sub={`${fmtNum(stats.total_tracks)} track`} icon={Disc3} accent="violet" />
      </div>

      {/* Wallet & Penarikan */}
      <WalletCard stats={stats} totalUnwithdrawn={totalUnwithdrawn} lastWithdraw={lastWithdraw} locked={locked} />

      {/* Quick Actions */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4" data-testid="label-dashboard-quick-actions">
        <QuickAction to="/label/releases/upload" icon={UploadCloud} label="Ajukan Rilisan" />
        <QuickAction to="/label/royalty" icon={BarChart3} label="Lihat Royalti" />
        <QuickAction to="/label/withdraw" icon={Wallet} label="Tarik Dana" />
        <QuickAction to="/label/artists" icon={Users} label="Kelola Artis" />
      </div>

      {/* Performa Royalti — trend */}
      {!locked && trend && trend.length > 0 && (
        <section className="rm-card p-5" data-testid="label-dashboard-trend">
          <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-zinc-500"><TrendingUp className="h-4 w-4" /> Tren Stream 6 Bulan Terakhir</div>
          <div className="h-40 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trend} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="streamGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#FF1F8E" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="#FF1F8E" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="period" tickFormatter={(p) => (p || "").slice(5)} tick={{ fill: "#71717a", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: "#101010", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, fontSize: 12 }}
                  labelStyle={{ color: "#a1a1aa" }} formatter={(v) => [Number(v).toLocaleString("id-ID"), "Stream"]}
                />
                <Area type="monotone" dataKey="streams" stroke="#FF1F8E" strokeWidth={2} fill="url(#streamGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 text-[11px] text-zinc-500">Berdasarkan laporan royalti aktif (tidak termasuk riwayat legacy yang sudah cut-off).</p>
        </section>
      )}

      {/* Insight Utama */}
      <LabelAnalyticsOverview analytics={analytics} />

      {/* Operations grid: Attention + Pipeline */}
      <div className="grid gap-5 lg:grid-cols-2">
        <section className="rm-card p-5" data-testid="label-dashboard-attention">
          <h3 className="mb-4 font-display text-lg font-bold tracking-tight">Yang Perlu Diperhatikan</h3>
          {attention.length === 0 ? (
            <div className="flex items-center gap-3 rounded-lg border border-emerald-400/20 bg-emerald-400/[0.05] px-4 py-5 text-sm text-emerald-200" data-testid="label-dashboard-attention-empty">
              <CheckCircle className="h-5 w-5 shrink-0 text-emerald-400" /> Semua aman. Tidak ada yang perlu ditindak saat ini.
            </div>
          ) : (
            <div className="space-y-2">
              {attention.map((item, i) => (
                <div key={i} className={`flex items-center justify-between gap-3 rounded-lg border px-3 py-2.5 ${item.tone === "warn" ? "border-amber-400/25 bg-amber-400/[0.06]" : "border-white/10 bg-white/[0.02]"}`} data-testid={`label-dashboard-attention-item-${i}`}>
                  <div className="flex min-w-0 items-center gap-2.5">
                    <item.icon className={`h-4 w-4 shrink-0 ${item.tone === "warn" ? "text-amber-300" : "text-sky-300"}`} />
                    <span className="truncate text-sm text-zinc-200">{item.text}</span>
                  </div>
                  <Link to={item.to} className="shrink-0 text-xs font-semibold rm-gradient-text">{item.cta} →</Link>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="rm-card p-5" data-testid="label-dashboard-pipeline">
          <h3 className="mb-4 font-display text-lg font-bold tracking-tight">Pipeline Rilisan</h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <PipelineStep label="Draft" value={pipeline.draft} tone="zinc" />
            <PipelineStep label="Review" value={pipeline.review} tone="amber" />
            <PipelineStep label="Dikirim" value={pipeline.delivered} tone="blue" />
            <PipelineStep label="Tayang" value={pipeline.live} tone="emerald" />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <MiniStat label="Total Artist" value={fmtNum(stats.total_artists)} icon={Users} testId={LABEL_DASHBOARD.totalArtists} />
            <MiniStat label="Tiket Aktif" value={fmtNum(stats.active_tickets)} icon={AlertCircle} />
          </div>
        </section>
      </div>

      {/* Recent releases */}
      <LabelAddonOrders title="Layanan Tambahan" showRelease hideWhenEmpty />

      <div className="rm-card p-5">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-display text-lg font-bold tracking-tight">Rilisan Terbaru</h3>
          <Link to="/label/releases" className="text-sm font-semibold rm-gradient-text">Lihat semua →</Link>
        </div>
        {releases.length === 0 ? (
          <div className="py-8 text-center text-sm text-zinc-500">
            Belum ada rilisan. <Link to="/label/releases/upload" className="font-semibold rm-gradient-text">Ajukan sekarang</Link>
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            {releases.map((r) => (
              <div key={r.id} className="flex items-center justify-between gap-3 py-3">
                <div className="flex min-w-0 items-center gap-3">
                  <ReleaseCover url={r.display_cover_url || r.cover_url} />
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold">{r.release_title}</div>
                    <div className="truncate text-xs text-zinc-500">{(r.display_primary_artists?.[0]) || r.artist_name} • {r.release_date}</div>
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

function MultiLabelBar({ account, onSwitch, onWithdraw, analyticsLabel, onAnalyticsLabel, locked }) {
  const exp = account?.entitlements?.subscription_expires_at;
  const expText = exp ? new Date(exp).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "—";
  return (
    <section className="rounded-2xl border border-[#A24EFF]/35 bg-gradient-to-r from-[#A24EFF]/[0.12] to-[#4E7CFF]/[0.08] p-5" data-testid="label-multi-label-bar">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="inline-flex items-center gap-2 text-[11px] font-bold uppercase tracking-widest text-[#C79BFF]"><Layers className="h-4 w-4" /> Multi Label</div>
          <div className="mt-1 text-sm text-zinc-300" data-testid="label-multi-label-summary">{account.label_count} label dikelola • Aktif sampai {expText}</div>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <div>
            <div className="text-[11px] font-bold uppercase tracking-widest text-zinc-500">Total Saldo Tersedia</div>
            {locked ? (
              <div className="mt-0.5 flex items-center gap-2"><span className="select-none font-display text-2xl font-extrabold tabular-nums blur-[6px]">{fmtIDR(account.account_available_idr)}</span><Lock className="h-4 w-4 text-zinc-500" /></div>
            ) : (
              <div className="mt-0.5 font-display text-2xl font-extrabold tabular-nums rm-gradient-text" data-testid="label-account-available">{fmtIDR(account.account_available_idr)}</div>
            )}
            {!locked && account.account_available_idr > 0 && (
              <button type="button" onClick={onWithdraw} className="rm-btn-primary mt-2 inline-flex items-center gap-2 text-xs" data-testid="label-batch-withdraw-cta"><Wallet className="h-3.5 w-3.5" /> Cairkan Saldo Gabungan</button>
            )}
          </div>
          <label className="min-w-[180px]">
            <span className="mb-1 block text-[11px] font-bold uppercase tracking-widest text-zinc-500">Label Aktif</span>
            <div className="relative">
              <select
                className="rm-input w-full appearance-none pr-9"
                value={account.active_label_id || ""}
                onChange={(e) => onSwitch(e.target.value)}
                data-testid="label-active-switcher"
              >
                {account.labels.map((l) => <option key={l.id} value={l.id}>{l.label_name}</option>)}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
            </div>
          </label>
          <label className="min-w-[200px]">
            <span className="mb-1 block text-[11px] font-bold uppercase tracking-widest text-zinc-500">Filter Analitik</span>
            <div className="relative">
              <select
                className="rm-input w-full appearance-none pr-9"
                value={analyticsLabel || "all"}
                onChange={(e) => onAnalyticsLabel(e.target.value)}
                data-testid="label-analytics-filter"
              >
                <option value="all">Semua Label</option>
                {account.labels.map((l) => <option key={l.id} value={l.id}>{l.label_name}</option>)}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
            </div>
          </label>
        </div>
      </div>
    </section>
  );
}

const WITHDRAW_STATUS = {
  requested: { label: "Diminta", cls: "bg-amber-500/15 text-amber-300", dateKey: "request_date" },
  approved: { label: "Disetujui", cls: "bg-sky-500/15 text-sky-300", dateKey: "approved_date" },
  paid: { label: "Dibayar", cls: "bg-emerald-500/15 text-emerald-300", dateKey: "paid_date" },
  rejected: { label: "Ditolak", cls: "bg-red-500/15 text-red-300", dateKey: "request_date" },
  cancelled: { label: "Dibatalkan", cls: "bg-zinc-500/15 text-zinc-300", dateKey: "request_date" },
};
function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return isNaN(d) ? "—" : d.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
}

function WalletCard({ stats, totalUnwithdrawn, lastWithdraw, locked }) {
  const meta = lastWithdraw ? (WITHDRAW_STATUS[lastWithdraw.status] || WITHDRAW_STATUS.requested) : null;
  const lastDate = lastWithdraw ? (lastWithdraw[meta.dateKey] || lastWithdraw.request_date || lastWithdraw.created_at) : null;
  return (
    <section className="rm-card p-5" data-testid="label-dashboard-wallet">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-[11px] font-bold uppercase tracking-widest text-zinc-500">Saldo Siap Ditarik</div>
          {locked ? (
            <div className="mt-1 flex items-center gap-2"><span className="select-none font-display text-2xl font-extrabold tabular-nums blur-[6px] md:text-3xl">{fmtIDR(stats.balance_available_idr)}</span><Lock className="h-5 w-5 text-zinc-500" /></div>
          ) : (
            <div className="mt-1 font-display text-2xl font-extrabold tabular-nums md:text-3xl" data-testid="label-wallet-available">{fmtIDR(stats.balance_available_idr)}</div>
          )}
        </div>
        <Link to="/label/withdraw" className="rm-btn-primary inline-flex items-center gap-2" data-testid="label-wallet-withdraw-cta"><Wallet className="h-4 w-4" /> Tarik Dana</Link>
      </div>

      <div className="mt-5 grid gap-4 border-t border-white/5 pt-4 sm:grid-cols-3">
        <div data-testid={LABEL_DASHBOARD.balancePending}>
          <div className="text-[11px] font-bold uppercase tracking-widest text-zinc-500">Pending</div>
          <div className={`mt-1 font-display text-lg font-extrabold tabular-nums ${locked ? "select-none blur-[5px]" : ""}`}>{fmtIDR(stats.balance_pending_idr)}</div>
          <div className="text-[11px] text-zinc-500">Menunggu pembayaran platform</div>
        </div>
        <div data-testid="label-dashboard-withdraw-processing">
          <div className="text-[11px] font-bold uppercase tracking-widest text-zinc-500">Withdraw Diproses</div>
          <div className={`mt-1 font-display text-lg font-extrabold tabular-nums ${locked ? "select-none blur-[5px]" : ""}`}>{fmtIDR(stats.balance_withdraw_requested_idr)}</div>
          <div className="text-[11px] text-zinc-500">Sedang dalam proses pencairan</div>
        </div>
        <div data-testid="label-dashboard-last-withdraw">
          <div className="text-[11px] font-bold uppercase tracking-widest text-zinc-500">Terakhir Ditarik</div>
          {lastWithdraw ? (
            <>
              <div className="mt-1 flex items-center gap-2">
                <span className="font-display text-lg font-extrabold tabular-nums" data-testid="label-last-withdraw-amount">{fmtIDR(lastWithdraw.amount_idr)}</span>
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${meta.cls}`} data-testid="label-last-withdraw-status">{meta.label}</span>
              </div>
              <div className="text-[11px] text-zinc-500" data-testid="label-last-withdraw-date">{fmtDate(lastDate)}</div>
            </>
          ) : (
            <div className="mt-1 text-sm text-zinc-500" data-testid="label-last-withdraw-empty">Belum ada penarikan</div>
          )}
        </div>
      </div>
      <div className="mt-3 text-[11px] text-zinc-500">Total belum ditarik: <span className={locked ? "select-none blur-[4px]" : "font-semibold text-zinc-300"} data-testid="label-dashboard-unwithdrawn-total">{fmtIDR(totalUnwithdrawn)}</span></div>
    </section>
  );
}

function ReleaseCover({ url }) {  const [failed, setFailed] = useState(false);
  if (url && !failed) {
    return <img src={fileUrl(url)} alt="" loading="lazy" className="h-11 w-11 shrink-0 rounded-lg object-cover" onError={() => setFailed(true)} />;
  }
  return <div className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-[#FF1F8E] to-[#A24EFF] text-white"><Disc3 className="h-5 w-5" /></div>;
}

function QuickAction({ to, icon: Icon, label }) {
  return (
    <Link to={to} className="group flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.02] p-4 transition-colors hover:border-[#FF1F8E]/40 hover:bg-white/[0.04]" data-testid={`label-quick-action-${to.split("/").pop()}`}>
      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-[#FF1F8E]/15 to-[#A24EFF]/10 text-[#FF7FC0]"><Icon className="h-5 w-5" /></div>
      <span className="min-w-0 truncate text-sm font-semibold text-zinc-200">{label}</span>
    </Link>
  );
}

function PipelineStep({ label, value, tone }) {
  const tones = {
    zinc: "text-zinc-300", amber: "text-amber-300", blue: "text-sky-300", emerald: "text-emerald-300",
  };
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.02] p-4 text-center" data-testid={`label-pipeline-${label.toLowerCase()}`}>
      <div className={`font-display text-2xl font-extrabold tabular-nums ${tones[tone]}`}>{value}</div>
      <div className="mt-1 text-[11px] font-bold uppercase tracking-widest text-zinc-500">{label}</div>
    </div>
  );
}

function MiniStat({ label, value, icon: Icon, testId }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.02] px-3 py-3" data-testid={testId}>
      <div>
        <div className="text-[11px] font-bold uppercase tracking-widest text-zinc-500">{label}</div>
        <div className="mt-0.5 font-display text-xl font-extrabold tabular-nums">{value}</div>
      </div>
      <Icon className="h-4 w-4 text-zinc-500" />
    </div>
  );
}

function StatCard({ label, value, sub, icon: Icon, accent, mini, testId, locked }) {
  const colors = {
    emerald: "from-emerald-500/15 to-emerald-500/5 text-emerald-300",
    amber: "from-amber-500/15 to-amber-500/5 text-amber-300",
    blue: "from-sky-500/15 to-sky-500/5 text-sky-300",
    rose: "from-rose-500/15 to-rose-500/5 text-rose-300",
    violet: "from-[#A24EFF]/15 to-[#A24EFF]/5 text-[#C79BFF]",
  };
  const cl = colors[accent] || "from-slate-50 to-slate-100 text-zinc-400";
  return (
    <div className={`rm-card min-w-0 ${mini ? "p-4" : "p-4 sm:p-5"}`} data-testid={testId}>
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0 truncate text-[10px] font-bold uppercase tracking-widest text-zinc-500 sm:text-[11px]">{label}</div>
        <div className={`grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-gradient-to-br ${locked ? "from-zinc-500/15 to-zinc-500/5 text-zinc-500" : cl}`}>
          {locked ? <Lock className="h-4 w-4" /> : (Icon && <Icon className="h-4 w-4" />)}
        </div>
      </div>
      {locked ? (
        <div className="mt-2 flex items-center gap-2" data-testid={testId ? `${testId}-locked` : undefined}>
          <span className={`select-none font-display font-extrabold leading-tight tabular-nums blur-[6px] ${mini ? "text-xl" : "text-lg sm:text-xl md:text-2xl"}`}>{value}</span>
          <Lock className="h-4 w-4 shrink-0 text-zinc-500" />
        </div>
      ) : (
        <div className={`mt-2 break-words font-display font-extrabold leading-tight tabular-nums ${mini ? "text-xl" : "text-lg sm:text-xl md:text-2xl"}`}>{value}</div>
      )}
      {sub && !locked && <div className="mt-1 truncate text-xs text-zinc-500">{sub}</div>}
    </div>
  );
}

function ClaimBanner({ claimStatus, rejectReason, onDismiss }) {
  if (claimStatus === "linked") return null;
  if (claimStatus === "pending_link") {
    return (
      <div className="flex items-start gap-3 rounded-xl border border-sky-400/30 bg-sky-400/[0.08] p-4" data-testid="label-dashboard-claim-pending">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-sky-400/15 text-sky-300"><ShieldCheck className="h-5 w-5" /></div>
        <div className="flex-1 text-sm"><div className="font-display font-bold text-sky-100">Permintaan klaim label sedang ditinjau</div><p className="mt-0.5 text-sky-200/80">Admin sedang memproses klaim label lama Anda. Royalti periode sebelumnya akan muncul setelah disetujui.</p></div>
      </div>
    );
  }
  const rejected = claimStatus === "rejected";
  return (
    <div className="relative rounded-xl border border-[#FF1F8E]/30 bg-gradient-to-r from-[#FF1F8E]/[0.1] to-[#A24EFF]/[0.08] p-5" data-testid="label-dashboard-claim-banner">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-[#FF1F8E]/15 text-[#FF7FC0]"><Sparkles className="h-5 w-5" /></div>
          <div>
            <h2 className="font-display text-lg font-bold text-white">{rejected ? "Klaim label belum disetujui" : "Punya label lama di RILIS MUSIK?"}</h2>
            <p className="mt-0.5 text-sm text-zinc-300">{rejected ? `Ajukan klaim kembali untuk melihat royalti periode sebelumnya${rejectReason ? ` (alasan sebelumnya: ${rejectReason})` : ""}.` : "Klaim label Anda untuk menautkan riwayat royalti & penarikan periode sebelumnya. Royalti bulan berjalan biasanya baru masuk bulan berikutnya."}</p>
          </div>
        </div>
        <Link to="/label/profile" className="rm-btn-primary inline-flex shrink-0 items-center justify-center gap-2" data-testid="label-dashboard-claim-cta">Klaim Label <ArrowRight className="h-4 w-4" /></Link>
      </div>
      <button onClick={onDismiss} className="absolute right-3 top-3 text-zinc-500 hover:text-white" title="Tutup" data-testid="label-dashboard-claim-dismiss"><span className="text-lg leading-none">×</span></button>
    </div>
  );
}

function OnboardStep({ n, title, done, to, cta, locked }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-white/10 bg-white/[0.02] p-3" data-testid={`label-onboard-step-${n}`}>
      {done ? <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" /> : locked ? <Lock className="h-5 w-5 shrink-0 text-zinc-600" /> : <Circle className="h-5 w-5 shrink-0 text-[#FF1F8E]" />}
      <span className={`flex-1 text-sm font-semibold ${done ? "text-zinc-400 line-through" : locked ? "text-zinc-500" : "text-white"}`}>{title}</span>
      {!done && !locked && <Link to={to} className="rm-btn-ghost shrink-0 py-1.5 text-xs" data-testid={`label-onboard-cta-${n}`}>{cta}</Link>}
    </div>
  );
}

function StatusPill({ icon: Icon, label, active, warn }) {
  let cls = "bg-white/[0.06] text-zinc-400";
  if (active) cls = "bg-emerald-500/15 text-emerald-300";
  if (warn) cls = "bg-amber-500/15 text-amber-300";
  return (
    <div className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold ${cls}`}>
      <Icon className="h-3.5 w-3.5" />
      {label}
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="mx-auto max-w-6xl space-y-6" data-testid="label-dashboard-loading">
      <div className="h-10 w-64 animate-pulse rounded-lg bg-zinc-800" />
      <div className="h-64 w-full animate-pulse rounded-2xl bg-zinc-800" />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">{[0, 1, 2, 3].map((i) => <div key={i} className="h-28 animate-pulse rounded-xl bg-zinc-800" />)}</div>
      <div className="h-72 w-full animate-pulse rounded-xl bg-zinc-800" />
    </div>
  );
}
