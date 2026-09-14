import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import * as Icons from "lucide-react";
import { api } from "@/api/client";
import { ADMIN_DASHBOARD } from "@/constants/testIds";
import { useAuth } from "@/api/AuthContext";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import {
  Building2, Users2, Disc3, FileSpreadsheet, CreditCard, Crown, ShieldOff,
  Activity, BarChart3, ArrowRight, AlertTriangle, CheckCircle2, Target,
  ClipboardList, Users, Settings2, Sun, Sunrise, Sunset, Moon,
} from "lucide-react";

const iconFor = (name) => Icons[name] || Icons.Circle;
function fmtIDR(n) { return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0); }
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

// ---------------- Greeting ----------------
function greetPhrase(hourWIB, t) {
  if (hourWIB < 11) return { text: t("Selamat pagi"), Icon: Sunrise };
  if (hourWIB < 15) return { text: t("Selamat siang"), Icon: Sun };
  if (hourWIB < 19) return { text: t("Selamat sore"), Icon: Sunset };
  return { text: t("Selamat malam"), Icon: Moon };
}

function Greeting({ name, work, team, isManager }) {
  const { t } = useAppPreferences();
  const hourWIB = new Date(Date.now() + 7 * 3600 * 1000).getUTCHours();
  const { text, Icon } = greetPhrase(hourWIB, t);
  const openWork = work.reduce((s, w) => s + (w.open_count || 0), 0);
  const overdue = work.reduce((s, w) => s + (w.overdue_count || 0), 0);
  const teamOpen = team.reduce((s, w) => s + (w.open_count || 0), 0);

  let message;
  if (openWork === 0 && (!isManager || teamOpen === 0)) {
    message = t("Semua pekerjaan Anda sudah tertangani. 🎉");
  } else if (isManager && teamOpen > 0) {
    message = `${t("Tim Anda memiliki")} ${teamOpen} ${t("pekerjaan terbuka hari ini")}${overdue ? `, ${t("termasuk")} ${overdue} ${t("lewat tempo")}` : ""}.`;
  } else {
    message = `${t("Anda memiliki")} ${openWork} ${t("pekerjaan di antrean")}${overdue ? `, ${overdue} ${t("lewat tempo")}` : ""}.`;
  }

  return (
    <div data-testid="admin-greeting">
      <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">{t("Command Center")}</div>
      <h1 className="mt-1 flex items-center gap-2.5 font-display text-3xl md:text-4xl font-extrabold tracking-tighter">
        <Icon className="h-7 w-7 text-[#FF1F8E]" /> {text}, {name}.
      </h1>
      <p className="mt-2 text-sm text-zinc-300" data-testid="admin-greeting-message">{message}</p>
    </div>
  );
}

// ---------------- My Work ----------------
function WorkQueueCard({ item }) {
  const { t } = useAppPreferences();
  const Ico = iconFor(item.icon);
  return (
    <Link to={item.link} className="group flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/[0.02] p-4 transition-colors hover:bg-white/[0.05]" data-testid={`mywork-item-${item.work_type}`}>
      <div className="flex min-w-0 items-center gap-3">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-white/5"><Ico className="h-4 w-4 text-pink-300" /></span>
        <div className="min-w-0">
          <div className="truncate text-sm font-bold">{t(item.label_id)}</div>
          {item.overdue_count > 0 && <div className="mt-0.5 inline-flex items-center gap-1 rounded bg-red-500/15 px-1.5 text-[11px] font-bold text-red-300"><AlertTriangle className="h-3 w-3" />{item.overdue_count} {t("lewat tempo")}</div>}
        </div>
      </div>
      <span className="font-display text-2xl font-extrabold tabular-nums" data-testid={`mywork-count-${item.work_type}`}>{item.open_count}</span>
    </Link>
  );
}

