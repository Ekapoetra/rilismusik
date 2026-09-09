import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import { ADMIN_DASHBOARD } from "@/constants/testIds";
import { useAuth } from "@/api/AuthContext";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import {
  Building2, Users2, Disc3, FileSpreadsheet, CreditCard, Banknote, MessageSquare, Crown, ShieldOff,
  Activity, BarChart3, ArrowRight, ShieldCheck, DatabaseZap, CheckCircle2, AlertTriangle, RefreshCw,
  Sparkles, UserPlus, Upload, Clock,
} from "lucide-react";

const ICONS = { Banknote, CreditCard, Disc3, ShieldCheck, MessageSquare, DatabaseZap, Activity };
const PRIORITY = {
  critical: { label: "Kritis", cls: "border-rose-500/40 bg-rose-500/[0.08]", chip: "bg-rose-500/20 text-rose-200", icon: "text-rose-300" },
  high: { label: "Penting", cls: "border-amber-400/40 bg-amber-400/[0.07]", chip: "bg-amber-400/20 text-amber-200", icon: "text-amber-300" },
  normal: { label: "Rutin", cls: "border-white/10 bg-white/[0.03]", chip: "bg-white/10 text-zinc-300", icon: "text-zinc-300" },
  low: { label: "Info", cls: "border-white/10 bg-white/[0.02]", chip: "bg-white/5 text-zinc-400", icon: "text-zinc-400" },
};

