import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import * as Icons from "lucide-react";
import { api } from "@/api/client";
import { ADMIN_DASHBOARD } from "@/constants/testIds";
import { useAuth } from "@/api/AuthContext";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import {
  Building2, Users2, Disc3, CreditCard, Crown, Activity, ArrowRight, AlertTriangle,
  CheckCircle2, Target, ClipboardList, Users, ChevronRight, TrendingUp, TrendingDown,
  Wallet, Coins, Sun, Sunrise, Sunset, Moon, ListChecks, Loader2,
} from "lucide-react";

const iconFor = (name) => Icons[name] || Icons.Circle;
function fmtIDR(n) { return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0); }
function fmtEUR(n) { return "€ " + (n || 0).toLocaleString("en-US", { maximumFractionDigits: 0 }); }
function fmtNum(n) { return new Intl.NumberFormat("id-ID").format(n || 0); }
function hhmm(iso) { if (!iso) return ""; return new Date(iso).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Jakarta" }); }
const humanize = (s) => (s || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
const MODULE_ICON = { release: Disc3, label: Building2, withdraw: Wallet, kyc: CheckCircle2, ticket: Icons.MessageSquare, support: Icons.MessageSquare, payment: CreditCard, admin_user: Users2, auth: Users2 };
function activityLink(a) {
  const ref = a.reference_id;
  const map = { release: ref ? `/admin/releases/${ref}` : "/admin/releases", label: ref ? `/admin/labels/${ref}` : "/admin/labels", withdraw: "/admin/withdraw", kyc: "/admin/kyc", ticket: "/admin/tickets", support: "/admin/tickets", payment: "/admin/payments", bank_account: "/admin/labels", admin_user: "/admin/admin-users" };
  return map[a.module] || null;
}
const PERIODS = [{ k: "today", l: "Hari ini" }, { k: "week", l: "Minggu ini" }, { k: "month", l: "Bulan ini" }];

function greetPhrase(hourWIB, t) {
  if (hourWIB < 11) return { text: t("Selamat pagi"), Icon: Sunrise };
  if (hourWIB < 15) return { text: t("Selamat siang"), Icon: Sun };
  if (hourWIB < 19) return { text: t("Selamat sore"), Icon: Sunset };
  return { text: t("Selamat malam"), Icon: Moon };
}

const PRIO_META = {
  critical: { cls: "bg-rose-500/15 text-rose-300", label: "Kritis" },
  high: { cls: "bg-amber-500/15 text-amber-300", label: "Tinggi" },
  normal: { cls: "bg-sky-500/15 text-sky-300", label: "Normal" },
  low: { cls: "bg-zinc-500/15 text-zinc-300", label: "Rendah" },
};

function Greeting({ name, work, team, isManager }) {
  const { t } = useAppPreferences();
  const now = new Date();
  const dateStr = now.toLocaleDateString("id-ID", { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Jakarta" });
  const hourWIB = new Date(Date.now() + 7 * 3600 * 1000).getUTCHours();
  const { text, Icon } = greetPhrase(hourWIB, t);
  const openWork = work.reduce((s, w) => s + (w.open_count || 0), 0);
  const teamOpen = team.reduce((s, w) => s + (w.open_count || 0), 0);
  const overdue = work.reduce((s, w) => s + (w.overdue_count || 0), 0);
  let message;
  if (openWork === 0 && (!isManager || teamOpen === 0)) message = t("Semua pekerjaan sudah tertangani. 🎉");
  else if (isManager && teamOpen > 0) message = `${t("Tim Anda punya")} ${teamOpen} ${t("pekerjaan terbuka")}${overdue ? `, ${overdue} ${t("lewat tempo")}` : ""}. ${t("Mari selesaikan yang prioritas.")}`;
  else message = `${t("Ada")} ${openWork} ${t("pekerjaan menunggu, mari selesaikan yang paling prioritas.")}`;
  return (
    <div data-testid="admin-greeting">
      <div className="text-xs uppercase tracking-widest text-zinc-500 font-semibold">{dateStr}</div>
      <h1 className="mt-1 flex items-center gap-2.5 font-display text-3xl md:text-4xl font-extrabold tracking-tighter">
        <Icon className="h-7 w-7 text-[#FF1F8E]" /> {text}, {name}.
      </h1>
      <p className="mt-2 text-sm text-zinc-300" data-testid="admin-greeting-message">{message}</p>
    </div>
  );
}

function TodaysFocus({ work }) {
  const { t } = useAppPreferences();
  const order = { critical: 0, high: 1, normal: 2, low: 3 };
  const items = work.filter((w) => w.open_count > 0)
    .sort((a, b) => (order[a.priority] ?? 2) - (order[b.priority] ?? 2))
    .slice(0, 5);
  return (
    <section className="rm-card p-5" data-testid="admin-todays-focus">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2"><Target className="h-5 w-5 text-[#FF1F8E]" /><div><div className="font-display text-lg font-extrabold tracking-tight">{t("Fokus Hari Ini")}</div><div className="text-xs text-zinc-500">{items.length} {t("prioritas pekerjaan")}</div></div></div>
        <Link to="/admin/work" className="inline-flex items-center gap-1 text-xs font-bold text-zinc-400 hover:text-white" data-testid="admin-focus-all">{t("Lihat semua")} <ArrowRight className="h-3.5 w-3.5" /></Link>
      </div>
      {items.length === 0 ? (
        <div className="py-4 text-center text-sm text-emerald-300" data-testid="admin-todays-focus-empty">{t("Semuanya terkendali.")}</div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {items.map((it, i) => {
            const p = PRIO_META[it.priority] || PRIO_META.normal;
            return (
              <Link key={it.work_type} to={it.link} className="group flex items-center gap-3 rounded-lg border border-white/10 bg-white/[0.02] p-3 transition-colors hover:bg-white/[0.05]" data-testid={`admin-focus-item-${i}`}>
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[#FF1F8E]/15 font-display text-sm font-extrabold text-[#FF1F8E]">{i + 1}</span>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-bold">{t(it.label_id)}</div>
                  <span className={`mt-1 inline-block rounded px-1.5 py-0.5 text-[10px] font-bold ${p.cls}`}>{t(p.label)}</span>
                </div>
                <span className="font-display text-lg font-extrabold tabular-nums">{it.open_count}</span>
              </Link>
            );
          })}
        </div>
      )}
    </section>
  );
}

function WorkList({ items, testid, emptyLabel }) {
  const { t } = useAppPreferences();
  if (!items.length) return <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/[0.05] p-8 text-center" data-testid={`${testid}-empty`}><CheckCircle2 className="mx-auto h-8 w-8 text-emerald-400" /><div className="mt-2 font-display font-bold text-sm">{t(emptyLabel)}</div></div>;
  return (
    <div className="space-y-2.5" data-testid={testid}>
      {items.map((it) => {
        const Ico = iconFor(it.icon);
        return (
          <Link key={it.work_type} to={it.link} className="group flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/[0.02] p-3.5 transition-colors hover:bg-white/[0.05]" data-testid={`work-row-${it.work_type}`}>
            <div className="flex min-w-0 items-center gap-3">
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-white/5"><Ico className="h-4 w-4 text-pink-300" /></span>
              <div className="min-w-0">
                <div className="truncate text-sm font-bold">{t(it.label_id)}</div>
                {it.overdue_count > 0 ? <div className="mt-0.5 inline-flex items-center gap-1 rounded bg-red-500/15 px-1.5 text-[11px] font-bold text-red-300"><AlertTriangle className="h-3 w-3" />{it.overdue_count} {t("lewat tempo")}</div> : <div className="text-[11px] text-zinc-500">{t(PRIO_META[it.priority]?.label || "Normal")}</div>}
              </div>
            </div>
            <div className="flex items-center gap-2"><span className="font-display text-2xl font-extrabold tabular-nums" data-testid={`work-count-${it.work_type}`}>{it.open_count}</span><ChevronRight className="h-4 w-4 text-zinc-600 transition-transform group-hover:translate-x-0.5" /></div>
          </Link>
        );
      })}
    </div>
  );
}

function Panel({ icon: Icon, title, subtitle, to, tint = "text-[#FF1F8E]", children, testid }) {
  const { t } = useAppPreferences();
  return (
    <section className="rm-card p-5 h-full flex flex-col" data-testid={testid}>
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2"><Icon className={`h-5 w-5 ${tint}`} /><div><div className="font-display text-lg font-extrabold tracking-tight">{title}</div>{subtitle && <div className="text-xs text-zinc-500">{subtitle}</div>}</div></div>
        {to && <Link to={to} className="inline-flex items-center gap-1 text-xs font-bold text-zinc-400 hover:text-white">{t("Lihat semua")} <ArrowRight className="h-3.5 w-3.5" /></Link>}
      </div>
      <div className="flex-1">{children}</div>
    </section>
  );
}

function Pager({ page, pages, setPage, testid }) {
  if (pages <= 1) return null;
  return (
    <div className="mt-3 flex items-center justify-center gap-2" data-testid={testid}>
      <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0} className="grid h-7 w-7 place-items-center rounded-full border border-white/10 text-zinc-400 transition-colors hover:bg-white/10 disabled:opacity-30" data-testid={`${testid}-prev`}><ChevronRight className="h-3.5 w-3.5 rotate-180" /></button>
      {Array.from({ length: pages }).map((_, i) => <button key={i} onClick={() => setPage(i)} className={`h-1.5 rounded-full transition-all ${i === page ? "w-5 bg-[#FF1F8E]" : "w-1.5 bg-white/20"}`} data-testid={`${testid}-dot-${i}`} />)}
      <button onClick={() => setPage((p) => Math.min(pages - 1, p + 1))} disabled={page === pages - 1} className="grid h-7 w-7 place-items-center rounded-full border border-white/10 text-zinc-400 transition-colors hover:bg-white/10 disabled:opacity-30" data-testid={`${testid}-next`}><ChevronRight className="h-3.5 w-3.5" /></button>
    </div>
  );
}

const PAGE_SIZE = 4;

function InProgress({ items }) {
  const { t } = useAppPreferences();
  const [page, setPage] = useState(0);
  if (items === null) return <div className="space-y-2">{[0, 1, 2].map((i) => <div key={i} className="h-10 animate-pulse rounded bg-white/[0.04]" />)}</div>;
  if (!items.length) return <div className="py-6 text-center text-sm text-zinc-500" data-testid="admin-inprogress-empty">{t("Tidak ada pekerjaan berjalan.")}</div>;
  const pages = Math.ceil(items.length / PAGE_SIZE);
  const view = items.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);
  const barColor = (p) => p >= 75 ? "bg-emerald-400" : p >= 50 ? "bg-sky-400" : p > 0 ? "bg-amber-400" : "bg-zinc-600";
  return (
    <div data-testid="admin-inprogress">
      <div className="space-y-3">
        {view.map((it) => (
          <Link key={`${it.category}-${it.id}`} to={it.link} className="block rounded-lg border border-white/10 bg-white/[0.02] p-3 transition-colors hover:bg-white/[0.05]" data-testid={`inprogress-item-${it.id}`}>
            <div className="mb-1.5 flex items-center justify-between gap-3">
              <div className="min-w-0"><div className="truncate text-sm font-bold">{it.title}</div><div className="text-[11px] text-zinc-500">{it.category} · <span className="text-zinc-400">{it.status_label}</span></div></div>
              <span className="shrink-0 font-display text-sm font-extrabold tabular-nums text-zinc-300">{it.percent}%</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10"><div className={`h-full rounded-full transition-all ${barColor(it.percent)}`} style={{ width: `${it.percent}%` }} /></div>
          </Link>
        ))}
      </div>
      <Pager page={page} pages={pages} setPage={setPage} testid="admin-inprogress-pager" />
    </div>
  );
}

const DONUT = [
  { key: "completed", label: "Completed", color: "#34d399" },
  { key: "in_progress", label: "In Progress", color: "#38bdf8" },
  { key: "open", label: "Open", color: "#a1a1aa" },
  { key: "overdue", label: "Overdue", color: "#fb7185" },
];
function WorkSummary() {
  const { t } = useAppPreferences();
  const [period, setPeriod] = useState("today");
  const [data, setData] = useState(null);
  useEffect(() => { setData(null); api.get("/admin/dashboard/work-summary", { params: { period } }).then((r) => setData(r.data)).catch(() => setData({ total: 0, completed: 0, in_progress: 0, open: 0, overdue: 0 })); }, [period]);
  return (
    <section className="rm-card p-5 h-full flex flex-col" data-testid="admin-work-summary-panel">
      <div className="mb-4 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2"><Icons.BarChart3 className="h-5 w-5 text-[#FF1F8E]" /><div><div className="font-display text-lg font-extrabold tracking-tight">{t("Ringkasan Kerja")}</div><div className="text-xs text-zinc-500">{t("Distribusi tugas")}</div></div></div>
        <select value={period} onChange={(e) => setPeriod(e.target.value)} className="rounded-lg border border-white/10 bg-white/[0.04] px-2.5 py-1 text-xs font-bold text-zinc-200 outline-none focus:border-[#FF1F8E]" data-testid="admin-work-summary-period">
          {PERIODS.map((p) => <option key={p.k} value={p.k} className="bg-zinc-900">{t(p.l)}</option>)}
        </select>
      </div>
      <div className="flex flex-1 items-center"><WorkSummaryChart data={data} /></div>
    </section>
  );
}

function useCountUp(target, duration = 700) {
  const [value, setValue] = useState(0);
  const fromRef = useRef(0);
  useEffect(() => {
    const from = fromRef.current;
    const to = Number(target) || 0;
    if (from === to) return undefined;
    const start = performance.now();
    let raf;
    const tick = (now) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setValue(Math.round(from + (to - from) * eased));
      if (p < 1) raf = requestAnimationFrame(tick); else fromRef.current = to;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);
  return value;
}

function WorkSummaryChart({ data }) {
  const { t } = useAppPreferences();
  const [ready, setReady] = useState(false);
  const [hover, setHover] = useState(null);
  useEffect(() => { setReady(false); const id = requestAnimationFrame(() => setReady(true)); return () => cancelAnimationFrame(id); }, [data]);
  const overdue = data?.overdue || 0;
  const openActive = Math.max(0, (data?.open || 0) - overdue);
  const parts = { completed: data?.completed || 0, in_progress: data?.in_progress || 0, open: openActive, overdue };
  const total = parts.completed + parts.in_progress + parts.open + parts.overdue;
  const animatedTotal = useCountUp(ready ? total : 0);
  if (!data) return <div className="h-40 animate-pulse rounded bg-white/[0.04]" />;
  const R = 52, C = 2 * Math.PI * R;
  let offset = 0;
  const segs = DONUT.map((d) => {
    const val = parts[d.key] || 0;
    const frac = total ? val / total : 0;
    const seg = { ...d, val, pct: total ? Math.round(frac * 100) : 0, dash: frac * C, off: offset };
    offset += frac * C;
    return seg;
  });
  const focus = hover ? segs.find((s) => s.key === hover) : null;
  return (
    <div className="flex w-full flex-col items-center gap-5 sm:flex-row sm:items-center" data-testid="admin-work-summary">
      <div className="relative h-36 w-36 shrink-0">
        <svg viewBox="0 0 140 140" className="h-full w-full -rotate-90">
          <circle cx="70" cy="70" r={R} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="14" />
          {segs.map((s) => s.val > 0 && (
            <circle
              key={s.key} cx="70" cy="70" r={R} fill="none" stroke={s.color}
              strokeWidth={hover === s.key ? 18 : 14}
              strokeDasharray={ready ? `${s.dash} ${C - s.dash}` : `0 ${C}`}
              strokeDashoffset={-s.off} strokeLinecap="butt"
              onMouseEnter={() => setHover(s.key)} onMouseLeave={() => setHover(null)}
              className="cursor-pointer transition-[stroke-dasharray,stroke-width,opacity] duration-700 ease-out"
              style={{ opacity: hover && hover !== s.key ? 0.3 : 1 }}
              data-testid={`work-summary-arc-${s.key}`}
            />
          ))}
        </svg>
        <div className="absolute inset-0 grid place-items-center">
          <div className="text-center transition-transform">
            {focus ? (
              <>
                <div className="font-display text-3xl font-extrabold tabular-nums" style={{ color: focus.color }}>{focus.val}</div>
                <div className="text-[10px] uppercase tracking-widest text-zinc-500">{t(focus.label)}</div>
              </>
            ) : (
              <>
                <div className="font-display text-3xl font-extrabold tabular-nums">{animatedTotal}</div>
                <div className="text-[10px] uppercase tracking-widest text-zinc-500">{t("Total Tugas")}</div>
              </>
            )}
          </div>
        </div>
      </div>
      <div className="w-full space-y-2">
        {segs.map((s) => (
          <div
            key={s.key}
            onMouseEnter={() => setHover(s.key)} onMouseLeave={() => setHover(null)}
            className={`flex items-center justify-between gap-3 rounded-md px-2 py-1 text-sm transition-colors ${hover === s.key ? "bg-white/[0.06]" : ""}`}
            data-testid={`work-summary-${s.key}`}
          >
            <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: s.color }} />{t(s.label)}</span>
            <span className="flex items-center gap-3"><strong className="tabular-nums">{s.val}</strong><span className="w-9 text-right text-xs text-zinc-500">{s.pct}%</span></span>
          </div>
        ))}
      </div>
    </div>
  );
}

function RecentActivity({ selfOnly, userId }) {
  const { t } = useAppPreferences();
  const [items, setItems] = useState(null);
  const [page, setPage] = useState(0);
  useEffect(() => { api.get("/admin/activity-logs", { params: { limit: 60 } }).then((r) => setItems(r.data || [])).catch(() => setItems([])); }, []);
  // Dashboard feed = Work & Finance activity only (system events excluded).
  const all = (items || []).filter((a) => (a.category === "work" || a.category === "finance") && (!selfOnly || a.user_id === userId));
  const pages = Math.ceil(all.length / PAGE_SIZE);
  const rows = all.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);
  return (
    <Panel icon={Activity} title={t("Aktivitas Terbaru")} subtitle={selfOnly ? t("Aktivitas Anda") : t("Kerja & Keuangan")} to="/admin/activity-logs" tint="text-indigo-300" testid="admin-recent-activity">
      {items === null ? <div className="space-y-2">{[0, 1, 2].map((i) => <div key={i} className="h-8 animate-pulse rounded bg-white/[0.04]" />)}</div>
        : rows.length === 0 ? <div className="py-6 text-center text-sm text-zinc-600">{t("Belum ada aktivitas.")}</div>
          : <><ul className="divide-y divide-white/5">
            {rows.map((a) => {
              const link = activityLink(a); const Ico = MODULE_ICON[a.module] || Activity;
              const who = selfOnly ? t("Anda") : (a.user_name || "—");
              const inner = (
                <div className="flex items-start gap-3 py-2.5">
                  <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-md bg-white/5"><Ico className="h-3.5 w-3.5 text-pink-300" /></span>
                  <div className="min-w-0 flex-1"><div className="text-sm text-zinc-200"><span className="font-semibold">{who}</span> <span className="text-zinc-400">{t(humanize(a.action))}</span></div><div className="text-[11px] text-zinc-500">{t(humanize(a.module))}</div></div>
                  <div className="shrink-0 text-[11px] tabular-nums text-zinc-500">{hhmm(a.created_at)}</div>
                </div>
              );
              return <li key={a.id}>{link ? <Link to={link} className="block transition-colors hover:bg-white/[0.03]" data-testid={`admin-activity-item-${a.id}`}>{inner}</Link> : <div data-testid={`admin-activity-item-${a.id}`}>{inner}</div>}</li>;
            })}
          </ul><Pager page={page} pages={pages} setPage={setPage} testid="admin-activity-pager" /></>}
    </Panel>
  );
}

function Trend({ trend }) {
  if (!trend || trend.pct === null || trend.pct === undefined) return <span className="text-[11px] text-zinc-500">—</span>;
  const up = trend.direction === "up"; const flat = trend.direction === "flat";
  const Ico = up ? TrendingUp : TrendingDown;
  const cls = flat ? "text-zinc-400" : up ? "text-emerald-400" : "text-rose-400";
  return <span className={`inline-flex items-center gap-1 text-[11px] font-bold ${cls}`}>{!flat && <Ico className="h-3 w-3" />}{trend.pct > 0 ? "+" : ""}{trend.pct}%</span>;
}

function KpiCard({ icon: Icon, label, value, trend, sub, accent, to, testid }) {
  const c = { rose: "from-rose-500/15 to-rose-500/5 text-rose-300", indigo: "from-indigo-500/15 to-indigo-500/5 text-indigo-300", amber: "from-amber-500/15 to-amber-500/5 text-amber-300", emerald: "from-emerald-500/15 to-emerald-500/5 text-emerald-300", pink: "from-pink-500/15 to-purple-500/15 text-pink-300" }[accent] || "text-zinc-400";
  const inner = (
    <div className="rm-card h-full p-5" data-testid={testid}>
      <div className="flex items-center justify-between"><div className={`grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br ${c}`}><Icon className="h-4 w-4" /></div>{to && <ChevronRight className="h-4 w-4 text-zinc-600" />}</div>
      <div className="mt-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500">{label}</div>
      <div className="mt-1 font-display text-2xl font-extrabold tracking-tighter" data-testid={`${testid}-value`}>{value}</div>
      <div className="mt-1.5 flex items-center gap-2"><Trend trend={trend} />{sub && <span className="text-[11px] text-zinc-500">{sub}</span>}</div>
    </div>
  );
  return to ? <Link to={to}>{inner}</Link> : inner;
}

const KPI_ACCENT = { rose: "from-rose-500/15 to-rose-500/5 text-rose-300", indigo: "from-indigo-500/15 to-indigo-500/5 text-indigo-300", amber: "from-amber-500/15 to-amber-500/5 text-amber-300", emerald: "from-emerald-500/15 to-emerald-500/5 text-emerald-300", pink: "from-pink-500/15 to-purple-500/15 text-pink-300" };

// Money KPI with its own independent period dropdown (Today / This week / This month).
function MoneyKpiCard({ kind, icon: Icon, label, accent = "emerald", sub, testid, nonce, defaultPeriod = "today" }) {
  const { t } = useAppPreferences();
  const [period, setPeriod] = useState(defaultPeriod);
  const [data, setData] = useState(null);
  useEffect(() => {
    let alive = true;
    api.get("/admin/dashboard/money", { params: { kind, period } })
      .then((r) => { if (alive) setData(r.data); })
      .catch(() => { if (alive) setData({ value: 0, trend: null }); });
    return () => { alive = false; };
  }, [kind, period, nonce]);
  const c = KPI_ACCENT[accent] || "text-zinc-400";
  return (
    <div className="rm-card h-full p-5" data-testid={testid}>
      <div className="flex items-center justify-between gap-2">
        <div className={`grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br ${c}`}><Icon className="h-4 w-4" /></div>
        <select value={period} onChange={(e) => setPeriod(e.target.value)} className="rounded-lg border border-white/10 bg-white/[0.04] px-2 py-1 text-[11px] font-bold text-zinc-200 outline-none focus:border-[#FF1F8E]" data-testid={`${testid}-period`}>
          {PERIODS.map((p) => <option key={p.k} value={p.k} className="bg-zinc-900">{t(p.l)}</option>)}
        </select>
      </div>
      <div className="mt-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500">{label}</div>
      <div className="mt-1 font-display text-2xl font-extrabold tracking-tighter" data-testid={`${testid}-value`}>{data ? fmtIDR(data.value) : "…"}</div>
      <div className="mt-1.5 flex items-center gap-2"><Trend trend={data?.trend} />{sub && <span className="text-[11px] text-zinc-500">{sub}</span>}</div>
    </div>
  );
}

export default function AdminDashboard() {
  const { user, hasPermission } = useAuth();
  const { t } = useAppPreferences();
  const [metrics, setMetrics] = useState(null);
  const [nonce, setNonce] = useState(0);
  const [inprog, setInprog] = useState(null);
  const [work, setWork] = useState([]);
  const [team, setTeam] = useState([]);
  const [isManager, setIsManager] = useState(false);
  const name = user?.name || user?.pic_name || user?.email || "Admin";
  const isSuper = user?.role === "super_admin";
  const canWork = hasPermission("work.view");

  const loadWork = useCallback(async () => {
    if (!canWork) return;
    try {
      const { data } = await api.get("/admin/work/queue", { params: { scope: "my" } });
      setWork(data.items || []); setIsManager(!!data.is_manager);
      if (data.is_manager) { try { const { data: td } = await api.get("/admin/work/queue", { params: { scope: "team" } }); setTeam(td.items || []); } catch { /* */ } }
    } catch { /* */ }
  }, [canWork]);

  const loadPeriodData = useCallback(() => {
    api.get("/admin/dashboard/metrics", { params: { period: "month" } }).then((r) => setMetrics(r.data)).catch(() => setMetrics({}));
  }, []);

  const refresh = useCallback(() => {
    loadWork(); loadPeriodData(); setNonce((n) => n + 1);
    api.get("/admin/dashboard/in-progress").then((r) => setInprog(r.data.items || [])).catch(() => setInprog([]));
  }, [loadWork, loadPeriodData]);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => { const iv = setInterval(refresh, 15000); const onN = () => refresh(); window.addEventListener("rilismusik:new-notification", onN); return () => { clearInterval(iv); window.removeEventListener("rilismusik:new-notification", onN); }; }, [refresh]);

  const m = metrics || {};

  return (
    <div className="space-y-6">
      <Greeting name={name} work={work} team={team} isManager={isManager} />

      {canWork && <TodaysFocus work={work} />}

      {canWork && (
        <div className="grid gap-5 lg:grid-cols-2">
          <Panel icon={ClipboardList} title={t("Pekerjaan Saya")} subtitle={`${t("Total")} ${work.reduce((s, w) => s + (w.open_count || 0), 0)} ${t("pekerjaan di antrean Anda")}`} to="/admin/work" testid="admin-my-work">
            <WorkList items={work.filter((w) => w.open_count > 0)} testid="admin-my-work-list" emptyLabel="Tidak ada pekerjaan untuk Anda." />
          </Panel>
          {isManager ? (
            <Panel icon={Users} title={t("Pekerjaan Tim")} subtitle={`${t("Total")} ${team.reduce((s, w) => s + (w.open_count || 0), 0)} ${t("pekerjaan dalam antrean tim")}`} to="/admin/work" tint="text-indigo-300" testid="admin-team-monitor">
              <WorkList items={team.filter((w) => w.open_count > 0)} testid="admin-team-list" emptyLabel="Tidak ada pekerjaan tim terbuka." />
            </Panel>
          ) : (
            <Panel icon={Loader2} title={t("Sedang Dikerjakan")} subtitle={t("Pekerjaan yang sedang berjalan")} to="/admin/work" tint="text-sky-300" testid="admin-inprogress-panel">
              <InProgress items={inprog} />
            </Panel>
          )}
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-3">
        {isManager && <Panel icon={ListChecks} title={t("Sedang Dikerjakan")} subtitle={t("Pekerjaan yang sedang berjalan")} to="/admin/work" tint="text-sky-300" testid="admin-inprogress-panel"><InProgress items={inprog} /></Panel>}
        <div className={isManager ? "h-full" : "lg:col-span-2 h-full"}>
          <WorkSummary />
        </div>
        <RecentActivity selfOnly={!isSuper} userId={user?.id} />
      </div>

      <section data-testid="admin-kpi-section">
        <div className="mb-3 flex items-center justify-between">
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">{t("Ringkasan Platform")}</div>
        </div>
        {metrics === null ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">{Array.from({ length: isSuper ? 7 : 5 }).map((_, i) => <div key={i} className="h-28 animate-pulse rounded-lg border border-white/10 bg-white/[0.03]" />)}</div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            <MoneyKpiCard kind="sales" icon={Wallet} label={t("Sales Revenue")} sub={t("via Xendit")} accent="emerald" nonce={nonce} defaultPeriod="today" testid="kpi-sales-revenue" />
            {isSuper && <MoneyKpiCard kind="withdrawal" icon={Coins} label={t("Requested Withdrawal")} accent="amber" nonce={nonce} defaultPeriod="month" testid="kpi-requested-withdrawal" />}
            {isSuper && <KpiCard icon={Icons.Landmark} label={t("Royalty Income")} value={fmtIDR(m.royalty_income?.value)} trend={m.royalty_income?.trend} sub={m.royalty_income?.period ? `${fmtEUR(m.royalty_income?.eur)} · ${m.royalty_income.period}` : t("impor CSV Believe")} accent="indigo" to="/admin/analytics" testid="kpi-royalty-income" />}
            <KpiCard icon={Building2} label={t("Total Label")} value={fmtNum(m.total_labels?.value)} trend={m.total_labels?.trend} sub={`+${m.total_labels?.added || 0} ${t("Bulan ini")}`} accent="rose" to="/admin/labels" testid={ADMIN_DASHBOARD.totalLabels} />
            <KpiCard icon={Users2} label={t("Total Artist")} value={fmtNum(m.total_artists?.value)} trend={m.total_artists?.trend} sub={`+${m.total_artists?.added || 0} ${t("Bulan ini")}`} accent="indigo" testid="kpi-total-artists" />
            <KpiCard icon={Disc3} label={t("Total Rilis")} value={fmtNum(m.total_releases?.value)} trend={m.total_releases?.trend} sub={`+${m.total_releases?.added || 0} ${t("Bulan ini")}`} accent="amber" to="/admin/releases" testid={ADMIN_DASHBOARD.totalReleases} />
            <KpiCard icon={Crown} label={t("Active Member")} value={fmtNum(m.active_members?.value)} trend={m.active_members?.trend} sub={t("aktivasi akun")} accent="emerald" testid="kpi-active-members" />
          </div>
        )}
      </section>
    </div>
  );
}