function MyWork({ work }) {
  const { t } = useAppPreferences();
  const items = work.filter((w) => w.open_count > 0);
  return (
    <section data-testid="admin-my-work">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2"><ClipboardList className="h-5 w-5 text-[#FF1F8E]" /><h2 className="font-display text-2xl font-extrabold tracking-tighter">{t("Pekerjaan Saya")}</h2></div>
        <Link to="/admin/work" className="inline-flex items-center gap-1 text-xs font-bold text-zinc-400 hover:text-white" data-testid="admin-my-work-all">{t("Buka antrean")} <ArrowRight className="h-3.5 w-3.5" /></Link>
      </div>
      {items.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-emerald-400/20 bg-emerald-400/[0.05] p-8 text-center" data-testid="admin-my-work-empty">
          <CheckCircle2 className="h-8 w-8 text-emerald-400" /><div className="font-display font-bold">{t("Tidak ada pekerjaan untuk Anda saat ini.")}</div>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{items.map((it) => <WorkQueueCard key={it.work_type} item={it} />)}</div>
      )}
    </section>
  );
}

// ---------------- Team Monitor ----------------
function TeamMonitor({ team }) {
  const { t } = useAppPreferences();
  const items = team.filter((w) => w.open_count > 0);
  const totalOpen = items.reduce((s, w) => s + w.open_count, 0);
  const totalOverdue = items.reduce((s, w) => s + (w.overdue_count || 0), 0);
  return (
    <section data-testid="admin-team-monitor">
      <div className="mb-3 flex items-center gap-2"><Users className="h-5 w-5 text-indigo-300" /><h2 className="font-display text-2xl font-extrabold tracking-tighter">{t("Monitor Tim")}</h2>
        <span className="ml-1 rounded-full bg-white/10 px-2 py-0.5 text-[11px] font-bold tabular-nums">{totalOpen} {t("terbuka")}</span>
        {totalOverdue > 0 && <span className="rounded-full bg-red-500/15 px-2 py-0.5 text-[11px] font-bold text-red-300">{totalOverdue} {t("lewat tempo")}</span>}
      </div>
      {items.length === 0 ? (
        <div className="rounded-lg border border-white/10 p-6 text-center text-sm text-zinc-500" data-testid="admin-team-monitor-empty">{t("Tidak ada pekerjaan tim yang terbuka.")}</div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{items.map((it) => <WorkQueueCard key={it.work_type} item={it} />)}</div>
      )}
    </section>
  );
}

// ---------------- Responsibility Gap ----------------
function ResponsibilityGap({ gaps }) {
  const { t } = useAppPreferences();
  if (!gaps || gaps.length === 0) return null;
  return (
    <div className="rounded-lg border border-amber-400/40 bg-amber-500/[0.06] p-4" data-testid="admin-responsibility-gap">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 font-bold text-amber-300"><AlertTriangle className="h-4 w-4" /> {t("Responsibility Gap")}</div>
          <p className="mt-1 text-sm text-amber-200/80">{gaps.length} {t("jenis pekerjaan belum memiliki role penanggung jawab")}: {gaps.map((g) => t(g.label_id)).join(", ")}.</p>
        </div>
        <Link to="/admin/work" className="rm-btn-ghost inline-flex items-center gap-2 text-sm" data-testid="admin-responsibility-gap-cta"><Settings2 className="h-4 w-4" /> {t("Atur penanggung jawab")}</Link>
      </div>
    </div>
  );
}

