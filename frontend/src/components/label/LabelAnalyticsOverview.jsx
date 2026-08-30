import React from "react";
import { BarChart3, MapPin, Music2, Play, Radio } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const fmtIDR = (value) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(value || 0);
const fmtNumber = (value) => new Intl.NumberFormat("id-ID", { notation: value >= 1_000_000 ? "compact" : "standard", maximumFractionDigits: 1 }).format(value || 0);
const fmtPeriod = (value) => value ? new Date(`${value}-01T00:00:00`).toLocaleDateString("id-ID", { month: "short", year: "numeric" }) : "—";

export function LabelAnalyticsOverview({ analytics }) {
  const { data, loading, error, windowValue, setWindowValue } = analytics;
  return (
    <section className="space-y-5 pt-3" data-testid="label-dashboard-analytics">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><div className="text-xs uppercase tracking-widest text-blue-400 font-bold">Performa Royalti</div><h2 className="font-display text-2xl font-extrabold tracking-normal mt-1">Stream & Pendapatan</h2><p className="text-xs text-zinc-500 mt-1">Data tampil setelah laporan dipublish dan tetap tersedia setelah withdraw.</p></div>
        <div><label className="rm-label">Periode</label><select value={windowValue} onChange={(event) => setWindowValue(event.target.value)} className="rm-input min-w-44 bg-zinc-900" data-testid="label-analytics-window"><option value="latest">Bulan terbaru</option><option value="6">6 bulan</option><option value="12">12 bulan</option></select></div>
      </div>

      {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200" data-testid="label-analytics-error">{error}</div>}
      {loading ? <AnalyticsSkeleton /> : !data?.latest_period ? <EmptyAnalytics /> : (
        <>
          <div className="grid sm:grid-cols-3 border border-white/10 rounded-lg overflow-hidden" data-testid="label-analytics-latest-summary">
            <Metric label="Laporan terbaru" value={fmtPeriod(data.latest_period)} icon={BarChart3} testId="period" />
            <Metric label="Stream laporan terbaru" value={fmtNumber(data.latest_report.streams)} icon={Play} testId="latest-streams" />
            <Metric label="Pendapatan laporan terbaru" value={fmtIDR(data.latest_report.revenue_idr)} icon={Radio} testId="latest-revenue" />
          </div>

          <div className="bg-zinc-900 border border-white/10 rounded-lg p-5 sm:p-6" data-testid="label-analytics-stream-chart">
            <div className="flex flex-wrap justify-between gap-3 mb-5"><div><h3 className="font-display font-bold text-lg tracking-normal">Pertumbuhan Stream</h3><p className="text-xs text-zinc-500 mt-1">{fmtPeriod(data.period_from)} — {fmtPeriod(data.period_to)}</p></div><div className="text-right"><div className="text-xs text-zinc-500">Total periode</div><div className="font-mono tabular-nums font-bold text-blue-300">{fmtNumber(data.totals.streams)} stream</div></div></div>
            <div className="w-full h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.monthly} margin={{ top: 8, right: 4, left: -18, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="period" tickFormatter={fmtPeriod} tick={{ fill: "#71717a", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tickFormatter={fmtNumber} tick={{ fill: "#71717a", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} content={<StreamTooltip />} />
                  <Bar dataKey="streams" fill="#2563EB" radius={[4, 4, 0, 0]} maxBarSize={56} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid lg:grid-cols-3 gap-5">
            <TopList title="Track Teratas" icon={Music2} rows={data.top_tracks} name={(row) => row.title} sub={(row) => row.artist} testId="tracks" />
            <TopList title="Platform Teratas" icon={Radio} rows={data.top_platforms} name={(row) => row.name} testId="platforms" />
            <TopList title="Negara Teratas" icon={MapPin} rows={data.top_countries} name={(row) => row.name} testId="countries" />
          </div>
        </>
      )}
    </section>
  );
}

function Metric({ label, value, icon: Icon, testId }) { return <div className="px-5 py-4 border-r border-b sm:border-b-0 border-white/10 last:border-r-0" data-testid={`label-analytics-metric-${testId}`}><div className="flex items-center gap-2 text-[11px] uppercase tracking-widest text-zinc-500 font-bold"><Icon className="w-3.5 h-3.5 text-blue-400" />{label}</div><div className="text-xl sm:text-2xl font-bold tabular-nums mt-2 text-zinc-50">{value}</div></div>; }
function TopList({ title, icon: Icon, rows, name, sub, testId }) { return <div className="bg-zinc-900 border border-white/10 rounded-lg p-5" data-testid={`label-analytics-top-${testId}`}><h3 className="font-display font-bold tracking-normal flex items-center gap-2"><Icon className="w-4 h-4 text-blue-400" />{title}</h3><div className="mt-4 divide-y divide-white/5">{rows.length ? rows.slice(0, 5).map((row, index) => <div className="py-3 grid grid-cols-[24px_1fr_auto] gap-2 items-center" key={`${name(row)}-${index}`}><span className="font-mono text-xs text-zinc-600">{String(index + 1).padStart(2, "0")}</span><div className="min-w-0"><div className="font-semibold text-sm truncate">{name(row)}</div>{sub && <div className="text-[11px] text-zinc-500 truncate">{sub(row)}</div>}</div><div className="text-right"><div className="font-mono text-xs text-blue-300">{fmtNumber(row.streams)}</div><div className="text-[10px] text-zinc-500">{fmtIDR(row.revenue_idr)}</div></div></div>) : <div className="py-8 text-center text-xs text-zinc-500">Belum ada data laporan</div>}</div></div>; }
function StreamTooltip({ active, payload, label }) { if (!active || !payload?.length) return null; const row = payload[0].payload; return <div className="bg-zinc-950 border border-white/10 rounded-md px-3 py-2 shadow-xl"><div className="text-xs text-zinc-400">{fmtPeriod(label)}</div><div className="text-sm font-bold text-blue-300 mt-1">{fmtNumber(row.streams)} stream</div><div className="text-xs text-emerald-400">{fmtIDR(row.revenue_idr)}</div></div>; }
function AnalyticsSkeleton() { return <div className="space-y-4" data-testid="label-analytics-loading"><div className="h-20 rounded-lg bg-zinc-800 animate-pulse" /><div className="h-72 rounded-lg bg-zinc-800 animate-pulse" /><div className="grid md:grid-cols-3 gap-4"><div className="h-52 rounded-lg bg-zinc-800 animate-pulse" /><div className="h-52 rounded-lg bg-zinc-800 animate-pulse" /><div className="h-52 rounded-lg bg-zinc-800 animate-pulse" /></div></div>; }
function EmptyAnalytics() { return <div className="border border-dashed border-zinc-700 rounded-lg py-14 text-center" data-testid="label-analytics-empty"><BarChart3 className="w-8 h-8 text-zinc-600 mx-auto" /><div className="text-sm text-zinc-400 mt-3">Belum ada data laporan</div><div className="text-xs text-zinc-600 mt-1">Analytics akan muncul setelah laporan dipublish.</div></div>; }