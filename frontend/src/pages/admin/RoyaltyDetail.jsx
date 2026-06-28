import React, { useEffect, useRef, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { Loader2, RefreshCw, XCircle } from "lucide-react";

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

  // Auto-poll every 3s while status is processing OR publishing
  const pollRef = useRef(null);
  useEffect(() => {
    const inFlight = data?.import?.status === "processing" || data?.import?.status === "publishing";
    if (inFlight && !pollRef.current) {
      pollRef.current = setInterval(load, 3000);
    } else if (!inFlight && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
    // eslint-disable-next-line
  }, [data?.import?.status]);

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
  const retry = async () => {
    setBusy(true); setErr(""); setMsg("");
    try { await api.post(`/royalty/admin/imports/${id}/retry`); setMsg("Retry dijadwalkan — refresh otomatis akan menampilkan progress."); load(); }
    catch (e) { setErr(formatApiError(e.response?.data?.detail)); } finally { setBusy(false); }
  };

  if (!data) return <div className="text-zinc-500">Memuat…</div>;
  const { import: imp, lines, per_label } = data;

  return (
    <div className="space-y-5">
      <Link to="/admin/royalty" className="text-sm text-zinc-400 hover:rm-gradient-text">← Royalty Imports</Link>
      <div className="flex justify-between items-start flex-wrap gap-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Royalty Import</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter">Periode {imp.period}</h1>
          <div className="text-sm text-zinc-400">File: {imp.filename} • Kurs: Rp {imp.exchange_rate_eur_idr?.toLocaleString("id-ID")} / €1 • Fee distributor: {imp.fee_percent}%</div>
        </div>
        <div className="flex gap-2 flex-wrap">
          {imp.status === "processing" && (
            <span className="px-3 py-2 rounded-full text-xs font-bold bg-sky-500/15 text-sky-300 flex items-center gap-2" data-testid="royalty-detail-status-processing">
              <Loader2 className="w-3 h-3 animate-spin" /> Processing… {imp.progress_pct || 0}%
            </span>
          )}
          {imp.status === "publishing" && (
            <span className="px-3 py-2 rounded-full text-xs font-bold bg-violet-500/15 text-violet-300 flex items-center gap-2" data-testid="royalty-detail-status-publishing">
              <Loader2 className="w-3 h-3 animate-spin" /> Publishing… {imp.publish_progress_pct || imp.progress_pct || 0}%
            </span>
          )}
          {(imp.status === "processing" || imp.status === "error") && (
            <button className="rm-btn-ghost flex items-center gap-2" disabled={busy} onClick={retry} data-testid="admin-royalty-retry">
              <RefreshCw className="w-4 h-4" /> Retry
            </button>
          )}
          {(imp.status === "pending_review" || imp.status === "publish_error") && (
            <button className="rm-btn-primary" disabled={busy} onClick={publish} data-testid="admin-royalty-publish">
              {imp.status === "publish_error" ? "Coba Publish Lagi" : "Publish (kredit ke pending)"}
            </button>
          )}
          {imp.status === "published" && <button className="rm-btn-primary" disabled={busy} onClick={markDana} data-testid="admin-royalty-mark-dana">Tandai Dana Diterima</button>}
          {imp.status === "dana_received" && <span className="px-3 py-2 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-300">✓ Dana sudah diterima</span>}
        </div>
      </div>

      {imp.status === "processing" && (
        <div className="rm-card p-5 space-y-3" data-testid="royalty-detail-progress">
          <div className="flex justify-between items-center text-sm">
            <span className="text-zinc-400">Memproses CSV di background…</span>
            <span className="font-bold text-sky-300">{imp.progress_pct || 0}%</span>
          </div>
          <div className="h-2 rounded-full bg-white/10 overflow-hidden">
            <div className="h-full bg-gradient-to-r from-sky-400 to-violet-400 transition-all" style={{ width: `${imp.progress_pct || 0}%` }} />
          </div>
          <div className="text-[11px] text-zinc-500">
            {(imp.processed_lines || 0).toLocaleString("id-ID")} baris diproses • {(imp.matched_lines || 0).toLocaleString("id-ID")} matched • {(imp.auto_created_labels || 0)} label / {(imp.auto_created_tracks || 0)} track baru auto-dibuat
          </div>
          <div className="text-[11px] text-zinc-500">Auto-refresh setiap 3 detik. Jika container restart, processing akan otomatis dilanjutkan saat backend start kembali.</div>
        </div>
      )}

      {imp.status === "publishing" && (
        <div className="rm-card p-5 space-y-3" data-testid="royalty-detail-publish-progress">
          <div className="flex justify-between items-center text-sm">
            <span className="text-zinc-400">Memublish royalti ke saldo label di background…</span>
            <span className="font-bold text-violet-300">{imp.publish_progress_pct || imp.progress_pct || 0}%</span>
          </div>
          <div className="h-2 rounded-full bg-white/10 overflow-hidden">
            <div className="h-full bg-gradient-to-r from-violet-400 to-fuchsia-400 transition-all" style={{ width: `${imp.publish_progress_pct || imp.progress_pct || 0}%` }} />
          </div>
          <div className="text-[11px] text-zinc-500">
            Mengkredit saldo pending untuk setiap label. Proses ini <strong>idempotent</strong> — aman untuk di-retry.
            Auto-refresh setiap 3 detik. Jika container restart, publish akan otomatis dilanjutkan.
          </div>
        </div>
      )}

      {(imp.status === "error" || imp.status === "publish_error") && imp.error_message && (
        <div className="rounded-2xl bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-200 flex items-start gap-3" data-testid="royalty-detail-error-banner">
          <XCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <div className="font-bold">{imp.status === "publish_error" ? "Publish gagal" : "Import gagal"}</div>
            <div className="text-red-200/80 mt-1">{imp.error_message}</div>
            <div className="text-[11px] text-red-200/60 mt-1">
              {imp.status === "publish_error"
                ? "Klik tombol \"Coba Publish Lagi\" di atas — proses idempotent, label yang sudah dikredit tidak akan didouble."
                : "Klik Retry jika file CSV masih ada di server, atau upload ulang."}
            </div>
          </div>
        </div>
      )}

      {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm">{err}</div>}
      {msg && <div className="rounded-2xl bg-emerald-500/15 text-emerald-300 px-4 py-3 text-sm">{msg}</div>}

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card label="Total Lines" v={imp.total_lines} />
        <Card label="Matched" v={imp.matched_lines} accent="emerald" />
        <Card label="Unmatched" v={imp.unmatched_lines} accent="amber" />
        <Card label="Total Revenue" v={fmtEUR(imp.total_revenue_eur)} />
        <Card label="Bagian Label" v={fmtIDR(imp.total_label_idr)} accent="rose" />
      </div>

      <div className="rm-card p-5">
        <h3 className="font-display font-bold text-lg tracking-tight mb-3">Breakdown per Label</h3>
        {per_label?.length === 0 ? <div className="text-sm text-zinc-500">Belum ada line matched.</div> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-[11px] uppercase tracking-widest text-zinc-500"><th className="py-2">Label</th><th>Lines</th><th>Revenue EUR</th><th className="text-right">Bagian IDR</th></tr></thead>
              <tbody>
                {per_label.map((r) => (
                  <tr key={r._id} className="border-t border-white/5">
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
            <thead><tr className="text-left text-[10px] uppercase tracking-widest text-zinc-500">
              <th className="py-2">ISRC</th><th>Track</th><th>Artist</th><th>Platform</th><th>Country</th><th>Streams</th><th>Revenue EUR</th><th>Match</th><th className="text-right">Label IDR</th>
            </tr></thead>
            <tbody>
              {lines.slice(0, 100).map((l) => (
                <tr key={l.id} className="border-t border-white/5">
                  <td className="py-2 font-mono text-[10px]">{l.isrc || "—"}</td>
                  <td className="font-semibold truncate max-w-[150px]">{l.track_title_raw}</td>
                  <td className="truncate max-w-[120px]">{l.artist_name_raw}</td>
                  <td>{l.platform}</td>
                  <td>{l.country}</td>
                  <td>{l.quantity?.toLocaleString("id-ID")}</td>
                  <td>{fmtEUR(l.revenue_eur)}</td>
                  <td><span className={`text-[10px] font-bold ${l.match_status === "matched" || l.match_status === "manually_matched" ? "text-emerald-300" : "text-amber-300"}`}>{l.match_status}</span></td>
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
  const cls = { emerald: "text-emerald-300", amber: "text-amber-300", rose: "text-rose-300" }[accent] || "";
  return <div className="rm-card p-4"><div className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold">{label}</div><div className={`font-display text-2xl font-extrabold tracking-tighter mt-1 ${cls}`}>{v}</div></div>;
}
