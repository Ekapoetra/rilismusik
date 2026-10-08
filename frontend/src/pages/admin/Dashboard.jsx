import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import { usePollingRead } from "@/hooks/usePollingRead";
import { ADMIN_DASHBOARD } from "@/constants/testIds";
import { useAuth } from "@/api/AuthContext";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { useMasthead } from "@/components/v13/Masthead";
import { AlertTriangle, Check, ChevronDown, ChevronRight, ChevronUp } from "lucide-react";

function fmtIDR(n) { return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0); }
function fmtEUR(n) { return "€ " + (n || 0).toLocaleString("en-US", { maximumFractionDigits: 0 }); }
function fmtNum(n) { return new Intl.NumberFormat("id-ID").format(n || 0); }
function hhmm(iso) { if (!iso) return ""; return new Date(iso).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Jakarta" }); }
const humanize = (s) => (s || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
function activityLink(a) {
  const ref = a.reference_id;
  const map = { release: ref ? `/admin/releases/${ref}` : "/admin/releases", label: ref ? `/admin/labels/${ref}` : "/admin/labels", withdraw: "/admin/withdraw", kyc: "/admin/kyc", ticket: "/admin/tickets", support: "/admin/tickets", payment: "/admin/payments", bank_account: "/admin/labels", admin_user: "/admin/admin-users" };
  return map[a.module] || null;
}
const PERIODS = [{ k: "today", l: "Hari ini" }, { k: "week", l: "Minggu ini" }, { k: "month", l: "Bulan ini" }];
const sum = (list, field) => list.reduce((total, item) => total + (item[field] || 0), 0);

const Chevron = ({ direction = "right" }) => {
  const Icon = { right: ChevronRight, down: ChevronDown, up: ChevronUp }[direction];
  return <span className="v13-chevron" aria-hidden="true"><Icon /></span>;
};

// One compact status design; only Priority/Overdue bullets pulse.
function WorkPill({ item }) {
  const { t } = useAppPreferences();
  if (item.overdue_count > 0) return <span className="v13-pill" data-tone="red" data-pulse>{t("Lewat tenggat")}</span>;
  if (item.priority === "critical" || item.priority === "high") return <span className="v13-pill" data-tone="mustard" data-pulse>{t("Prioritas")}</span>;
  return <span className="v13-pill">{t("Baru")}</span>;
}

function Attention({ work }) {
  const { t } = useAppPreferences();
  const late = work.filter((item) => item.overdue_count > 0);
  const total = sum(late, "overdue_count");
  if (!total) return null;
  const names = late.map((item) => t(item.label_id));
  const detail = names.length > 2 ? `${names.slice(0, 2).join(", ")} ${t("dan")} ${names.length - 2} ${t("jenis pekerjaan lainnya")}.` : `${names.join(` ${t("dan")} `)}.`;
  return <Link to={late[0].link || "/admin/work"} className="v13-attention" data-testid="admin-attention">
    <AlertTriangle aria-hidden="true" />
    <div><h3>{t("Tenggat terlewat")} · {total}</h3><p>{detail}</p></div>
    <Chevron />
  </Link>;
}

function WorkStats({ work, team, progress, completed }) {
  const { t } = useAppPreferences();
  const open = sum(work, "open_count") + sum(team, "open_count");
  const overdue = sum(work, "overdue_count") + sum(team, "overdue_count");
  const handling = progress?.length ?? null;
  const cards = [
    ["total", "Total Pekerjaan", handling === null ? "…" : open + handling, "Antrean dan proses berjalan"],
    ["open", "Antrean Baru", Math.max(0, open - overdue), "Belum ditangani"],
    ["progress", "Dalam Penanganan", handling ?? "…", "Sedang diproses"],
    ["overdue", "Lewat Tenggat", overdue, "Melewati SLA"],
    ["done", "Selesai Hari Ini", completed ?? "…", "Pekerjaan selesai"],
  ];
  return <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5" data-testid="admin-work-stats">
    {cards.map(([key, label, value, sub]) => <Link key={key} to="/admin/work" className="v13-stat" data-testid={`admin-work-stat-${key}`}><span>{t(label)}</span><strong>{value}</strong><small>{t(sub)}</small><Chevron direction="down" /></Link>)}
  </div>;
}

function Queue({ work, team, isManager, pending, error }) {
  const { t } = useAppPreferences();
  const [scope, setScope] = useState("my");
  const list = (scope === "team" ? team : work).filter((item) => item.open_count > 0);
  return <section className="v13-card" data-testid="admin-my-work">
    <div className="v13-card-head"><h2>{t("Antrean Pekerjaan")}</h2>{isManager && <select className="v13-select" value={scope} onChange={(event) => setScope(event.target.value)} aria-label={t("Lingkup antrean")} data-testid="admin-queue-scope"><option value="my">{t("Saya")}</option><option value="team">{t("Tim")}</option></select>}</div>
    <div className="v13-card-body">
      {pending ? <p role="status" className="py-6 text-sm text-[var(--ui-muted)]">{t("Memuat pekerjaan…")}</p>
        : error ? <p role="alert" className="py-6 text-sm text-[var(--v13-urgent)]">{t("Pekerjaan belum dapat dimuat.")}</p>
          : !list.length ? <p className="py-6 text-sm text-[var(--ui-muted)]" data-testid="admin-my-work-list-empty">{t(scope === "team" ? "Tidak ada pekerjaan tim terbuka." : "Tidak ada pekerjaan untuk Anda.")}</p>
            : <div data-testid="admin-my-work-list">{list.slice(0, 6).map((item) => <Link key={item.work_type} to={item.link} className="v13-row" data-testid={`work-row-${item.work_type}`}>
              <div className="min-w-0"><div className="v13-row-title truncate">{t(item.label_id)}</div><div className="v13-row-sub"><span data-testid={`work-count-${item.work_type}`}>{item.open_count}</span> {t("terbuka")}{item.oldest_age_days ? ` · ${t("tertua")} ${item.oldest_age_days} ${t("hari")}` : ""}</div></div>
              <div className="flex shrink-0 items-center gap-3"><WorkPill item={item} /><Chevron /></div>
            </Link>)}</div>}
      <Link to="/admin/work" className="mt-2 inline-flex text-sm text-[var(--ui-muted)] hover:text-[var(--ui-text)]" data-testid="admin-focus-all">{t("Lihat semua antrean")}</Link>
    </div>
  </section>;
}

function Steps({ step, total }) {
  const count = Math.max(1, total || 1);
  const done = Math.max(0, Math.min(count, step || 0));
  return <div className="v13-steps" style={{ "--steps": count, "--fraction": count > 1 ? Math.min(1, done / (count - 1)) : 1 }} aria-label={`${done}/${count}`}>
    {Array.from({ length: count }).map((_, index) => <i key={index} className={index < done ? "is-done" : index === done ? "is-current" : ""}>{index < done && <Check strokeWidth={3} />}</i>)}
  </div>;
}

function Running({ items, error }) {
  const { t } = useAppPreferences();
  return <section className="v13-card" data-testid="admin-inprogress-panel">
    <div className="v13-card-head"><h2>{t("Pekerjaan Berjalan")}</h2></div>
    <div className="v13-card-body">
      {error && items === null ? <p role="alert" className="py-6 text-sm text-[var(--v13-urgent)]">{t("Pekerjaan berjalan belum dapat dimuat.")}</p>
        : items === null ? <p role="status" className="py-6 text-sm text-[var(--ui-muted)]">{t("Memuat pekerjaan…")}</p>
          : !items.length ? <p className="py-6 text-sm text-[var(--ui-muted)]" data-testid="admin-inprogress-empty">{t("Tidak ada pekerjaan berjalan.")}</p>
            : <div data-testid="admin-inprogress">{items.slice(0, 5).map((item) => <Link key={`${item.category}-${item.id}`} to={item.link} className="block border-b border-[var(--ui-border)] py-3.5 last:border-0" data-testid={`inprogress-item-${item.id}`}>
              <div className="flex items-center justify-between gap-3"><div className="min-w-0"><div className="v13-row-title truncate">{t(item.category)} · {item.title}</div><div className="v13-row-sub">{t(item.status_label)}</div></div><Chevron /></div>
              <Steps step={item.step} total={item.total_steps} />
            </Link>)}</div>}
    </div>
  </section>;
}

function Trend({ trend }) {
  if (!trend || trend.pct === null || trend.pct === undefined) return <span className="v13-trend">—</span>;
  const direction = trend.direction === "up" ? "up" : trend.direction === "down" ? "down" : "flat";
  return <span className="v13-trend" data-trend={direction}>{direction === "up" && <ChevronUp />}{direction === "down" && <ChevronDown />}{trend.pct > 0 ? "+" : ""}{trend.pct}%</span>;
}

function KpiCard({ label, value, trend, sub, to, testid }) {
  const inner = <div className="v13-metric h-full" data-testid={testid}>
    <h3>{label}</h3>
    <strong data-testid={`${testid}-value`}>{value}</strong>
    <div className="mt-auto flex flex-wrap items-center gap-2 pt-3"><Trend trend={trend} />{sub && <span className="text-xs text-[var(--ui-muted)]">{sub}</span>}</div>
  </div>;
  return to ? <Link to={to}>{inner}</Link> : inner;
}

// Money KPI with its own independent period dropdown (Today / This week / This month).
function MoneyKpiCard({ kind, label, sub, testid, defaultPeriod = "today" }) {
  const { t } = useAppPreferences();
  const [period, setPeriod] = useState(defaultPeriod);
  const result = usePollingRead("/admin/dashboard/money", { kind, period }, { refreshEvent: "rilismusik:new-notification" });
  const data = result.data;
  return <div className="v13-metric h-full" data-testid={testid}>
    <div className="flex items-center justify-between gap-2"><h3>{label}</h3>
      <select value={period} onChange={(e) => setPeriod(e.target.value)} className="v13-select" data-testid={`${testid}-period`}>{PERIODS.map((p) => <option key={p.k} value={p.k}>{t(p.l)}</option>)}</select>
    </div>
    <strong data-testid={`${testid}-value`}>{data ? fmtIDR(data.value) : result.error ? "—" : "…"}</strong>
    {result.error && <p role="alert" className="mt-1 text-xs text-[var(--v13-urgent)]">{t("Nilai belum dapat diperbarui.")}</p>}
    <div className="mt-auto flex flex-wrap items-center gap-2 pt-3"><Trend trend={data?.trend} />{sub && <span className="text-xs text-[var(--ui-muted)]">{sub}</span>}</div>
  </div>;
}

function RecentActivity({ selfOnly, userId }) {
  const { t } = useAppPreferences();
  const [items, setItems] = useState(null);
  useEffect(() => { api.get("/admin/activity-logs", { params: { limit: 60 } }).then((r) => setItems(r.data || [])).catch(() => setItems([])); }, []);
  // Dashboard feed = Work & Finance activity only (system events excluded).
  const rows = (items || []).filter((a) => (a.category === "work" || a.category === "finance") && (!selfOnly || a.user_id === userId)).slice(0, 6);
  return <section className="v13-card" data-testid="admin-recent-activity">
    <div className="v13-card-head"><h2>{t("Aktivitas Terbaru")}</h2><Link to="/admin/activity-logs" className="text-sm text-[var(--ui-muted)] hover:text-[var(--ui-text)]">{t("Lihat semua")}</Link></div>
    <div className="v13-card-body">
      {items === null ? <p role="status" className="py-6 text-sm text-[var(--ui-muted)]">{t("Memuat aktivitas…")}</p>
        : !rows.length ? <p className="py-6 text-sm text-[var(--ui-muted)]">{t("Belum ada aktivitas.")}</p>
          : rows.map((a) => {
            const link = activityLink(a);
            const inner = <><div className="min-w-0"><div className="v13-row-title truncate">{selfOnly ? t("Anda") : (a.user_name || "—")} · {t(humanize(a.action))}</div><div className="v13-row-sub">{t(humanize(a.module))}</div></div><span className="shrink-0 text-xs tabular-nums text-[var(--ui-muted)]">{hhmm(a.created_at)}</span></>;
            return link ? <Link key={a.id} to={link} className="v13-row" data-testid={`admin-activity-item-${a.id}`}>{inner}</Link> : <div key={a.id} className="v13-row" data-testid={`admin-activity-item-${a.id}`}>{inner}</div>;
          })}
    </div>
  </section>;
}

export default function AdminDashboard() {
  const { user, hasPermission } = useAuth();
  const { t } = useAppPreferences();
  const canWork = hasPermission("work.view");
  const workResult = usePollingRead("/admin/work/queue", { scope: "all" }, { enabled: canWork, refreshEvent: "rilismusik:new-notification" });
  const metricsResult = usePollingRead("/admin/dashboard/metrics", { period: "month", include_money: false }, { refreshEvent: "rilismusik:new-notification" });
  const progressResult = usePollingRead("/admin/dashboard/in-progress");
  const summaryResult = usePollingRead("/admin/dashboard/work-summary", { period: "today", include_progress: false });
  const metrics = metricsResult.data;
  const inprog = progressResult.data?.items || null;
  const work = workResult.data?.items || [];
  const team = workResult.data?.team_items || [];
  const isManager = Boolean(workResult.data?.is_manager);
  const workPending = canWork && (!workResult.data || workResult.data.synchronizing);
  const completed = summaryResult.data ? summaryResult.data.completed : null;
  const isSuper = user?.role === "super_admin";
  const m = metrics || {};
  const openWork = sum(work, "open_count");

  let summary = t("Selamat datang di dashboard.");
  if (canWork && workResult.error) summary = t("Daftar pekerjaan belum dapat diperbarui.");
  else if (canWork && workPending) summary = t("Memuat daftar pekerjaan…");
  else if (canWork) summary = `${openWork} ${t("pekerjaan dalam antrean")}${completed !== null ? ` · ${completed} ${t("pekerjaan selesai hari ini")}` : ""}.`;
  useMasthead({
    summary,
    insight: metrics?.total_labels ? { value: fmtNum(metrics.total_labels.value), title: t("Label dalam ruang kerja Rilis Musik."), detail: `+${fmtNum(metrics.total_labels.added || 0)} ${t("label baru bulan ini.")}`, to: "/admin/labels" } : null,
  });

  return <div className="space-y-5" data-testid="admin-dashboard">
    <p className="sr-only" data-testid="admin-greeting-message">{summary}</p>
    {canWork && workResult.error && <p role="alert" className="text-sm text-[var(--v13-urgent)]">{t("Daftar pekerjaan belum dapat diperbarui. Data terakhir tetap ditampilkan.")}</p>}
    {canWork && !workPending && <Attention work={[...work, ...team]} />}
    {canWork && <WorkStats work={work} team={team} progress={inprog} completed={completed} />}
    {canWork && <div className="grid gap-5 lg:grid-cols-2">
      <Queue work={work} team={team} isManager={isManager} pending={workPending} error={workResult.error && !workResult.data} />
      <Running items={inprog} error={progressResult.error} />
    </div>}

    {metricsResult.error && <p role="alert" className="text-sm text-[var(--v13-urgent)]">{t("Ringkasan platform belum dapat diperbarui.")}</p>}
    <section className="space-y-3" data-testid="admin-kpi-section">
      {metrics === null && !metricsResult.error ? <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-40 animate-pulse rounded-2xl bg-[var(--ui-surface)]" />)}</div>
        : !metrics ? <p role="alert">{t("Ringkasan belum tersedia.")}</p> : <>
          <div className={`grid gap-3 ${isSuper ? "md:grid-cols-3" : "md:grid-cols-1"}`}>
            <MoneyKpiCard kind="sales" label={t("Pendapatan Penjualan")} sub={t("via Xendit")} defaultPeriod="today" testid="kpi-sales-revenue" />
            {isSuper && <MoneyKpiCard kind="withdrawal" label={t("Penarikan Diajukan")} defaultPeriod="month" testid="kpi-requested-withdrawal" />}
            {isSuper && <KpiCard label={t("Pendapatan Royalti")} value={fmtIDR(m.royalty_income?.value)} trend={m.royalty_income?.trend} sub={m.royalty_income?.period ? `${fmtEUR(m.royalty_income?.eur)} · ${m.royalty_income.period}` : t("impor CSV Believe")} to="/admin/analytics" testid="kpi-royalty-income" />}
          </div>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <KpiCard label={t("Total Label")} value={fmtNum(m.total_labels?.value)} trend={m.total_labels?.trend} sub={`+${m.total_labels?.added || 0} ${t("bulan ini")}`} to="/admin/labels" testid={ADMIN_DASHBOARD.totalLabels} />
            <KpiCard label={t("Total Artis")} value={fmtNum(m.total_artists?.value)} trend={m.total_artists?.trend} sub={`+${m.total_artists?.added || 0} ${t("bulan ini")}`} testid="kpi-total-artists" />
            <KpiCard label={t("Total Rilisan")} value={fmtNum(m.total_releases?.value)} trend={m.total_releases?.trend} sub={`+${m.total_releases?.added || 0} ${t("bulan ini")}`} to="/admin/releases" testid={ADMIN_DASHBOARD.totalReleases} />
            <KpiCard label={t("Member Aktif")} value={fmtNum(m.active_members?.value)} trend={m.active_members?.trend} sub={t("aktivasi akun")} testid="kpi-active-members" />
          </div>
        </>}
    </section>
    <RecentActivity selfOnly={!isSuper} userId={user?.id} />
  </div>;
}
