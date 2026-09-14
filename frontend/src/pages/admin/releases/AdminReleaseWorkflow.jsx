import React, { useEffect, useState } from "react";
import { CheckCircle2, CreditCard, RadioTower, Send, ShieldCheck, SquareArrowOutUpRight, XCircle, History, Wallet, Upload, Image as ImageIcon, FileAudio, FileCheck2 } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { releaseStatusLabel } from "@/utils/releasePresentation";

const OVERRIDE_STATUSES = ["draft", "submitted", "under_review", "approved", "delivered", "live", "need_revision", "rejected", "taken_down"];
const fmtIDR = (value) => `Rp ${Number(value || 0).toLocaleString("id-ID")}`;

export const AdminReleaseWorkflow = ({ release, onUpdated, setMessage, setError }) => {
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [upc, setUpc] = useState(release.upc || "");
  const [releaseDate, setReleaseDate] = useState((release.release_date || "").slice(0, 10));
  const [isrcs, setIsrcs] = useState({});
  const [showOverride, setShowOverride] = useState(false);
  const [targetStatus, setTargetStatus] = useState("");
  const [showShortfall, setShowShortfall] = useState(false);
  const [shortfall, setShortfall] = useState(null);
  const [shortfallBusy, setShortfallBusy] = useState(false);
  useEffect(() => { setUpc(release.upc || ""); setReleaseDate((release.release_date || "").slice(0, 10)); setIsrcs(Object.fromEntries((release.tracks || []).map((track) => [track.id, track.isrc || ""]))); }, [release]);

  const loadShortfall = async () => {
    setShortfallBusy(true); setError("");
    try { const { data } = await api.get(`/releases/${release.id}/admin/shortfall-preview`); setShortfall(data); }
    catch (requestError) { setError(formatApiError(requestError.response?.data?.detail)); }
    finally { setShortfallBusy(false); }
  };
  const toggleShortfall = async () => {
    const next = !showShortfall; setShowShortfall(next);
    if (next && !shortfall) await loadShortfall();
  };
  const createShortfall = async () => {
    setShortfallBusy(true); setError("");
    try {
      const { data } = await api.post(`/releases/${release.id}/admin/shortfall-invoice`, {});
      setShortfall(data.state);
      setMessage(`Invoice kekurangan Rp ${Number(data.invoice.amount).toLocaleString("id-ID")} dibuat. Label dapat membayarnya di menu Invoice.`);
    } catch (requestError) { setError(formatApiError(requestError.response?.data?.detail)); }
    finally { setShortfallBusy(false); }
  };

  const action = async (name, extra = {}) => {
    setBusy(true); setError("");
    try {
      const { data } = await api.post(`/releases/${release.id}/admin/action`, { action: name, note: note.trim() || null, ...extra });
      setMessage({ start_review: "Rilisan masuk tahap pemeriksaan.", send_payment: "Tautan pembayaran dikirim ke label.", approve: "Rilisan disetujui.", deliver: "Rilisan dikirim ke Believe.", mark_live: "Rilisan kini tayang.", need_revision: "Permintaan revisi dikirim ke label.", reject: "Rilisan ditolak.", takedown: "Rilisan diturunkan.", override_status: "Status rilisan berhasil dikoreksi." }[name]);
      setNote(""); setShowOverride(false); setTargetStatus(""); onUpdated(data);
    } catch (requestError) { setError(formatApiError(requestError.response?.data?.detail)); }
    finally { setBusy(false); }
  };
  const status = release.status;
  const [assetBusy, setAssetBusy] = useState("");
  const uploadAsset = async (key, url, formData, okMsg) => {
    setAssetBusy(key); setError("");
    try {
      const { data } = await api.post(url, formData, { headers: { "Content-Type": "multipart/form-data" } });
      setMessage(okMsg);
      const { data: fresh } = await api.get(`/releases/${release.id}`);
      onUpdated(fresh);
      return data;
    } catch (requestError) { setError(formatApiError(requestError.response?.data?.detail)); }
    finally { setAssetBusy(""); }
  };
  const onCoverChange = (event) => { const file = event.target.files?.[0]; if (!file) return; const fd = new FormData(); fd.append("file", file); uploadAsset("cover", `/releases/${release.id}/admin/upload-cover`, fd, "Cover berhasil diperbarui."); event.target.value = ""; };
  const onAudioChange = (trackId) => (event) => { const file = event.target.files?.[0]; if (!file) return; const fd = new FormData(); fd.append("track_id", trackId); fd.append("file", file); uploadAsset(`audio-${trackId}`, `/releases/${release.id}/admin/upload-audio`, fd, "Audio track berhasil diperbarui."); event.target.value = ""; };
  const onRemixChange = (event) => { const file = event.target.files?.[0]; if (!file) return; const fd = new FormData(); fd.append("file", file); uploadAsset("remix", `/releases/${release.id}/admin/upload-remix-permission`, fd, "Bukti izin remix diunggah."); event.target.value = ""; };
  return <aside className="sticky bottom-4 border border-white/15 bg-zinc-950/95 p-4 shadow-2xl backdrop-blur" data-testid="admin-release-workflow"><div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between"><div><div className="text-xs font-bold uppercase text-zinc-500">Tindakan Berikutnya</div><div className="mt-1 text-sm text-zinc-300" data-testid="admin-release-workflow-status">Status saat ini: <strong className="text-white">{releaseStatusLabel(status)}</strong></div></div>
    {["submitted", "under_review", "need_revision", "live"].includes(status) && <label className="min-w-72 flex-1 lg:max-w-xl"><span className="rm-label">Catatan / alasan</span><textarea className="rm-input min-h-20" value={note} onChange={(event) => setNote(event.target.value)} data-testid="admin-release-note-input" /></label>}
    <div className="flex flex-wrap gap-2">
      {status === "submitted" && <><button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => action("start_review")} data-testid="admin-release-start-review-button"><ShieldCheck className="h-4 w-4" /> Mulai Pemeriksaan</button><button className="rm-btn-ghost" disabled={busy || !note.trim()} onClick={() => action("need_revision")} data-testid="admin-release-need-revision-button">Minta Revisi</button><button className="rounded-md border border-red-500/30 px-4 py-2 text-sm font-bold text-red-300" disabled={busy || !note.trim()} onClick={() => action("reject")} data-testid="admin-release-reject-button"><XCircle className="mr-2 inline h-4 w-4" /> Tolak</button></>}
      {status === "under_review" && <>{release.billing_flow === "pay_per_release" || release.payment_status === "not_generated" ? <button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => action("send_payment")} data-testid="admin-release-send-payment-button"><CreditCard className="h-4 w-4" /> Kirim Tautan Pembayaran</button> : <button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => action("approve")} data-testid="admin-release-approve-button"><CheckCircle2 className="h-4 w-4" /> Setujui</button>}<button className="rm-btn-ghost" disabled={busy || !note.trim()} onClick={() => action("need_revision")} data-testid="admin-release-need-revision-button">Minta Revisi</button><button className="rounded-md border border-red-500/30 px-4 py-2 text-sm font-bold text-red-300" disabled={busy || !note.trim()} onClick={() => action("reject")} data-testid="admin-release-reject-button">Tolak</button></>}
      {status === "awaiting_payment" && <div className="flex items-center gap-2 text-sm text-amber-300" data-testid="admin-release-awaiting-payment"><CreditCard className="h-4 w-4" /> Menunggu pembayaran label</div>}
      {status === "paid" && <button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => action("approve")} data-testid="admin-release-approve-button"><CheckCircle2 className="h-4 w-4" /> Setujui</button>}
      {status === "approved" && <div className="flex flex-wrap items-end gap-3"><label className="text-sm"><span className="rm-label">Tanggal Rilis (opsional, boleh diubah)</span><input type="date" className="rm-input" value={releaseDate} onChange={(event) => setReleaseDate(event.target.value)} data-testid="admin-release-deliver-date-input" /></label><button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => action("deliver", { release_date: releaseDate || undefined })} data-testid="admin-release-deliver-button"><SquareArrowOutUpRight className="h-4 w-4" /> Kirim ke Believe</button></div>}
      {status === "live" && <button className="rounded-md border border-red-500/30 px-4 py-2 text-sm font-bold text-red-300" disabled={busy || !note.trim()} onClick={() => action("takedown")} data-testid="admin-release-takedown-button"><RadioTower className="mr-2 inline h-4 w-4" /> Turunkan Rilisan</button>}
      {status === "need_revision" && <button className="rounded-md border border-red-500/30 px-4 py-2 text-sm font-bold text-red-300" disabled={busy || !note.trim()} onClick={() => action("reject")} data-testid="admin-release-reject-button">Tolak</button>}
      {["rejected", "taken_down"].includes(status) && <span className="text-sm text-zinc-500" data-testid="admin-release-no-action">Tidak ada tindakan lanjutan saat ini.</span>}
    </div></div>
    {status === "delivered" && <div className="mt-5 border-t border-white/10 pt-5" data-testid="admin-release-live-identifiers"><div className="grid gap-3 md:grid-cols-2"><label><span className="rm-label">Tanggal Rilis (opsional, boleh diubah)</span><input type="date" className="rm-input" value={releaseDate} onChange={(event) => setReleaseDate(event.target.value)} data-testid="admin-release-live-date-input" /></label><label><span className="rm-label">UPC Rilisan</span><input className="rm-input font-mono uppercase" value={upc} onChange={(event) => setUpc(event.target.value)} data-testid="admin-release-upc-input" /></label>{release.tracks?.map((track) => <label key={track.id}><span className="rm-label">ISRC — {track.track_title}</span><input className="rm-input font-mono uppercase" value={isrcs[track.id] || ""} onChange={(event) => setIsrcs((current) => ({ ...current, [track.id]: event.target.value }))} data-testid={`admin-release-track-isrc-input-${track.id}`} /></label>)}</div><div className="mt-4 flex justify-end"><button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => action("mark_live", { upc, track_isrcs: isrcs, release_date: releaseDate || undefined })} data-testid="admin-release-live-button"><Send className="h-4 w-4" /> Simpan ISRC/UPC & Tandai Tayang</button></div></div>}
    <div className="mt-5 border-t border-white/10 pt-4" data-testid="admin-release-override-section">
      <button type="button" className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-zinc-400 hover:text-white" onClick={() => setShowOverride((value) => !value)} data-testid="admin-release-override-toggle"><History className="h-4 w-4" /> Koreksi / Mundurkan Status {showOverride ? "▲" : "▼"}</button>
      {showOverride && <div className="mt-3 grid gap-3 md:grid-cols-2">
        <label><span className="rm-label">Ubah status ke (jika salah pilih)</span><select className="rm-input" value={targetStatus} onChange={(event) => setTargetStatus(event.target.value)} data-testid="admin-release-override-select"><option value="">— Pilih status tujuan —</option>{OVERRIDE_STATUSES.filter((s) => s !== status).map((s) => <option key={s} value={s}>{releaseStatusLabel(s)}</option>)}</select></label>
        <label><span className="rm-label">Alasan koreksi (wajib)</span><input className="rm-input" value={note} onChange={(event) => setNote(event.target.value)} placeholder="Contoh: salah pilih status" data-testid="admin-release-override-note" /></label>
        <div className="md:col-span-2 flex justify-end"><button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy || !targetStatus || !note.trim()} onClick={() => action("override_status", { target_status: targetStatus })} data-testid="admin-release-override-apply"><History className="h-4 w-4" /> Terapkan Perubahan Status</button></div>
        <p className="md:col-span-2 text-xs text-zinc-500">Koreksi manual tidak memicu pembayaran/pengiriman otomatis. Gunakan hanya untuk memperbaiki status yang salah dipilih.</p>
      </div>}
    </div>
    <div className="mt-5 border-t border-white/10 pt-4" data-testid="admin-release-shortfall-section">
      <button type="button" className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-zinc-400 hover:text-white" onClick={toggleShortfall} data-testid="admin-release-shortfall-toggle"><Wallet className="h-4 w-4" /> Invoice Kekurangan Paket Album {showShortfall ? "▲" : "▼"}</button>
      {showShortfall && <div className="mt-3 space-y-3">
        {shortfallBusy && !shortfall && <div className="text-sm text-zinc-400" data-testid="admin-release-shortfall-loading">Menghitung kekurangan…</div>}
        {shortfall && <>
          <div className="grid gap-2 rounded-lg border border-white/10 bg-white/[0.02] p-4 text-sm" data-testid="admin-release-shortfall-summary">
            <div className="flex justify-between"><span className="text-zinc-400">Paket Album</span><strong data-testid="admin-release-shortfall-album">{fmtIDR(shortfall.album_package_price_idr)}</strong></div>
            <div className="flex justify-between"><span className="text-zinc-400">Sudah dibayar</span><strong data-testid="admin-release-shortfall-paid">{fmtIDR(shortfall.already_paid_idr)}</strong></div>
            <div className="flex justify-between border-t border-white/10 pt-2"><span className="text-zinc-400">Kekurangan</span><strong className="rm-gradient-text" data-testid="admin-release-shortfall-amount">{fmtIDR(shortfall.shortfall_idr)}</strong></div>
          </div>
          {shortfall.open_shortfall_invoice_id && <p className="text-xs text-amber-300" data-testid="admin-release-shortfall-pending">Invoice kekurangan masih menunggu pembayaran label.</p>}
          {!shortfall.is_album && <p className="text-xs text-zinc-500" data-testid="admin-release-shortfall-not-album">Hanya untuk rilisan tipe ALBUM.</p>}
          {shortfall.is_album && !shortfall.has_prior_payment && <p className="text-xs text-zinc-500" data-testid="admin-release-shortfall-no-payment">Belum ada pembayaran per lagu untuk rilisan ini.</p>}
          {shortfall.is_album && shortfall.has_prior_payment && !shortfall.eligible && !shortfall.open_shortfall_invoice_id && <p className="text-xs text-zinc-500" data-testid="admin-release-shortfall-none">Tidak ada kekurangan untuk rilisan ini.</p>}
          <div className="flex justify-end"><button type="button" className="rm-btn-primary inline-flex items-center gap-2" disabled={shortfallBusy || !shortfall.eligible} onClick={createShortfall} data-testid="admin-release-shortfall-create"><Wallet className="h-4 w-4" /> {shortfallBusy ? "Memproses…" : "Buat Invoice Kekurangan"}</button></div>
        </>}
        <p className="text-xs text-zinc-500">Gunakan untuk album yang terlanjur dibayar per lagu. Invoice hanya menagih selisih menuju paket album dan tidak mengubah status rilisan.</p>
      </div>}
    </div>

    {status !== "live" && <div className="mt-5 border-t border-white/10 pt-4 space-y-3" data-testid="admin-release-assets-section">
      <div className="text-xs font-bold uppercase tracking-widest text-zinc-400">Revisi Aset (Admin)</div>
      <div className="flex flex-wrap gap-2">
        <label className="rm-btn-ghost inline-flex cursor-pointer items-center gap-2 text-sm" data-testid="admin-release-upload-cover-label"><ImageIcon className="h-4 w-4" />{assetBusy === "cover" ? "Mengunggah…" : "Ganti Cover (3000×3000)"}<input type="file" accept="image/png,image/jpeg" className="hidden" onChange={onCoverChange} disabled={!!assetBusy} data-testid="admin-release-upload-cover-input" /></label>
        <label className="rm-btn-ghost inline-flex cursor-pointer items-center gap-2 text-sm" data-testid="admin-release-upload-remix-label"><FileCheck2 className="h-4 w-4" />{assetBusy === "remix" ? "Mengunggah…" : (release.remix_permission_url ? "Ganti Bukti Izin Remix" : "Upload Bukti Izin Remix")}<input type="file" accept="application/pdf,image/png,image/jpeg" className="hidden" onChange={onRemixChange} disabled={!!assetBusy} data-testid="admin-release-upload-remix-input" /></label>
      </div>
      {release.remix_permission_url && <a href={release.remix_permission_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-xs text-sky-300 hover:text-sky-200" data-testid="admin-release-remix-link"><FileCheck2 className="h-3.5 w-3.5" /> Lihat bukti izin remix ({release.remix_permission_filename || "file"})</a>}
      <p className="text-[11px] text-zinc-500">Surat izin remix wajib ditandatangani kedua belah pihak (pencipta asli & label) serta dibubuhi materai Rp 10.000.</p>
      <div className="space-y-2">
        <div className="text-[11px] font-bold uppercase tracking-widest text-zinc-500">Ganti Audio per Track</div>
        {(release.tracks || []).map((track) => <div key={track.id} className="flex items-center justify-between gap-3 rounded-md border border-white/10 bg-white/[0.02] px-3 py-2 text-sm">
          <span className="min-w-0 truncate text-zinc-300">{track.track_number}. {track.track_title}</span>
          <label className="shrink-0 cursor-pointer rounded-md border border-white/15 px-2.5 py-1 text-xs font-semibold text-zinc-200 transition-colors hover:bg-white/10" data-testid={`admin-release-upload-audio-label-${track.id}`}><FileAudio className="mr-1 inline h-3.5 w-3.5" />{assetBusy === `audio-${track.id}` ? "Mengunggah…" : "Ganti WAV"}<input type="file" accept=".wav,audio/wav" className="hidden" onChange={onAudioChange(track.id)} disabled={!!assetBusy} data-testid={`admin-release-upload-audio-input-${track.id}`} /></label>
        </div>)}
      </div>
      <p className="text-[11px] text-zinc-600">Aset tidak dapat diubah setelah rilisan berstatus tayang (live).</p>
    </div>}
  </aside>;
};