function fmtIDR(n) {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
}
function timeAgo(iso) {
  if (!iso) return "";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "baru saja";
  if (diff < 3600) return `${Math.floor(diff / 60)}m lalu`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}j lalu`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}h lalu`;
  return new Date(iso).toLocaleDateString("id-ID");
}
const humanize = (s) => (s || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
function activityLink(a) {
  const ref = a.reference_id;
  const map = { release: ref ? `/admin/releases/${ref}` : "/admin/releases", label: ref ? `/admin/labels/${ref}` : "/admin/labels", withdraw: "/admin/withdraw", kyc: "/admin/kyc", ticket: "/admin/tickets", payment: "/admin/payments", bank_account: "/admin/labels", admin_user: "/admin/admin-users" };
  return map[a.module] || null;
}

function ActionCenter() {
  const { hasPermission } = useAuth();
  const { t } = useAppPreferences();
  const [state, setState] = useState({ loading: true, error: false, items: [] });
  const load = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: false }));
    try { const { data } = await api.get("/admin/action-center"); setState({ loading: false, error: false, items: data.items || [] }); }
    catch { setState({ loading: false, error: true, items: [] }); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const items = state.items.filter((it) => hasPermission(it.permission));

  return (
    <section data-testid="admin-action-center">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2"><Sparkles className="h-5 w-5 text-[#FF1F8E]" /><h2 className="font-display text-2xl font-extrabold tracking-tighter">Perlu Perhatian Anda</h2></div>
        <button onClick={load} className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white" data-testid="admin-action-center-refresh"><RefreshCw className={`h-3.5 w-3.5 ${state.loading ? "animate-spin" : ""}`} /> Segarkan</button>
      </div>
      {state.loading ? (
        <div className="space-y-3" data-testid="admin-action-center-loading">{[0, 1, 2].map((i) => <div key={i} className="h-20 animate-pulse rounded-lg border border-white/10 bg-white/[0.03]" />)}</div>
      ) : state.error ? (
        <div className="flex items-center justify-between rounded-lg border border-rose-500/30 bg-rose-500/[0.08] p-5" data-testid="admin-action-center-error">
          <div className="flex items-center gap-3 text-sm text-rose-200"><AlertTriangle className="h-5 w-5" /> Gagal memuat daftar tindakan.</div>
          <button onClick={load} className="rm-btn-ghost text-sm" data-testid="admin-action-center-retry">Coba lagi</button>
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-emerald-400/20 bg-emerald-400/[0.05] p-10 text-center" data-testid="admin-action-center-empty">
          <CheckCircle2 className="h-10 w-10 text-emerald-400" />
          <div className="font-display text-lg font-bold">Semua beres!</div>
          <p className="text-sm text-zinc-400">Tidak ada tindakan operasional yang menunggu saat ini.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((it) => {
            const p = PRIORITY[it.priority] || PRIORITY.normal;
            const Icon = ICONS[it.icon] || Activity;
            return (
              <div key={it.key} className={`flex flex-col gap-3 rounded-lg border p-4 sm:flex-row sm:items-center sm:justify-between ${p.cls}`} data-testid={`admin-action-item-${it.key}`}>
                <div className="flex items-start gap-3">
                  <div className={`grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-black/30 ${p.icon}`}><Icon className="h-5 w-5" /></div>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-display text-base font-bold" data-testid={`admin-action-title-${it.key}`}>{t(it.title)}</span>
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${p.chip}`} data-testid={`admin-action-priority-${it.key}`}>{t(p.label)}</span>
                      <span className="rounded-full bg-white/10 px-2 py-0.5 text-[11px] font-bold tabular-nums text-white" data-testid={`admin-action-count-${it.key}`}>{it.count}</span>
                      {it.oldest_at && <span className="inline-flex items-center gap-1 text-[11px] text-zinc-500"><Clock className="h-3 w-3" /> tertua {timeAgo(it.oldest_at)}</span>}
                    </div>
                    <p className="mt-0.5 text-sm text-zinc-400" data-testid={`admin-action-description-${it.key}`}>{t(it.description)}</p>
                  </div>
                </div>
                <Link to={it.link} className="rm-btn-primary inline-flex shrink-0 items-center justify-center gap-2" data-testid={`admin-action-cta-${it.key}`}>{t(it.cta)} <ArrowRight className="h-4 w-4" /></Link>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

function QuickActions() {
  const { hasPermission } = useAuth();
  const actions = [
    { key: "add-label", label: "Tambah Label", to: "/admin/labels", icon: Building2, perm: "labels.view" },
    { key: "add-artist", label: "Tambah Artis", to: "/admin/artists", icon: UserPlus, perm: "artists.view" },
    { key: "import-royalty", label: "Impor Royalti", to: "/admin/royalty", icon: Upload, perm: "royalty.view" },
    { key: "review-withdraw", label: "Penarikan Dana", to: "/admin/withdraw", icon: Banknote, perm: "withdraw.view" },
    { key: "analytics", label: "Analitik", to: "/admin/analytics", icon: BarChart3, perm: "analytics.view" },
  ].filter((a) => hasPermission(a.perm));
  if (!actions.length) return null;
  return (
    <section data-testid="admin-quick-actions">
      <div className="mb-3 text-xs font-bold uppercase tracking-widest text-zinc-500">Aksi Cepat</div>
      <div className="flex flex-wrap gap-2">
        {actions.map((a) => (
          <Link key={a.key} to={a.to} className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-3.5 py-2 text-sm font-semibold text-zinc-200 transition-colors hover:border-white/20 hover:bg-white/[0.07]" data-testid={`admin-quick-action-${a.key}`}>
            <a.icon className="h-4 w-4 text-[#FF1F8E]" /> {a.label}
          </Link>
        ))}
      </div>
    </section>
  );
}

function RecentActivity() {
  const [items, setItems] = useState(null);
  useEffect(() => { api.get("/admin/activity-logs", { params: { limit: 8 } }).then((r) => setItems(r.data || [])).catch(() => setItems([])); }, []);
  return (
    <section className="rm-card p-5" data-testid="admin-recent-activity">
      <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-zinc-500"><Activity className="h-4 w-4" /> Aktivitas Terbaru</div>
      {items === null ? (
        <div className="space-y-2">{[0, 1, 2].map((i) => <div key={i} className="h-8 animate-pulse rounded bg-white/[0.04]" />)}</div>
      ) : items.length === 0 ? (
        <div className="py-6 text-center text-sm text-zinc-600">Belum ada aktivitas.</div>
      ) : (
        <ul className="divide-y divide-white/5">
          {items.map((a) => {
            const link = activityLink(a);
            const inner = (
              <div className="flex items-start gap-3 py-2.5">
                <div className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[#FF1F8E]" />
                <div className="min-w-0 flex-1">
                  <div className="text-sm text-zinc-200"><span className="font-semibold">{humanize(a.action)}</span> <span className="text-zinc-500">· {humanize(a.module)}</span></div>
                  <div className="text-[11px] text-zinc-500">{a.user_name} · {timeAgo(a.created_at)}</div>
                </div>
                {link && <ArrowRight className="mt-1 h-3.5 w-3.5 shrink-0 text-zinc-600" />}
              </div>
            );
            return <li key={a.id}>{link ? <Link to={link} className="block transition-colors hover:bg-white/[0.03]" data-testid={`admin-activity-item-${a.id}`}>{inner}</Link> : <div data-testid={`admin-activity-item-${a.id}`}>{inner}</div>}</li>;
          })}
        </ul>
      )}
    </section>
  );
}

export default function AdminDashboard() {
  const [m, setM] = useState(null);
  useEffect(() => { api.get("/admin/dashboard").then((r) => setM(r.data)); }, []);

  return (
    <div className="space-y-8">
      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Command Center</div>
        <h1 className="font-display text-3xl md:text-4xl font-extrabold tracking-tighter">Admin Dashboard</h1>
        <p className="text-sm text-zinc-400 mt-1">Apa yang terjadi dan apa yang perlu ditindaklanjuti di RILIS MUSIK.</p>
      </div>

      <ActionCenter />
      <QuickActions />

      <section>
        <div className="mb-3 text-xs font-bold uppercase tracking-widest text-zinc-500">Ringkasan Platform</div>
        {!m ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4" data-testid="admin-dashboard-loading">{Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-24 animate-pulse rounded-lg border border-white/10 bg-white/[0.03]" />)}</div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            <Stat testId={ADMIN_DASHBOARD.totalLabels} label="Total Label" value={m.total_labels} icon={Building2} accent="rose" />
            <Stat testId="admin-dashboard-total-artists" label="Total Artist" value={m.total_artists} icon={Users2} accent="indigo" />
            <Stat testId={ADMIN_DASHBOARD.totalReleases} label="Total Rilisan" value={m.total_releases} icon={Disc3} accent="amber" />
            <Stat testId="admin-dashboard-live" label="Live di DSP" value={m.live} icon={BarChart3} accent="emerald" />
            <Stat testId="admin-dashboard-delivered" label="Didistribusikan" value={m.delivered} icon={Disc3} accent="indigo" />
            <Stat testId="admin-dashboard-active-subscriptions" label="Langganan Aktif" value={m.active_subscriptions} icon={Crown} accent="amber" />
            <Stat testId="admin-dashboard-suspended-labels" label="Label Ditangguhkan" value={m.suspended_labels} icon={ShieldOff} accent="rose" />
            <Stat testId="admin-dashboard-paid-invoices" label="Invoice Dibayar" value={m.paid_invoices} icon={CreditCard} accent="emerald" />
          </div>
        )}
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        {m && (
          <div className="rm-card p-5">
            <div className="text-xs uppercase tracking-widest font-bold text-zinc-500 mb-3 flex items-center gap-2"><FileSpreadsheet className="w-4 h-4" /> Royalti</div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-zinc-500">Pendapatan Kotor EUR</div>
                <div className="font-display text-2xl font-extrabold tracking-tight">€ {(m.total_revenue_eur || 0).toLocaleString("en-US", { maximumFractionDigits: 2 })}</div>
              </div>
              <div>
                <div className="text-xs text-zinc-500">Total Bagian Label IDR</div>
                <div className="font-display text-2xl font-extrabold tracking-tight" data-testid={ADMIN_DASHBOARD.totalLabelShare}>{fmtIDR(m.total_revenue_idr)}</div>
                <div className="mt-3 divide-y divide-white/5 border-t border-white/10 text-xs">
                  <div className="flex items-center justify-between gap-3 py-2"><span className="text-zinc-500">Sudah Withdraw</span><strong className="tabular-nums text-zinc-300" data-testid={ADMIN_DASHBOARD.withdrawnLabelShare}>{fmtIDR(m.total_label_withdrawn_idr)}</strong></div>
                  <div className="flex items-center justify-between gap-3 py-2"><span className="text-zinc-500">Belum Withdraw</span><strong className="tabular-nums text-emerald-300" data-testid={ADMIN_DASHBOARD.unwithdrawnLabelShare}>{fmtIDR(m.total_label_unwithdrawn_idr)}</strong></div>
                </div>
              </div>
            </div>
            <div className="mt-4 text-xs text-zinc-500">CSV terakhir: {m.last_csv_import ? `${m.last_csv_import.period} • ${m.last_csv_import.created_at?.slice(0, 10)}` : "Belum ada"}</div>
          </div>
        )}
        <RecentActivity />
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
        <div className={`w-8 h-8 rounded-xl bg-gradient-to-br ${c} grid place-items-center`}><Icon className="w-4 h-4" /></div>
      </div>
      <div className="font-display font-extrabold tracking-tighter text-3xl mt-2" data-testid={`${testId}-value`}>{value}</div>
    </div>
  );
}