// ---------------- Today's Focus ----------------
function TodaysFocus({ work, gaps }) {
  const { t } = useAppPreferences();
  const buckets = [];
  if (gaps.length) buckets.push({ key: "gap", label: t("Responsibility Gap"), count: gaps.length, cls: "text-amber-300", Icon: AlertTriangle });
  const critical = work.filter((w) => w.priority === "critical" && w.open_count > 0).reduce((s, w) => s + w.open_count, 0);
  if (critical) buckets.push({ key: "critical", label: t("Pekerjaan kritis/mendesak"), count: critical, cls: "text-rose-300", Icon: Target });
  const overdue = work.reduce((s, w) => s + (w.overdue_count || 0), 0);
  if (overdue) buckets.push({ key: "overdue", label: t("Pekerjaan lewat tempo"), count: overdue, cls: "text-red-300", Icon: AlertTriangle });
  const important = work.filter((w) => w.priority === "high" && w.open_count > 0).reduce((s, w) => s + w.open_count, 0);
  if (important) buckets.push({ key: "important", label: t("Persetujuan penting"), count: important, cls: "text-amber-200", Icon: Target });
  const other = work.filter((w) => !["critical", "high"].includes(w.priority)).reduce((s, w) => s + w.open_count, 0);
  if (other) buckets.push({ key: "other", label: t("Pekerjaan terbuka lainnya"), count: other, cls: "text-zinc-300", Icon: ClipboardList });

  return (
    <section className="rm-card p-5" data-testid="admin-todays-focus">
      <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-zinc-500"><Target className="h-4 w-4" /> {t("Fokus Hari Ini")}</div>
      {buckets.length === 0 ? (
        <div className="py-6 text-center text-sm text-emerald-300" data-testid="admin-todays-focus-empty">{t("Semuanya terkendali.")}</div>
      ) : (
        <ul className="space-y-2">
          {buckets.map((b) => (
            <li key={b.key} className="flex items-center justify-between gap-3 rounded-md border border-white/5 bg-white/[0.02] px-3 py-2.5" data-testid={`admin-focus-${b.key}`}>
              <span className={`flex items-center gap-2 text-sm ${b.cls}`}><b.Icon className="h-4 w-4" /> {b.label}</span>
              <span className="font-display text-lg font-extrabold tabular-nums">{b.count}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// ---------------- Recent Activity ----------------
function RecentActivity() {
  const { t } = useAppPreferences();
  const [items, setItems] = useState(null);
  useEffect(() => { api.get("/admin/activity-logs", { params: { limit: 6 } }).then((r) => setItems(r.data || [])).catch(() => setItems([])); }, []);
  return (
    <section className="rm-card p-5" data-testid="admin-recent-activity">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-zinc-500"><Activity className="h-4 w-4" /> {t("Aktivitas Terbaru")}</div>
        <Link to="/admin/activity-logs" className="inline-flex items-center gap-1 text-xs font-bold text-zinc-400 hover:text-white" data-testid="admin-recent-activity-all">{t("Lihat semua")} <ArrowRight className="h-3.5 w-3.5" /></Link>
      </div>
      {items === null ? (
        <div className="space-y-2">{[0, 1, 2].map((i) => <div key={i} className="h-8 animate-pulse rounded bg-white/[0.04]" />)}</div>
      ) : items.length === 0 ? (
        <div className="py-6 text-center text-sm text-zinc-600">{t("Belum ada aktivitas.")}</div>
      ) : (
        <ul className="divide-y divide-white/5">
          {items.map((a) => {
            const link = activityLink(a);
            const inner = (
              <div className="flex items-start gap-3 py-2.5">
                <div className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[#FF1F8E]" />
                <div className="min-w-0 flex-1">
                  <div className="text-sm text-zinc-200"><span className="font-semibold">{a.user_name || "—"}</span> <span className="text-zinc-400">{t(humanize(a.action))}</span> <span className="text-zinc-500">· {t(humanize(a.module))}</span></div>
                  <div className="text-[11px] text-zinc-500">{timeAgo(a.created_at)}</div>
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

// ---------------- Page ----------------
export default function AdminDashboard() {
  const { user, hasPermission } = useAuth();
  const { t } = useAppPreferences();
  const [m, setM] = useState(null);
  const [work, setWork] = useState([]);
  const [gaps, setGaps] = useState([]);
  const [team, setTeam] = useState([]);
  const [isManager, setIsManager] = useState(false);
  const name = user?.name || user?.pic_name || user?.email || "Admin";
  const canWork = hasPermission("work.view");

  const loadWork = useCallback(async () => {
    if (!canWork) return;
    try {
      const { data } = await api.get("/admin/work/queue", { params: { scope: "my" } });
      setWork(data.items || []); setGaps(data.gaps || []); setIsManager(!!data.is_manager);
      if (data.is_manager) {
        try { const { data: td } = await api.get("/admin/work/queue", { params: { scope: "team" } }); setTeam(td.items || []); } catch { /* */ }
      }
    } catch { /* no work.view permission */ }
  }, [canWork]);

  useEffect(() => { api.get("/admin/dashboard").then((r) => setM(r.data)).catch(() => {}); loadWork(); }, [loadWork]);

  return (
    <div className="space-y-8">
      <Greeting name={name} work={work} team={team} isManager={isManager} />

      {canWork && <ResponsibilityGap gaps={gaps} />}

      {canWork && (
        <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
          <MyWork work={work} />
          <TodaysFocus work={work} gaps={gaps} />
        </div>
      )}

      {canWork && isManager && <TeamMonitor team={team} />}

      <section>
        <div className="mb-3 text-xs font-bold uppercase tracking-widest text-zinc-500">{t("Ringkasan Platform")}</div>
        {!m ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4" data-testid="admin-dashboard-loading">{Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-24 animate-pulse rounded-lg border border-white/10 bg-white/[0.03]" />)}</div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            <Stat testId={ADMIN_DASHBOARD.totalLabels} label={t("Total Label")} value={m.total_labels} icon={Building2} accent="rose" />
            <Stat testId="admin-dashboard-total-artists" label={t("Total Artist")} value={m.total_artists} icon={Users2} accent="indigo" />
            <Stat testId={ADMIN_DASHBOARD.totalReleases} label={t("Total Rilisan")} value={m.total_releases} icon={Disc3} accent="amber" />
            <Stat testId="admin-dashboard-live" label={t("Live di DSP")} value={m.live} icon={BarChart3} accent="emerald" />
            <Stat testId="admin-dashboard-delivered" label={t("Didistribusikan")} value={m.delivered} icon={Disc3} accent="indigo" />
            <Stat testId="admin-dashboard-active-subscriptions" label={t("Langganan Aktif")} value={m.active_subscriptions} icon={Crown} accent="amber" />
            <Stat testId="admin-dashboard-suspended-labels" label={t("Label Ditangguhkan")} value={m.suspended_labels} icon={ShieldOff} accent="rose" />
            <Stat testId="admin-dashboard-paid-invoices" label={t("Invoice Dibayar")} value={m.paid_invoices} icon={CreditCard} accent="emerald" />
          </div>
        )}
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        {m && (
          <div className="rm-card p-5">
            <div className="text-xs uppercase tracking-widest font-bold text-zinc-500 mb-3 flex items-center gap-2"><FileSpreadsheet className="w-4 h-4" /> {t("Royalti")}</div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-zinc-500">{t("Pendapatan Kotor EUR")}</div>
                <div className="font-display text-2xl font-extrabold tracking-tight">€ {(m.total_revenue_eur || 0).toLocaleString("en-US", { maximumFractionDigits: 2 })}</div>
              </div>
              <div>
                <div className="text-xs text-zinc-500">{t("Total Bagian Label IDR")}</div>
                <div className="font-display text-2xl font-extrabold tracking-tight" data-testid={ADMIN_DASHBOARD.totalLabelShare}>{fmtIDR(m.total_revenue_idr)}</div>
                <div className="mt-3 divide-y divide-white/5 border-t border-white/10 text-xs">
                  <div className="flex items-center justify-between gap-3 py-2"><span className="text-zinc-500">{t("Sudah Withdraw")}</span><strong className="tabular-nums text-zinc-300" data-testid={ADMIN_DASHBOARD.withdrawnLabelShare}>{fmtIDR(m.total_label_withdrawn_idr)}</strong></div>
                  <div className="flex items-center justify-between gap-3 py-2"><span className="text-zinc-500">{t("Belum Withdraw")}</span><strong className="tabular-nums text-emerald-300" data-testid={ADMIN_DASHBOARD.unwithdrawnLabelShare}>{fmtIDR(m.total_label_unwithdrawn_idr)}</strong></div>
                </div>
              </div>
            </div>
            <div className="mt-4 text-xs text-zinc-500">{t("CSV terakhir")}: {m.last_csv_import ? `${m.last_csv_import.period} • ${m.last_csv_import.created_at?.slice(0, 10)}` : t("Belum ada")}</div>
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
