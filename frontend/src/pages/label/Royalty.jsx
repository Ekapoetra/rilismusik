import React, { useEffect, useState, useMemo } from "react";
import { api, API_BASE, formatApiError } from "@/api/client";
import { Download, Music, Globe2, TrendingUp } from "lucide-react";

function fmtIDR(n) { return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0); }

export default function LabelRoyalty() {
  const [months, setMonths] = useState([]);
  const [period, setPeriod] = useState("");
  const [summary, setSummary] = useState(null);
  const [lines, setLines] = useState([]);
  const [filter, setFilter] = useState({ platform: "", country: "", track_id: "" });
  const [err, setErr] = useState("");

  useEffect(() => {
    let active = true;
    api.get("/royalty/months")
      .then((response) => {
        if (!active) return;
        setMonths(response.data);
        setPeriod((current) => current || response.data[0] || "");
      })
      .catch((error) => active && setErr(formatApiError(error.response?.data?.detail)));
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    const params = { period: period || undefined, ...Object.fromEntries(Object.entries(filter).filter(([, value]) => value)) };
    Promise.all([
      api.get("/royalty/summary", { params: { period: period || undefined } }),
      api.get("/royalty/lines", { params }),
    ]).then(([summaryResponse, linesResponse]) => {
      if (!active) return;
      setSummary(summaryResponse.data);
      setLines(linesResponse.data);
      setErr("");
    }).catch((error) => active && setErr(formatApiError(error.response?.data?.detail)));
    return () => { active = false; };
  }, [period, filter]);

  const exportUrl = useMemo(() => {
    const p = new URLSearchParams();
    if (period) p.set("period", period);
    return `${API_BASE}/royalty/export.csv?${p.toString()}`;
  }, [period]);

  if (!summary) return <div className="text-zinc-500">Memuat…</div>;

  return (
    <div className="space-y-5 max-w-6xl">
      <div className="flex justify-between items-end flex-wrap gap-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Royalti</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter">Laporan Royalti</h1>
          <p className="text-sm text-zinc-400 mt-1">Detail bagian Anda dari laporan Believe (dalam IDR).</p>
        </div>
        <div className="flex gap-2">
          <select className="rm-input min-w-[140px]" value={period} onChange={(e) => setPeriod(e.target.value)} data-testid="royalty-period-select">
            <option value="">Semua periode</option>
            {months.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
          <a href={exportUrl} className="rm-btn-ghost flex items-center gap-2 text-sm" data-testid="royalty-export-csv"><Download className="w-4 h-4" /> Export CSV</a>
        </div>
      </div>
      {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm" data-testid="royalty-error">{err}</div>}

      {months.length === 0 ? (
        <div className="rm-card p-10 text-center text-zinc-500">
          <Music className="w-10 h-10 mx-auto mb-3 text-zinc-700" />
          <div className="font-display font-bold text-lg">Belum ada data royalti</div>
          <p className="text-sm mt-1">Data royalti akan muncul setelah admin upload CSV Believe dan publish.</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <Card label="Total Royalti" v={fmtIDR(summary.summary.total_idr)} accent="rose" />
            <Card label="Total Streams" v={summary.summary.total_streams?.toLocaleString("id-ID")} accent="indigo" icon={TrendingUp} />
            <Card label="Total Lines" v={summary.summary.total_lines} icon={Music} />
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <Panel title="Per Platform" icon={Music}>
              {summary.by_platform.length === 0 ? <Empty /> : summary.by_platform.map((p) => (
                <Row key={p.platform || "unknown-platform"} k={p.platform} v={fmtIDR(p.total_idr)} sub={`${p.streams?.toLocaleString("id-ID")} streams`} />
              ))}
            </Panel>
            <Panel title="Top Country" icon={Globe2}>
              {summary.by_country.length === 0 ? <Empty /> : summary.by_country.map((c) => (
                <Row key={c.country || "unknown-country"} k={c.country} v={fmtIDR(c.total_idr)} />
              ))}
            </Panel>
          </div>

          <div className="rm-card p-5">
            <div className="flex justify-between items-center mb-3">
              <h3 className="font-display font-bold text-lg tracking-tight">Top Tracks</h3>
            </div>
            {summary.by_track.length === 0 ? <Empty /> : (
              <table className="w-full text-sm">
                <thead><tr className="text-left text-[11px] uppercase tracking-widest text-zinc-500"><th className="py-2">#</th><th>Track</th><th>Streams</th><th className="text-right">Royalti IDR</th></tr></thead>
                <tbody>
                  {summary.by_track.map((t, i) => (
                    <tr key={`${t.isrc || "no-isrc"}-${t.title || "untitled"}`} className="border-t border-white/5">
                      <td className="py-2 text-zinc-600">{i + 1}</td>
                      <td className="font-semibold truncate max-w-[260px]">{t.title}</td>
                      <td>{t.streams?.toLocaleString("id-ID")}</td>
                      <td className="text-right font-bold">{fmtIDR(t.total_idr)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Filter + table */}
          <div className="rm-card p-5">
            <div className="flex justify-between items-center mb-3 flex-wrap gap-2">
              <h3 className="font-display font-bold text-lg tracking-tight">Detail Lines ({lines.length})</h3>
              <div className="flex gap-2 flex-wrap">
                <input className="rm-input text-sm" placeholder="Platform…" value={filter.platform} onChange={(e) => setFilter({ ...filter, platform: e.target.value })} data-testid="royalty-filter-platform" />
                <input className="rm-input text-sm" placeholder="Country (ID/US/…)" value={filter.country} onChange={(e) => setFilter({ ...filter, country: e.target.value })} data-testid="royalty-filter-country" />
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead><tr className="text-left text-[10px] uppercase tracking-widest text-zinc-500">
                  <th className="py-2">Periode</th><th>Track</th><th>Artist</th><th>Platform</th><th>Country</th><th>Streams</th><th>Status</th><th className="text-right">Royalti IDR</th>
                </tr></thead>
                <tbody>
                  {lines.slice(0, 200).map((l) => (
                    <tr key={l.id} className="border-t border-white/5">
                      <td className="py-2">{l.period}</td>
                      <td className="font-semibold truncate max-w-[160px]">{l.track_title_raw || "—"}</td>
                      <td className="truncate max-w-[120px]">{l.artist_name_raw}</td>
                      <td>{l.platform || "—"}</td>
                      <td>{l.country || "—"}</td>
                      <td>{l.quantity?.toLocaleString("id-ID")}</td>
                      <td><span className={`text-[10px] font-bold ${l.status === "available" ? "text-emerald-300" : l.status === "withdrawn" ? "text-zinc-500" : "text-amber-300"}`}>{l.status}</span></td>
                      <td className="text-right font-bold">{fmtIDR(l.label_idr)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {lines.length > 200 && <div className="text-xs text-zinc-500 text-center mt-3">Menampilkan 200 lines pertama. Export CSV untuk data lengkap.</div>}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
function Card({ label, v, accent, icon: Icon }) {
  const cls = { rose: "text-rose-300", indigo: "text-indigo-300" }[accent] || "";
  return <div className="rm-card p-5">
    <div className="flex justify-between items-start"><div className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold">{label}</div>{Icon && <Icon className="w-4 h-4 text-zinc-600" />}</div>
    <div className={`font-display text-2xl md:text-3xl font-extrabold tracking-tighter mt-2 ${cls}`}>{v}</div>
  </div>;
}
function Panel({ title, icon: Icon, children }) {
  return <div className="rm-card p-5"><div className="flex items-center gap-2 mb-3"><Icon className="w-4 h-4 text-zinc-600" /><h3 className="font-display font-bold tracking-tight">{title}</h3></div>{children}</div>;
}
function Row({ k, v, sub }) {
  return <div className="flex justify-between items-center py-1.5 border-b border-white/5 last:border-0"><div className="text-sm">{k}{sub && <div className="text-[10px] text-zinc-500">{sub}</div>}</div><div className="font-bold text-sm">{v}</div></div>;
}
function Empty() { return <div className="text-sm text-zinc-500 py-4">Belum ada data.</div>; }
