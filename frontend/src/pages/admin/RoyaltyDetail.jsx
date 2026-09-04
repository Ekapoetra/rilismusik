import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { RoyaltyImportReplacementPanel } from "@/components/admin/RoyaltyImportReplacementPanel";
import { Loader2, RefreshCw, Upload, XCircle, Trash2, Replace } from "lucide-react";

function fmtIDR(n) { return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0); }
function fmtEUR(n) { return new Intl.NumberFormat("en-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 2 }).format(n || 0); }
const STABLE_REPLACEMENT_STATUSES = ["published", "dana_received"];

export default function AdminRoyaltyDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { hasPermission } = useAuth();
  const canManage = hasPermission("royalty.manage");
  const canDelete = hasPermission("royalty.delete");
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [repairFile, setRepairFile] = useState(null);
  const [repairUploadBusy, setRepairUploadBusy] = useState(false);
  const [repairUploadPct, setRepairUploadPct] = useState(0);
  const [replacementOpen, setReplacementOpen] = useState(false);

  const load = useCallback(async () => {
    try { const { data } = await api.get(`/royalty/admin/imports/${id}`); setData(data); }
    catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
  }, [id]);
  useEffect(() => {
    setData(null);
    setErr("");
    setReplacementOpen(false);
    load();
  }, [load]);

  // Auto-poll every 3s while a background transition is running.
  const pollRef = useRef(null);
  useEffect(() => {
    const inFlight = ["processing", "publishing", "receiving"].includes(data?.import?.status)
      || data?.import?.period_repair_status === "processing";
    if (inFlight && !pollRef.current) {
      pollRef.current = setInterval(load, 3000);
    } else if (!inFlight && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [data?.import?.status, data?.import?.period_repair_status, load]);

  const publish = async () => {
    setBusy(true); setErr(""); setMsg("");
    try {
      const { data: res } = await api.post(`/royalty/admin/imports/${id}/publish`, { confirm: true });
      if (res?.status === "publishing") {
        setMsg("Publish dijadwalkan — progress akan ditampilkan di bawah.");
      } else if (res?.status === "published") {
        setMsg("Royalti dipublish — saldo pending bertambah ke label.");
      } else {
        setMsg(`Publish diterima (status: ${res?.status}).`);
      }
      load();
    }
    catch (e) {
      // Try to surface a descriptive error from the backend
      const detail = e.response?.data?.detail;
      const status = e.response?.status;
      if (status === 500) {
        setErr(`Server error 500: ${typeof detail === "string" ? detail : "Cek backend logs"}. Jika ini terjadi di production, pastikan deploy terbaru (Phase 16 background publish) sudah aktif.`);
      } else {
        setErr(formatApiError(detail) || e.message || "Gagal publish");
      }
    }
    finally { setBusy(false); }
  };
  const markDana = async () => {
    setBusy(true); setErr(""); setMsg("");
    try {
      const { data: response } = await api.post(`/royalty/admin/imports/${id}/mark-dana-received`);
      setMsg(response?.status === "receiving" ? "Pemindahan saldo dijadwalkan dan berjalan di background." : "Dana sudah diterima.");
      load();
    }
    catch (e) { setErr(formatApiError(e.response?.data?.detail)); } finally { setBusy(false); }
  };
  const retry = async () => {
    setBusy(true); setErr(""); setMsg("");
    try { await api.post(`/royalty/admin/imports/${id}/retry`); setMsg("Retry dijadwalkan — refresh otomatis akan menampilkan progress."); load(); }
    catch (e) { setErr(formatApiError(e.response?.data?.detail)); } finally { setBusy(false); }
  };
  const repairPeriod = async () => {
    setBusy(true); setErr(""); setMsg("");
    try {
      const { data: response } = await api.post(`/royalty/admin/imports/${id}/repair-reporting-period`);
      setMsg(response?.already_running ? "Reparasi Bulan laporan masih berjalan." : "Reparasi Bulan laporan dijadwalkan di background.");
      load();
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };
  const uploadRepairSource = async () => {
    if (!repairFile) { setErr("Pilih CSV asli untuk laporan ini."); return; }
    if (!repairFile.name.toLowerCase().endsWith(".csv")) { setErr("File sumber wajib berformat .csv"); return; }
    setRepairUploadBusy(true); setRepairUploadPct(0); setErr(""); setMsg("");
    try {
      const { data: initiated } = await api.post(`/royalty/admin/imports/${id}/repair-source/initiate`, {
        filename: repairFile.name,
        size_bytes: repairFile.size,
      });
      await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("PUT", initiated.upload_url);
        xhr.setRequestHeader("Content-Type", initiated.content_type);
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) setRepairUploadPct(Math.round((event.loaded / event.total) * 100));
        };
        xhr.onload = () => xhr.status >= 200 && xhr.status < 300
          ? resolve()
          : reject(new Error(`Upload R2 gagal (${xhr.status})`));
        xhr.onerror = () => reject(new Error("Koneksi upload R2 terputus"));
        xhr.send(repairFile);
      });
      const { data: finalized } = await api.post(`/royalty/admin/imports/${id}/repair-source/finalize`, {
        upload_id: initiated.upload_id,
      });
      setRepairUploadPct(100);
      setRepairFile(null);
      setMsg(finalized?.job_id
        ? "CSV sumber tersimpan di R2. Reparasi Bulan laporan dimulai di background."
        : "CSV sumber tersimpan di R2.");
      await load();
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail || e.message));
    } finally { setRepairUploadBusy(false); }
  };

  const remove = async () => {
    setBusy(true); setErr(""); setMsg("");
    if (!window.confirm(`Hapus import periode ${data?.import?.period || data?.import?.period_start || id} (status: ${data?.import?.status})? Semua baris royalti + label/release/track auto-created akan ikut terhapus. Aksi ini permanen.`)) {
      setBusy(false);
      return;
    }
    try {
      const { data: res } = await api.delete(`/royalty/admin/imports/${id}`);
      setMsg(`Import dihapus — ${(res.lines_deleted || 0).toLocaleString("id-ID")} baris terhapus. Kembali ke list…`);
      setTimeout(() => nav("/admin/royalty"), 1500);
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
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
          <div className="text-sm text-zinc-400">File: {imp.filename} • Kurs: Rp {imp.exchange_rate_eur_idr?.toLocaleString("id-ID")} / €1 • Pembagian label langsung tanpa fee tambahan</div>
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
          {imp.status === "receiving" && (
            <span className="px-3 py-2 rounded-full text-xs font-bold bg-cyan-500/15 text-cyan-300 flex items-center gap-2" data-testid="royalty-detail-status-receiving">
              <Loader2 className="w-3 h-3 animate-spin" /> Memindahkan saldo… {imp.receive_progress_pct || imp.progress_pct || 0}%
            </span>
          )}
          {canManage && (imp.status === "processing" || imp.status === "error") && (
            <button className="rm-btn-ghost flex items-center gap-2" disabled={busy} onClick={retry} data-testid="admin-royalty-retry">
              <RefreshCw className="w-4 h-4" /> Retry
            </button>
          )}
          {canManage && (imp.status === "pending_review" || imp.status === "publish_error") && (
            <button className="rm-btn-primary" disabled={busy} onClick={publish} data-testid="admin-royalty-publish">
              {imp.status === "publish_error" ? "Coba Publish Lagi" : "Publish (kredit ke pending)"}
            </button>
          )}
          {canManage && (imp.status === "published" || imp.status === "receive_error") && <button className="rm-btn-primary" disabled={busy} onClick={markDana} data-testid="admin-royalty-mark-dana">{imp.status === "receive_error" ? "Coba Tandai Dana Lagi" : "Tandai Dana Diterima"}</button>}
          {imp.status === "dana_received" && <span className="px-3 py-2 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-300" data-testid="royalty-detail-status-received">✓ Dana sudah diterima</span>}
          {STABLE_REPLACEMENT_STATUSES.includes(imp.status) && canManage && <button className="rm-btn-ghost flex items-center gap-2 text-amber-300" onClick={() => setReplacementOpen((value) => !value)} data-testid="admin-royalty-replacement-open"><Replace className="w-4 h-4" /> Ganti File Import</button>}
          {canManage && !['awaiting_upload', 'processing', 'publishing', 'receiving', 'deleting'].includes(imp.status) && imp.period_repair_status !== "processing" && (
            <button className="rm-btn-ghost flex items-center gap-2 text-cyan-300" disabled={busy} onClick={repairPeriod} data-testid="admin-royalty-repair-period">
              <RefreshCw className="w-4 h-4" /> Perbaiki Bulan Laporan
            </button>
          )}
          {canDelete && ["awaiting_upload", "processing", "error", "publish_error", "pending_review"].includes(imp.status) && (
            <button
              className="rm-btn-ghost text-rose-300 hover:bg-rose-500/10 flex items-center gap-2"
              disabled={busy}
              onClick={remove}
              data-testid="admin-royalty-delete"
              title="Hapus import ini permanen — hanya untuk yang belum dipublish/dana diterima"
            >
              <Trash2 className="w-4 h-4" /> Hapus Import
            </button>
          )}
        </div>
      </div>

      {replacementOpen && <RoyaltyImportReplacementPanel oldImport={imp} canCommit={canManage} onClose={() => setReplacementOpen(false)} onCompleted={(replacementId) => nav(`/admin/royalty/${replacementId}`)} />}

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

      {imp.status === "receiving" && (
        <div className="rm-card p-5 space-y-3" data-testid="royalty-detail-receive-progress">
          <div className="flex justify-between items-center text-sm">
            <span className="text-zinc-400">Memindahkan saldo pending menjadi tersedia di background…</span>
            <span className="font-bold text-cyan-300">{imp.receive_progress_pct || imp.progress_pct || 0}%</span>
          </div>
          <div className="h-2 rounded-full bg-white/10 overflow-hidden">
            <div className="h-full bg-gradient-to-r from-cyan-400 to-emerald-400 transition-all" style={{ width: `${imp.receive_progress_pct || imp.progress_pct || 0}%` }} />
          </div>
          <div className="text-[11px] text-zinc-500">Proses idempoten dan otomatis dilanjutkan setelah backend restart.</div>
        </div>
      )}

      {imp.period_repair_status === "processing" && (
        <div className="rm-card p-5 space-y-3" data-testid="royalty-detail-period-repair-progress">
          <div className="flex justify-between items-center text-sm">
            <span className="text-zinc-400">Memvalidasi dan memperbaiki Bulan laporan dari CSV asli…</span>
            <span className="font-bold text-cyan-300">{imp.period_repair_progress_pct || 0}%</span>
          </div>
          <div className="h-2 rounded-full bg-white/10 overflow-hidden">
            <div className="h-full bg-gradient-to-r from-cyan-400 to-sky-400 transition-all" style={{ width: `${imp.period_repair_progress_pct || 0}%` }} />
          </div>
          <div className="text-[11px] text-zinc-500">Nominal, saldo, dan status royalti tidak diubah.</div>
        </div>
      )}

      {imp.period_repair_status === "done" && (
        <div className="rounded-2xl bg-cyan-500/10 border border-cyan-500/20 px-4 py-3 text-sm text-cyan-200" data-testid="royalty-detail-period-repair-complete">
          Bulan laporan sudah diperbaiki dari CSV asli. Rebuild Analytics berjalan terpisah di background.
        </div>
      )}

      {imp.period_repair_status === "error" && imp.period_repair_error && (
        <div className="rounded-2xl bg-red-500/10 border border-red-500/30 px-4 py-4 text-sm text-red-200 space-y-3" data-testid="royalty-detail-period-repair-error">
          <div className="font-bold">Reparasi Bulan laporan gagal</div>
          <div className="mt-1 text-red-200/80">{imp.period_repair_error}</div>
          <div className="pt-3 border-t border-red-400/20 space-y-3">
            <div className="text-xs text-zinc-300">Jika CSV asli sudah tidak tersimpan, unggah ulang file yang sama. File hanya dipakai untuk memperbaiki periode—royalti dan saldo tidak diimpor ulang.</div>
            <input
              type="file"
              accept=".csv,text/csv"
              disabled={repairUploadBusy}
              onChange={(event) => setRepairFile(event.target.files?.[0] || null)}
              className="rm-input text-xs"
              data-testid="admin-royalty-repair-source-file"
            />
            {repairUploadBusy && (
              <div className="space-y-1" data-testid="admin-royalty-repair-source-progress">
                <div className="flex justify-between text-[11px] text-zinc-400"><span>Upload langsung ke R2</span><span>{repairUploadPct}%</span></div>
                <div className="h-1.5 rounded-full bg-white/10 overflow-hidden"><div className="h-full bg-cyan-400 transition-all" style={{ width: `${repairUploadPct}%` }} /></div>
              </div>
            )}
            <button
              className="rm-btn-primary flex items-center gap-2"
              disabled={!repairFile || repairUploadBusy}
              onClick={uploadRepairSource}
              data-testid="admin-royalty-repair-source-upload"
            >
              {repairUploadBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
              {repairUploadBusy ? "Mengunggah…" : "Unggah CSV Sumber & Perbaiki"}
            </button>
          </div>
        </div>
      )}

      {(imp.status === "error" || imp.status === "publish_error" || imp.status === "receive_error") && imp.error_message && (
        <div className="rounded-2xl bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-200 flex items-start gap-3" data-testid="royalty-detail-error-banner">
          <XCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <div className="font-bold">{imp.status === "publish_error" ? "Publish gagal" : imp.status === "receive_error" ? "Penerimaan dana gagal" : "Import gagal"}</div>
            <div className="text-red-200/80 mt-1">{imp.error_message}</div>
            <div className="text-[11px] text-red-200/60 mt-1">
              {imp.status === "publish_error"
                ? "Klik tombol \"Coba Publish Lagi\" di atas — proses idempotent, label yang sudah dikredit tidak akan didouble."
                : imp.status === "receive_error"
                  ? "Klik tombol \"Coba Tandai Dana Lagi\" — saldo yang sudah dipindahkan tidak akan dihitung dua kali."
                : "Klik Retry jika file CSV masih ada di server, atau upload ulang."}
            </div>
          </div>
        </div>
      )}

      {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm" data-testid="admin-royalty-detail-error">{err}</div>}
      {msg && <div className="rounded-2xl bg-emerald-500/15 text-emerald-300 px-4 py-3 text-sm" data-testid="admin-royalty-detail-message">{msg}</div>}

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card label="Total Lines" v={imp.total_lines} />
        <Card label="Matched" v={imp.matched_lines} accent="emerald" />
        <Card label="Unmatched" v={imp.unmatched_lines} accent="amber" />
        <Card label="Pendapatan Kotor" v={fmtEUR(imp.total_revenue_eur)} />
        <Card label="Bagian Label" v={fmtIDR(imp.total_label_idr)} accent="rose" />
      </div>

      <div className="rm-card p-5">
        <h3 className="font-display font-bold text-lg tracking-tight mb-3">Breakdown per Label</h3>
        {per_label?.length === 0 ? <div className="text-sm text-zinc-500">Belum ada line matched.</div> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-[11px] uppercase tracking-widest text-zinc-500"><th className="py-2">Label</th><th>Lines</th><th>Pendapatan Kotor EUR</th><th className="text-right">Bagian IDR</th></tr></thead>
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
              <th className="py-2">ISRC</th><th>Track</th><th>Artist</th><th>Platform</th><th>Country</th><th>Streams</th><th>Pendapatan Kotor EUR</th><th>Match</th><th className="text-right">Label IDR</th>
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
