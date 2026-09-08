import React, { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { api, API_BASE, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { useRoyaltyBalance } from "@/hooks/useRoyaltyBalance";
import { Download, Music, Globe2, TrendingUp, Info, BadgeCheck } from "lucide-react";

function fmtIDR(n) { return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0); }

export default function LabelRoyalty() {
  const { user } = useAuth();
  const { balance, error: balanceError } = useRoyaltyBalance(user?.role === "label");
  const [months, setMonths] = useState([]);
  const [period, setPeriod] = useState("");
  const [summary, setSummary] = useState(null);
  const [lines, setLines] = useState([]);
  const [filter, setFilter] = useState({ platform: "", country: "", track_id: "" });
  const [reportArtists, setReportArtists] = useState([]);
  const [reportArtist, setReportArtist] = useState("");
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
    api.get("/royalty/report-artists")
      .then((response) => active && setReportArtists(response.data || []))
      .catch(() => {});
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

  const excelUrl = useMemo(() => {
    const p = new URLSearchParams();
    if (period) p.set("period", period);
    if (reportArtist) p.set("artist", reportArtist);
    return `${API_BASE}/royalty/export.xlsx?${p.toString()}`;
  }, [period, reportArtist]);

  if (!summary) return <div className="text-zinc-500">Memuat…</div>;

  return (
    <div className="space-y-5 max-w-6xl">
      <div className="flex justify-between items-end flex-wrap gap-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Royalti</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter">Laporan Royalti</h1>
          <p className="text-sm text-zinc-400 mt-1">Detail bagian Anda dari laporan Believe (dalam IDR).</p>
        </div>
        <div className="flex gap-2 flex-wrap items-end">
          <select className="rm-input min-w-[140px]" value={period} onChange={(e) => setPeriod(e.target.value)} data-testid="royalty-period-select">
            <option value="">Semua periode</option>
            {months.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
          <select className="rm-input min-w-[150px]" value={reportArtist} onChange={(e) => setReportArtist(e.target.value)} data-testid="royalty-report-artist-select">
            <option value="">Semua artis</option>
            {reportArtists.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
          <a href={excelUrl} className="rm-btn-primary flex items-center gap-2 text-sm" data-testid="royalty-export-excel"><Download className="w-4 h-4" /> Download Excel</a>
          <a href={exportUrl} className="rm-btn-ghost flex items-center gap-2 text-sm" data-testid="royalty-export-csv"><Download className="w-4 h-4" /> Export CSV</a>
        </div>
      </div>
      {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm" data-testid="royalty-error">{err}</div>}

      {user?.role === "label" && <section className="flex flex-wrap items-center justify-between gap-4 border-y border-white/10 py-5" data-testid="royalty-available-section"><div className="min-w-0"><div className="text-xs text-zinc-500">Saldo tersedia</div><div className="mt-1 break-words font-display text-3xl font-bold text-emerald-300" data-testid="royalty-available-balance">{balance ? fmtIDR(balance.balance_available_idr) : "—"}</div>{balanceError && <p role="status" className="mt-1 text-xs text-amber-300" data-testid="royalty-balance-refresh-error">Saldo terbaru belum dapat dimuat.</p>}</div><Link to="/label/withdraw" className="rm-btn-ghost" data-testid="royalty-withdraw-link">Tarik Saldo</Link></section>}

      {months.length === 0 ? (
        <RoyaltyEmptyState claimStatus={user?.claim_status} rejectReason={user?.claim_reject_reason} />
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

function RoyaltyEmptyState({ claimStatus, rejectReason }) {
  if (claimStatus === "pending_link") {
    return (
      <div className="rm-card p-10 text-center" data-testid="royalty-empty-claim-pending">
        <Info className="w-10 h-10 mx-auto mb-3 text-amber-300" />
        <div className="font-display font-bold text-lg text-white">Permintaan klaim sedang ditinjau</div>
        <p className="text-sm mt-2 text-zinc-400 max-w-md mx-auto">Permintaan klaim label lama Anda sedang diproses admin. Royalti Anda akan muncul di sini setelah klaim disetujui dan data periode masuk.</p>
      </div>
    );
  }
  if (claimStatus === "rejected") {
    return (
      <div className="rm-card p-10 text-center" data-testid="royalty-empty-claim-rejected">
        <Info className="w-10 h-10 mx-auto mb-3 text-rose-300" />
        <div className="font-display font-bold text-lg text-white">Royalti belum tersedia bulan ini</div>
        <p className="text-sm mt-2 text-zinc-400 max-w-md mx-auto">Permintaan klaim label Anda belum disetujui{rejectReason ? ` (alasan: ${rejectReason})` : ""}. Data royalti biasanya baru masuk pada bulan berikutnya. Silakan ajukan klaim label kembali untuk mengecek royalti periode berikutnya.</p>
        <Link to="/label/profile" className="rm-btn-primary inline-flex items-center gap-2 mt-5 text-sm" data-testid="royalty-empty-claim-cta"><BadgeCheck className="w-4 h-4" /> Klaim Label</Link>
      </div>
    );
  }
  // Newly registered / not yet claimed (claimStatus undefined) — encourage claim.
  const notLinked = claimStatus !== "linked";
  return (
    <div className="rm-card p-10 text-center" data-testid="royalty-empty-default">
      <Info className="w-10 h-10 mx-auto mb-3 text-sky-300" />
      <div className="font-display font-bold text-lg text-white">Royalti belum tersedia bulan ini</div>
      <p className="text-sm mt-2 text-zinc-400 max-w-md mx-auto">Laporan royalti biasanya masuk pada bulan berikutnya setelah periode berjalan selesai. {notLinked ? "Jika Anda memiliki label lama, silakan klaim label Anda untuk melihat royalti periode sebelumnya dan mengecek royalti di bulan berikutnya." : "Data akan otomatis muncul di sini setelah periode royalti berikutnya masuk."}</p>
      {notLinked && <Link to="/label/profile" className="rm-btn-primary inline-flex items-center gap-2 mt-5 text-sm" data-testid="royalty-empty-claim-cta"><BadgeCheck className="w-4 h-4" /> Klaim Label</Link>}
    </div>
  );
}
