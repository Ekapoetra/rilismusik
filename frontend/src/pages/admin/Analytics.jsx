import React from "react";
import { useAdminAnalytics, fmtPeriod } from "@/hooks/useAdminAnalytics";
import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar, XAxis, YAxis,
  Tooltip, Legend, CartesianGrid,
} from "recharts";
import { RefreshCw, Calendar, Filter, Globe2, Music, Disc3, Building2, Users2, Sparkles, Loader2 } from "lucide-react";

// -- formatting helpers ----------------------------------------------------
const fmtIDR = (n) =>
  new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
const fmtEUR = (n) =>
  "€ " + Number(n || 0).toLocaleString("en-US", { maximumFractionDigits: 2 });
const fmtInt = (n) => Number(n || 0).toLocaleString("id-ID");
export default function AdminAnalytics() {
  const state = useAdminAnalytics();
  return <AnalyticsView {...state} />;
}

function AnalyticsView({ periods, periodFrom, setPeriodFrom, periodTo, setPeriodTo, filters, setFilters, data, loading, err, refreshing, cacheStatus, recompute, monthlyChart }) {
  const kpi = data?.kpi || {};
  const activeFilterCount = Object.values(filters).filter(Boolean).length;

  return (
    <div className="space-y-6" data-testid="admin-analytics-page">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter">Analytics Royalti</h1>
          <div className="text-sm text-zinc-400 mt-1">
            Acuan: <span className="text-zinc-200">kolom bulan laporan</span> (period dari CSV Believe). Cache otomatis ter-update setiap publish royalti baru.
          </div>
        </div>
        <button
          onClick={recompute}
          disabled={refreshing}
          className="rm-btn-ghost flex items-center gap-2 disabled:opacity-60"
          data-testid="analytics-recompute-btn"
          title="Force rebuild monthly_analytics cache dari royalty_lines"
        >
          {refreshing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          {refreshing ? "Recomputing…" : "Rebuild Cache"}
        </button>
      </div>

      {err && (
        <div className="rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-200 px-4 py-3 text-sm" data-testid="analytics-error">
          {err}
        </div>
      )}

      {/* Period range + filter strip */}
      <div className="rm-card p-5 space-y-4">
        <div className="grid md:grid-cols-3 gap-3">
          <div>
            <label className="text-[11px] uppercase tracking-widest font-bold text-zinc-500 flex items-center gap-1.5 mb-1.5">
              <Calendar className="w-3 h-3" /> Dari Bulan Laporan
            </label>
            <select
              value={periodFrom}
              onChange={(e) => setPeriodFrom(e.target.value)}
              className="rm-input w-full"
              data-testid="analytics-period-from"
            >
              {periods.map(p => <option key={p} value={p}>{fmtPeriod(p)}</option>)}
            </select>
          </div>
          <div>
            <label className="text-[11px] uppercase tracking-widest font-bold text-zinc-500 flex items-center gap-1.5 mb-1.5">
              <Calendar className="w-3 h-3" /> Sampai Bulan Laporan
            </label>
            <select
              value={periodTo}
              onChange={(e) => setPeriodTo(e.target.value)}
              className="rm-input w-full"
              data-testid="analytics-period-to"
            >
              {periods.map(p => <option key={p} value={p}>{fmtPeriod(p)}</option>)}
            </select>
          </div>
          <div>
            <label className="text-[11px] uppercase tracking-widest font-bold text-zinc-500 mb-1.5 block">Quick Range</label>
            <div className="flex gap-2 flex-wrap">
              <QuickRangeButton label="12 Bulan Terakhir" periods={periods} months={12} setFrom={setPeriodFrom} setTo={setPeriodTo} />
              <QuickRangeButton label="Tahun Ini" periods={periods} ytd setFrom={setPeriodFrom} setTo={setPeriodTo} />
              <QuickRangeButton label="Semua" periods={periods} all setFrom={setPeriodFrom} setTo={setPeriodTo} />
            </div>
          </div>
        </div>

        <FilterRow data={data} filters={filters} setFilters={setFilters} />
        {activeFilterCount > 0 && (
          <div className="flex items-center justify-between text-xs">
            <span className="text-amber-300 flex items-center gap-1.5">
              <Filter className="w-3 h-3" /> {activeFilterCount} filter aktif — data dihitung live dari royalty_lines (slow path)
            </span>
            <button
              onClick={() => setFilters({ label_id: "", platform: "", country: "", artist_id: "", track_id: "" })}
              className="text-zinc-400 hover:text-white"
              data-testid="analytics-clear-filters"
            >Clear semua</button>
          </div>
        )}
      </div>

      {/* KPI Tiles */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <KPI label="Revenue IDR" value={fmtIDR(kpi.total_revenue_idr)} accent="emerald" loading={loading} testId="analytics-kpi-idr" />
        <KPI label="Pendapatan Kotor EUR" value={fmtEUR(kpi.total_revenue_eur)} accent="indigo" loading={loading} testId="analytics-kpi-eur" />
        <KPI label="Total Stream" value={fmtInt(kpi.total_quantity)} accent="amber" loading={loading} testId="analytics-kpi-streams" />
        <KPI label="Platform Aktif" value={fmtInt(kpi.distinct_platforms)} accent="rose" loading={loading} />
        <KPI label="Negara Aktif" value={fmtInt(kpi.distinct_countries)} accent="orange" loading={loading} />
        <KPI label="Track Aktif" value={fmtInt(kpi.distinct_tracks)} accent="emerald" loading={loading} />
      </div>

      {/* Revenue line chart */}
      <div className="rm-card p-5">
        <div className="text-xs uppercase tracking-widest font-bold text-zinc-500 mb-4 flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5" /> Pendapatan per Bulan Laporan
        </div>
        <div className="h-72">
          {monthlyChart.length === 0 ? (
            <Empty loading={loading} message="Belum ada data di rentang ini" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={monthlyChart}>
                <defs>
                  <linearGradient id="grad-idr" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#10b981" />
                    <stop offset="100%" stopColor="#34d399" />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
                <XAxis dataKey="label" tick={{ fill: "#a1a1aa", fontSize: 11 }} />
                <YAxis
                  yAxisId="idr"
                  orientation="left"
                  tick={{ fill: "#10b981", fontSize: 11 }}
                  tickFormatter={(v) => v >= 1_000_000 ? `${(v / 1_000_000).toFixed(1)}M` : v >= 1_000 ? `${(v / 1_000).toFixed(0)}K` : v}
                />
                <YAxis
                  yAxisId="eur"
                  orientation="right"
                  tick={{ fill: "#818cf8", fontSize: 11 }}
                  tickFormatter={(v) => v >= 1_000 ? `${(v / 1_000).toFixed(1)}K` : v}
                />
                <Tooltip
                  contentStyle={{ background: "#0a0a0a", border: "1px solid #262626", borderRadius: 12, fontSize: 12 }}
                  formatter={(value, name) => name === "IDR" ? [fmtIDR(value), "Revenue IDR"] : [fmtEUR(value), "Revenue EUR"]}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line yAxisId="idr" type="monotone" dataKey="IDR" stroke="url(#grad-idr)" strokeWidth={2.5} dot={{ r: 3, fill: "#10b981" }} activeDot={{ r: 5 }} />
                <Line yAxisId="eur" type="monotone" dataKey="EUR" stroke="#818cf8" strokeWidth={2.5} strokeDasharray="4 4" dot={{ r: 3, fill: "#818cf8" }} activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Top tables — 2-column grid */}
      <div className="grid md:grid-cols-2 gap-4">
        <TopList title="Top 10 Platform" icon={Globe2} accent="rose" rows={data?.top_platforms || []} loading={loading} testId="analytics-top-platforms" onClick={(k) => setFilters((f) => ({ ...f, platform: k }))} />
        <TopList title="Top 10 Negara" icon={Globe2} accent="indigo" rows={data?.top_countries || []} loading={loading} testId="analytics-top-countries" onClick={(k) => setFilters((f) => ({ ...f, country: k }))} />
        <TopList title="Top 10 Label" icon={Building2} accent="emerald" rows={data?.top_labels || []} loading={loading} testId="analytics-top-labels" onClick={(k) => setFilters((f) => ({ ...f, label_id: k }))} />
        <TopList title="Top 10 Artist" icon={Users2} accent="amber" rows={data?.top_artists || []} loading={loading} testId="analytics-top-artists" onClick={(k) => setFilters((f) => ({ ...f, artist_id: k }))} />
        <TopList title="Top 10 Track" icon={Music} accent="orange" rows={data?.top_tracks || []} loading={loading} testId="analytics-top-tracks" extraSubLabel="(klik untuk filter)" onClick={(k) => setFilters((f) => ({ ...f, track_id: k }))} />
        <div className="rm-card p-5">
          <div className="text-xs uppercase tracking-widest font-bold text-zinc-500 mb-3 flex items-center gap-2">
            <Disc3 className="w-3.5 h-3.5" /> Status Cache
          </div>
          <div className="text-sm space-y-2">
            <div className="flex justify-between"><span className="text-zinc-500">Sumber data</span><span className="text-zinc-200 font-mono text-xs">{data?.source || "—"}</span></div>
            <div className="flex justify-between"><span className="text-zinc-500">Cache update</span><span className="text-zinc-200 font-mono text-xs">{cacheStatus?.finished_at ? new Date(cacheStatus.finished_at).toLocaleString("id-ID") : "Belum pernah"}</span></div>
            <div className="flex justify-between"><span className="text-zinc-500">Durasi recompute</span><span className="text-zinc-200 font-mono text-xs">{cacheStatus?.duration_sec ? `${cacheStatus.duration_sec}s` : "—"}</span></div>
            <div className="flex justify-between"><span className="text-zinc-500">Doc count</span><span className="text-zinc-200 font-mono text-xs">{fmtInt(cacheStatus?.doc_count || 0)}</span></div>
            {cacheStatus?.per_dim_counts && Object.keys(cacheStatus.per_dim_counts).length > 0 && (
              <div className="pt-2 mt-2 border-t border-white/5 space-y-1">
                <div className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">Per Dimensi</div>
                {Object.entries(cacheStatus.per_dim_counts).map(([dim, n]) => (
                  <div key={dim} className="flex justify-between text-xs">
                    <span className="text-zinc-500 capitalize">{dim}</span>
                    <span className="text-zinc-300 font-mono">{fmtInt(n)}</span>
                  </div>
                ))}
              </div>
            )}
            {cacheStatus?.last_error && (
              <div className="bg-red-500/10 border border-red-500/30 text-red-200 rounded p-2 text-[11px] mt-2">
                <div className="font-semibold mb-0.5">Last error</div>
                <div className="font-mono break-all">{cacheStatus.last_error}</div>
              </div>
            )}
            <div className="text-[10px] text-zinc-500 mt-3 leading-relaxed">
              Cache di-rebuild otomatis setelah publish royalti, hapus import, & backfill Bulan Laporan. Klik &quot;Rebuild Cache&quot; untuk paksa update sekarang.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function QuickRangeButton({ label, periods, months, ytd, all, setFrom, setTo }) {
  const apply = () => {
    if (periods.length === 0) return;
    if (all) {
      setFrom(periods[0]);
      setTo(periods[periods.length - 1]);
      return;
    }
    if (ytd) {
      const max = periods[periods.length - 1];
      const yr = max.split("-")[0];
      const ytdFrom = periods.find(p => p.startsWith(yr)) || periods[0];
      setFrom(ytdFrom);
      setTo(max);
      return;
    }
    if (months) {
      const max = periods[periods.length - 1];
      const [y, m] = max.split("-").map(Number);
      const d = new Date(Date.UTC(y, m - 1, 1));
      d.setUTCMonth(d.getUTCMonth() - (months - 1));
      const fromStr = `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
      setFrom(periods.includes(fromStr) ? fromStr : periods[0]);
      setTo(max);
    }
  };
  return (
    <button onClick={apply} className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs font-semibold text-zinc-300 transition" data-testid={`analytics-quick-${label.toLowerCase().replace(/\s+/g, '-')}`}>
      {label}
    </button>
  );
}

function FilterRow({ data, filters, setFilters }) {
  // populate options from current top lists (already loaded → no extra fetch)
  const opts = {
    platform: (data?.top_platforms || []).map(t => ({ key: t.key, name: t.name })),
    country: (data?.top_countries || []).map(t => ({ key: t.key, name: t.name })),
    label_id: (data?.top_labels || []).map(t => ({ key: t.key, name: t.name })),
    artist_id: (data?.top_artists || []).map(t => ({ key: t.key, name: t.name })),
    track_id: (data?.top_tracks || []).map(t => ({ key: t.key, name: t.name })),
  };
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
      <FilterSelect label="Label" value={filters.label_id} setValue={(v) => setFilters({ ...filters, label_id: v })} options={opts.label_id} testId="analytics-filter-label" />
      <FilterSelect label="Platform" value={filters.platform} setValue={(v) => setFilters({ ...filters, platform: v })} options={opts.platform} testId="analytics-filter-platform" />
      <FilterSelect label="Negara" value={filters.country} setValue={(v) => setFilters({ ...filters, country: v })} options={opts.country} testId="analytics-filter-country" />
      <FilterSelect label="Artist" value={filters.artist_id} setValue={(v) => setFilters({ ...filters, artist_id: v })} options={opts.artist_id} testId="analytics-filter-artist" />
      <FilterSelect label="Track" value={filters.track_id} setValue={(v) => setFilters({ ...filters, track_id: v })} options={opts.track_id} testId="analytics-filter-track" />
    </div>
  );
}

function FilterSelect({ label, value, setValue, options, testId }) {
  return (
    <div>
      <label className="text-[10px] uppercase tracking-widest font-bold text-zinc-500 mb-1 block">{label}</label>
      <select
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="rm-input w-full text-xs"
        data-testid={testId}
      >
        <option value="">— Semua —</option>
        {options.map(o => <option key={o.key} value={o.key}>{o.name?.length > 32 ? o.name.slice(0, 32) + "…" : o.name}</option>)}
      </select>
    </div>
  );
}

function KPI({ label, value, accent, loading, testId }) {
  const c = {
    emerald: "from-emerald-500/15 to-emerald-500/5 text-emerald-300",
    indigo: "from-indigo-500/15 to-indigo-500/5 text-indigo-300",
    amber: "from-amber-500/15 to-amber-500/5 text-amber-300",
    rose: "from-rose-500/15 to-rose-500/5 text-rose-300",
    orange: "from-pink-500/15 to-purple-500/15 text-pink-300",
  }[accent] || "from-slate-50 to-slate-100 text-zinc-400";
  return (
    <div className={`rm-card p-4 bg-gradient-to-br ${c}`} data-testid={testId}>
      <div className="text-[10px] uppercase tracking-widest font-bold text-zinc-500">{label}</div>
      <div className="font-display font-extrabold tracking-tighter text-xl mt-1.5">
        {loading ? <span className="text-zinc-600">…</span> : value}
      </div>
    </div>
  );
}

function TopList({ title, icon: Icon, accent, rows, loading, testId, onClick, extraSubLabel }) {
  const max = rows.length > 0 ? Math.max(...rows.map(r => r.revenue_idr || 0)) : 0;
  const c = {
    emerald: "text-emerald-300", indigo: "text-indigo-300", amber: "text-amber-300", rose: "text-rose-300", orange: "text-pink-300",
  }[accent] || "text-zinc-300";
  return (
    <div className="rm-card p-5" data-testid={testId}>
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs uppercase tracking-widest font-bold text-zinc-500 flex items-center gap-2">
          <Icon className={`w-3.5 h-3.5 ${c}`} />
          {title}
          {extraSubLabel && <span className="text-[9px] text-zinc-600 normal-case font-normal">{extraSubLabel}</span>}
        </div>
      </div>
      {loading ? (
        <Empty loading={true} />
      ) : rows.length === 0 ? (
        <Empty loading={false} message="Tidak ada data di rentang ini" />
      ) : (
        <ul className="space-y-1.5">
          {rows.map((r, i) => (
            <li key={r.key || `${r.name}-${r.revenue_idr}`} className="group">
              <button
                onClick={() => onClick && r.key && onClick(r.key)}
                className="w-full flex items-center gap-2 text-left hover:bg-white/5 -mx-2 px-2 py-1.5 rounded-lg transition"
                data-testid={`${testId}-row-${i}`}
                disabled={!onClick || !r.key}
              >
                <span className="text-[10px] font-mono text-zinc-600 w-6 text-right">{i + 1}.</span>
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-zinc-200 truncate font-medium">{r.name || "(unknown)"}</div>
                  <div className="h-1 rounded-full bg-white/5 mt-1 overflow-hidden">
                    <div className={`h-full bg-gradient-to-r ${accent === "emerald" ? "from-emerald-500 to-emerald-400" : accent === "indigo" ? "from-indigo-500 to-indigo-400" : accent === "amber" ? "from-amber-500 to-amber-400" : accent === "rose" ? "from-rose-500 to-rose-400" : "from-pink-500 to-purple-500"}`}
                         style={{ width: `${max > 0 ? (r.revenue_idr / max) * 100 : 0}%` }} />
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-[11px] font-mono font-bold text-zinc-100">{fmtIDR(r.revenue_idr)}</div>
                  <div className="text-[9px] text-zinc-500">{fmtInt(r.lines)} baris</div>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Empty({ loading, message }) {
  if (loading) return <div className="flex items-center gap-2 text-zinc-500 text-xs py-8 justify-center"><Loader2 className="w-4 h-4 animate-spin" /> Memuat…</div>;
  return <div className="text-zinc-600 text-xs text-center py-8">{message || "—"}</div>;
}
