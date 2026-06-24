import React, { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { api, formatApiError } from "@/api/client";

function fmtIDR(n) { return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0); }
function fmtEUR(n) { return new Intl.NumberFormat("en-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 2 }).format(n || 0); }

export default function AdminRoyaltyDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try { const { data } = await api.get(`/royalty/admin/imports/${id}`); setData(data); }
    catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const publish = async () => {
    setBusy(true); setErr(""); setMsg("");
    try { await api.post(`/royalty/admin/imports/${id}/publish`, { confirm: true }); setMsg("Royalti dipublish — saldo pending bertambah ke label."); load(); }
    catch (e) { setErr(formatApiError(e.response?.data?.detail)); } finally { setBusy(false); }
  };
  const markDana = async () => {
    setBusy(true); setErr(""); setMsg("");
    try { await api.post(`/royalty/admin/imports/${id}/mark-dana-received`); setMsg("Dana ditandai diterima — saldo pending dipindah ke tersedia."); load(); }
    catch (e) { setErr(formatApiError(e.response?.data?.detail)); } finally { setBusy(false); }
  };

  if (!data) return <div className="text-slate-500">Memuat…</div>;
  const { import: imp, lines, per_label } = data;

  return (
    <div className="space-y-5">
      <Link to="/admin/royalty" className="text-sm text-slate-600 hover:text-[#FF3B30]">← Royalty Imports</Link>
      <div className="flex justify-between items-start flex-wrap gap-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-slate-500 font-bold">Royalty Import</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter">Periode {imp.period}</h1>
          <div className="text-sm text-slate-600">File: {imp.filename} • Kurs: Rp {imp.exchange_rate_eur_idr?.toLocaleString("id-ID")} / €1 • Fee distributor: {imp.fee_percent}%</div>
        </div>
        <div className="flex gap-2 flex-wrap">
          {imp.status === "pending_review" && <button className="rm-btn-primary" disabled={busy} onClick={publish} data-testid="admin-royalty-publish">Publish (kredit ke pending)</button>}
          {imp.status === "published" && <button className="rm-btn-primary" disabled={busy} onClick={markDana} data-testid="admin-royalty-mark-dana">Tandai Dana Diterima</button>}
          {imp.status === "dana_received" && <span className="px-3 py-2 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700">✓ Dana sudah diterima</span>}
        </div>
      </div>

      {err && <div className="rounded-2xl bg-red-50 text-red-700 px-4 py-3 text-sm">{err}</div>}
      {msg && <div className="rounded-2xl bg-emerald-50 text-emerald-700 px-4 py-3 text-sm">{msg}</div>}

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card label="Total Lines" v={imp.total_lines} />
        <Card label="Matched" v={imp.matched_lines} accent="emerald" />
        <Card label="Unmatched" v={imp.unmatched_lines} accent="amber" />
        <Card label="Total Revenue" v={fmtEUR(imp.total_revenue_eur)} />
        <Card label="Bagian Label" v={fmtIDR(imp.total_label_idr)} accent="rose" />
      </div>

      <div className="rm-card p-5">
        <h3 className="font-display font-bold text-lg tracking-tight mb-3">Breakdown per Label</h3>
        {per_label?.length === 0 ? <div className="text-sm text-slate-500">Belum ada line matched.</div> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-[11px] uppercase tracking-widest text-slate-500"><th className="py-2">Label</th><th>Lines</th><th>Revenue EUR</th><th className="text-right">Bagian IDR</th></tr></thead>
              <tbody>
                {per_label.map((r) => (
                  <tr key={r._id} className="border-t border-slate-100">
                    <td className="py-2 font-semibold">{r.label?.label_name || r._id}</td>
                    <td>{r.lines}</td>
                    <td>{fmtEUR(r.total_eur)}</td>
                    <td className="text-right font-bold">{fmtIDR(r.total_idr)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="rm-card p-5">
        <h3 className="font-display font-bold text-lg tracking-tight mb-3">Lines (top 100)</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead><tr className="text-left text-[10px] uppercase tracking-widest text-slate-500">
              <th className="py-2">ISRC</th><th>Track</th><th>Artist</th><th>Platform</th><th>Country</th><th>Streams</th><th>Revenue EUR</th><th>Match</th><th className="text-right">Label IDR</th>
            </tr></thead>
            <tbody>
              {lines.slice(0, 100).map((l) => (
                <tr key={l.id} className="border-t border-slate-100">
                  <td className="py-2 font-mono text-[10px]">{l.isrc || "—"}</td>
                  <td className="font-semibold truncate max-w-[150px]">{l.track_title_raw}</td>
                  <td className="truncate max-w-[120px]">{l.artist_name_raw}</td>
                  <td>{l.platform}</td>
                  <td>{l.country}</td>
                  <td>{l.quantity?.toLocaleString("id-ID")}</td>
                  <td>{fmtEUR(l.revenue_eur)}</td>
                  <td><span className={`text-[10px] font-bold ${l.match_status === "matched" || l.match_status === "manually_matched" ? "text-emerald-700" : "text-amber-700"}`}>{l.match_status}</span></td>
                  <td className="text-right font-semibold">{fmtIDR(l.label_idr)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
function Card({ label, v, accent }) {
  const cls = { emerald: "text-emerald-700", amber: "text-amber-700", rose: "text-rose-700" }[accent] || "";
  return <div className="rm-card p-4"><div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">{label}</div><div className={`font-display text-2xl font-extrabold tracking-tighter mt-1 ${cls}`}>{v}</div></div>;
}
