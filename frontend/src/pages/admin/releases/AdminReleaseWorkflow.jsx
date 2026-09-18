import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, CreditCard, RadioTower, Send, Save, ShieldCheck, SquareArrowOutUpRight, XCircle, History, Wallet, Upload, Image as ImageIcon, FileAudio, FileCheck2, Minus, ChevronUp, ReceiptText, ExternalLink, ArrowUpRight, PencilLine } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { releaseStatusLabel } from "@/utils/releasePresentation";
import { PAYMENT_STATUS, formatDateTime } from "@/pages/admin/payments/paymentPresentation";

const OVERRIDE_STATUSES = ["draft", "submitted", "under_review", "approved", "delivered", "live", "need_revision", "rejected", "taken_down"];
const fmtIDR = (value) => `Rp ${Number(value || 0).toLocaleString("id-ID")}`;

export const AdminReleaseWorkflow = ({ release, onUpdated, setMessage, setError }) => {
  const { hasPermission, user } = useAuth();
  const isSuper = user?.role === "super_admin";
  const canGoLive = hasPermission("releases.go_live");
  const canTakedown = hasPermission("releases.takedown");
  const canReview = hasPermission("releases.review") || isSuper;
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
  const [minimized, setMinimized] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [editBusy, setEditBusy] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [editTracks, setEditTracks] = useState({});
  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem("adminReleaseWorkflowUI") || "{}");
      if (typeof saved.minimized === "boolean") setMinimized(saved.minimized);
      if (saved.pos) { delete saved.pos; localStorage.setItem("adminReleaseWorkflowUI", JSON.stringify(saved)); }
    } catch (_e) { /* ignore */ }
  }, []);
  const persist = (patch) => { try { const s = JSON.parse(localStorage.getItem("adminReleaseWorkflowUI") || "{}"); delete s.pos; localStorage.setItem("adminReleaseWorkflowUI", JSON.stringify({ ...s, ...patch })); } catch (_e) { /* ignore */ } };
  const toggleMinimized = () => setMinimized((value) => { persist({ minimized: !value }); return !value; });
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
      setMessage({ start_review: "Rilisan masuk tahap pemeriksaan.", send_payment: "Tautan pembayaran dikirim ke label.", bill_ppr: "Tagihan Pay Per Release dibuat sesuai submit.", approve: "Rilisan disetujui.", deliver: "Rilisan dikirim ke Believe.", save_identifiers: "UPC/ISRC tersimpan.", mark_live: "Rilisan kini tayang.", need_revision: "Permintaan revisi dikirim ke label.", reject: "Rilisan ditolak.", takedown: "Rilisan diturunkan.", override_status: "Status rilisan berhasil dikoreksi." }[name]);
      setNote(""); setShowOverride(false); setTargetStatus(""); onUpdated(data);
    } catch (requestError) { setError(formatApiError(requestError.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const openEdit = () => {
    setEditForm({
      release_title: release.release_title || "", artist_name: release.artist_name || "",
      release_date: (release.release_date || "").slice(0, 10), genre: release.genre || "",
      subgenre: release.subgenre || "", language: release.language || "",
      copyright_line: release.copyright_line || "", p_line: release.p_line || "", notes: release.notes || "",
    });
    setEditTracks(Object.fromEntries((release.tracks || []).map((t) => [t.id, { track_title: t.track_title || "", isrc: t.isrc || "" }])));
    setShowEdit((v) => !v);
  };
  const submitMetadataEdit = async () => {
    setEditBusy(true); setError("");
    try {
      const changes = {};
      Object.entries(editForm).forEach(([k, v]) => {
        const orig = k === "release_date" ? (release.release_date || "").slice(0, 10) : (release[k] ?? "");
        if ((v ?? "") !== (orig ?? "")) changes[k] = v;
      });
      const track_changes = {};
      (release.tracks || []).forEach((t) => {
        const e = editTracks[t.id] || {}; const tc = {};
        if ((e.track_title ?? "") !== (t.track_title ?? "")) tc.track_title = e.track_title;
        if ((e.isrc ?? "") !== (t.isrc ?? "")) tc.isrc = e.isrc;
        if (Object.keys(tc).length) track_changes[t.id] = tc;
      });
      if (!Object.keys(changes).length && !Object.keys(track_changes).length) { setError("Tidak ada perubahan metadata."); setEditBusy(false); return; }
      const { data } = await api.post(`/releases/${release.id}/admin/metadata-edit`, { changes, track_changes, note: note.trim() || null });
      setMessage(data.applied ? "Metadata berhasil diperbarui." : "Pengajuan perubahan metadata dikirim ke Super Admin untuk persetujuan.");
      const { data: fresh } = await api.get(`/releases/${release.id}`); onUpdated(fresh);
      setShowEdit(false); setNote("");
    } catch (requestError) { setError(formatApiError(requestError.response?.data?.detail)); }
    finally { setEditBusy(false); }
  };
  const reviewMetadataEdit = async (decision) => {
    const req = release.pending_metadata_edit; if (!req) return;
    setEditBusy(true); setError("");
    try {
      await api.post(`/releases/admin/metadata-edit/${req.id}/review`, { decision, note: note.trim() || null });
      setMessage(decision === "approve" ? "Perubahan metadata disetujui & diterapkan." : "Pengajuan metadata ditolak.");
      const { data: fresh } = await api.get(`/releases/${release.id}`); onUpdated(fresh); setNote("");
    } catch (requestError) { setError(formatApiError(requestError.response?.data?.detail)); }
    finally { setEditBusy(false); }
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
  const primaryAction = (() => {
    if (status === "submitted") return { name: "start_review", label: "Mulai Periksa", Icon: ShieldCheck };
    if (status === "under_review") return release.requires_ppr_payment
      ? { name: "send_payment", label: "Kirim Bayar", Icon: CreditCard }
      : { name: "approve", label: "Setujui", Icon: CheckCircle2 };
    if (status === "paid") return { name: "approve", label: "Setujui", Icon: CheckCircle2 };
    if (status === "approved") return { name: "deliver", label: "Kirim Believe", Icon: SquareArrowOutUpRight, extra: { release_date: releaseDate || undefined } };
    return null;
  })();
  return <aside className="fixed bottom-0 left-0 right-0 z-40 flex max-h-[70vh] flex-col rounded-t-xl border-t border-white/15 bg-zinc-950/95 shadow-2xl backdrop-blur md:left-[var(--rm-dock-left,256px)]" data-testid="admin-release-workflow"><div className="flex items-center justify-between gap-2 border-b border-white/10 px-4 py-2.5" data-testid="admin-release-workflow-dragbar"><div className="min-w-0"><div className="text-[11px] font-bold uppercase tracking-widest text-zinc-500">Tindakan Rilisan</div><div className="truncate text-xs text-zinc-400" data-testid="admin-release-workflow-status">Status: <strong className="text-white">{releaseStatusLabel(status)}</strong></div></div><div className="flex shrink-0 items-center gap-1.5">{primaryAction && <button type="button" data-nodrag onClick={() => action(primaryAction.name, primaryAction.extra || {})} disabled={busy} className="inline-flex items-center gap-1.5 rounded-md bg-pink-500 px-3 py-1.5 text-xs font-bold text-white transition-colors hover:bg-pink-400 disabled:opacity-50" data-testid="admin-release-quick-action"><primaryAction.Icon className="h-3.5 w-3.5" />{primaryAction.label}</button>}<button type="button" data-nodrag onClick={toggleMinimized} className="rounded-md border border-white/15 p-1.5 text-zinc-300 transition-colors hover:bg-white/10" data-testid="admin-release-workflow-toggle" title={minimized ? "Perbesar" : "Kecilkan"}>{minimized ? <ChevronUp className="h-4 w-4" /> : <Minus className="h-4 w-4" />}</button></div></div>{!minimized && <div className="min-h-0 flex-1 overflow-y-auto p-4" data-testid="admin-release-workflow-body"><div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between"><div><div className="text-xs font-bold uppercase text-zinc-500">Tindakan Berikutnya</div><div className="mt-1 text-sm text-zinc-300">Status saat ini: <strong className="text-white">{releaseStatusLabel(status)}</strong></div></div>
    {["submitted", "under_review", "need_revision", "live"].includes(status) && <label className="min-w-72 flex-1 lg:max-w-xl"><span className="rm-label">Catatan / alasan</span><textarea className="rm-input min-h-20" value={note} onChange={(event) => setNote(event.target.value)} data-testid="admin-release-note-input" /></label>}
    <div className="flex flex-wrap gap-2">
      {status === "submitted" && <><button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => action("start_review")} data-testid="admin-release-start-review-button"><ShieldCheck className="h-4 w-4" /> Mulai Pemeriksaan</button>{release.requires_ppr_payment && release.payment_status !== "paid" && <button className="inline-flex items-center gap-2 rounded-md border border-amber-500/40 px-4 py-2 text-sm font-bold text-amber-300 hover:bg-amber-500/10" disabled={busy} onClick={() => action("bill_ppr")} data-testid="admin-release-bill-ppr-button"><CreditCard className="h-4 w-4" /> Buat Tagihan Pay Per Release</button>}<button className="rm-btn-ghost" disabled={busy || !note.trim()} onClick={() => action("need_revision")} data-testid="admin-release-need-revision-button">Minta Revisi</button><button className="rounded-md border border-red-500/30 px-4 py-2 text-sm font-bold text-red-300" disabled={busy || !note.trim()} onClick={() => action("reject")} data-testid="admin-release-reject-button"><XCircle className="mr-2 inline h-4 w-4" /> Tolak</button></>}
      {status === "under_review" && <>{release.requires_ppr_payment ? <button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => action("send_payment")} data-testid="admin-release-send-payment-button"><CreditCard className="h-4 w-4" /> Kirim Tautan Pembayaran</button> : <button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => action("approve")} data-testid="admin-release-approve-button"><CheckCircle2 className="h-4 w-4" /> Setujui</button>}<button className="rm-btn-ghost" disabled={busy || !note.trim()} onClick={() => action("need_revision")} data-testid="admin-release-need-revision-button">Minta Revisi</button><button className="rounded-md border border-red-500/30 px-4 py-2 text-sm font-bold text-red-300" disabled={busy || !note.trim()} onClick={() => action("reject")} data-testid="admin-release-reject-button">Tolak</button></>}
      {status === "awaiting_payment" && <div className="flex items-center gap-2 text-sm text-amber-300" data-testid="admin-release-awaiting-payment"><CreditCard className="h-4 w-4" /> Menunggu pembayaran label</div>}
      {status === "paid" && <button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => action("approve")} data-testid="admin-release-approve-button"><CheckCircle2 className="h-4 w-4" /> Setujui</button>}
      {status === "approved" && (release.requires_ppr_payment && release.payment_status !== "paid"
        ? <div className="flex flex-col gap-2"><button className="inline-flex items-center gap-2 rounded-md border border-amber-500/40 px-4 py-2 text-sm font-bold text-amber-300 hover:bg-amber-500/10" disabled={busy} onClick={() => action("bill_ppr")} data-testid="admin-release-bill-ppr-button"><CreditCard className="h-4 w-4" /> Buat Tagihan Pay Per Release</button><span className="text-[11px] text-amber-300/80" data-testid="admin-release-approved-ppr-hint">Label kini Pay Per Release — buat tagihan sesuai submit sebelum kirim ke Believe.</span></div>
        : <div className="flex flex-wrap items-end gap-3"><label className="text-sm"><span className="rm-label">Tanggal Rilis (opsional, boleh diubah)</span><input type="date" className="rm-input" value={releaseDate} onChange={(event) => setReleaseDate(event.target.value)} data-testid="admin-release-deliver-date-input" /></label><button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => action("deliver", { release_date: releaseDate || undefined })} data-testid="admin-release-deliver-button"><SquareArrowOutUpRight className="h-4 w-4" /> Kirim ke Believe</button></div>)}
      {status === "live" && canTakedown && <button className="rounded-md border border-red-500/30 px-4 py-2 text-sm font-bold text-red-300" disabled={busy || !note.trim()} onClick={() => action("takedown")} data-testid="admin-release-takedown-button"><RadioTower className="mr-2 inline h-4 w-4" /> Turunkan Rilisan</button>}
      {status === "need_revision" && <button className="rounded-md border border-red-500/30 px-4 py-2 text-sm font-bold text-red-300" disabled={busy || !note.trim()} onClick={() => action("reject")} data-testid="admin-release-reject-button">Tolak</button>}
      {["rejected", "taken_down"].includes(status) && <span className="text-sm text-zinc-500" data-testid="admin-release-no-action">Tidak ada tindakan lanjutan saat ini.</span>}
    </div></div>
    {status === "delivered" && <div className="mt-5 border-t border-white/10 pt-5" data-testid="admin-release-live-identifiers"><div className="grid gap-3 md:grid-cols-2"><label><span className="rm-label">Tanggal Rilis (opsional, boleh diubah)</span><input type="date" className="rm-input" value={releaseDate} onChange={(event) => setReleaseDate(event.target.value)} data-testid="admin-release-live-date-input" /></label><label><span className="rm-label">UPC Rilisan</span><input className="rm-input font-mono uppercase" value={upc} onChange={(event) => setUpc(event.target.value)} data-testid="admin-release-upc-input" /></label>{release.tracks?.map((track) => <label key={track.id}><span className="rm-label">ISRC — {track.track_title}</span><input className="rm-input font-mono uppercase" value={isrcs[track.id] || ""} onChange={(event) => setIsrcs((current) => ({ ...current, [track.id]: event.target.value }))} data-testid={`admin-release-track-isrc-input-${track.id}`} /></label>)}</div><div className="mt-4 flex flex-wrap justify-end gap-2"><button className="rm-btn-ghost inline-flex items-center gap-2" disabled={busy} onClick={() => action("save_identifiers", { upc, track_isrcs: isrcs })} data-testid="admin-release-save-identifiers-button"><Save className="h-4 w-4" /> Simpan UPC/ISRC</button>{canGoLive ? <button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy || !upc.trim()} onClick={() => action("mark_live", { upc, track_isrcs: isrcs, release_date: releaseDate || undefined })} data-testid="admin-release-live-button" title={!upc.trim() ? "UPC wajib diisi sebelum tayang" : undefined}><Send className="h-4 w-4" /> Tandai Tayang</button> : <span className="text-xs text-zinc-500" data-testid="admin-release-live-denied">Perlu izin “Finalisasi Tayang” untuk menandai rilisan tayang.</span>}</div>{canGoLive && !upc.trim() && <p className="mt-1 text-right text-[11px] text-amber-300" data-testid="admin-release-upc-required-hint">UPC wajib terisi untuk menandai tayang.</p>}</div>}
    <div className="mt-5 border-t border-white/10 pt-4" data-testid="admin-release-override-section">
      <button type="button" className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-zinc-400 hover:text-white" onClick={() => setShowOverride((value) => !value)} data-testid="admin-release-override-toggle"><History className="h-4 w-4" /> Koreksi / Mundurkan Status {showOverride ? "▲" : "▼"}</button>
      {showOverride && <div className="mt-3 grid gap-3 md:grid-cols-2">
        <label><span className="rm-label">Ubah status ke (jika salah pilih)</span><select className="rm-input" value={targetStatus} onChange={(event) => setTargetStatus(event.target.value)} data-testid="admin-release-override-select"><option value="">— Pilih status tujuan —</option>{OVERRIDE_STATUSES.filter((s) => s !== status).map((s) => <option key={s} value={s}>{releaseStatusLabel(s)}</option>)}</select></label>
        <label><span className="rm-label">Alasan koreksi (wajib)</span><input className="rm-input" value={note} onChange={(event) => setNote(event.target.value)} placeholder="Contoh: salah pilih status" data-testid="admin-release-override-note" /></label>
        <div className="md:col-span-2 flex justify-end"><button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy || !targetStatus || !note.trim()} onClick={() => action("override_status", { target_status: targetStatus })} data-testid="admin-release-override-apply"><History className="h-4 w-4" /> Terapkan Perubahan Status</button></div>
        <p className="md:col-span-2 text-xs text-zinc-500">Koreksi manual tidak memicu pembayaran/pengiriman otomatis. Gunakan hanya untuk memperbaiki status yang salah dipilih.</p>
      </div>}
    </div>
    {canReview && <div className="mt-5 border-t border-white/10 pt-4" data-testid="admin-release-metadata-edit-section">
      <button type="button" className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-zinc-400 hover:text-white" onClick={openEdit} data-testid="admin-release-metadata-edit-toggle"><PencilLine className="h-4 w-4" /> Edit Metadata {isSuper ? "" : "(perlu persetujuan Super Admin)"} {showEdit ? "▲" : "▼"}</button>
      {release.pending_metadata_edit && <div className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/[0.06] p-3 text-xs text-amber-200" data-testid="admin-release-metadata-pending">
        Ada pengajuan perubahan metadata oleh <strong>{release.pending_metadata_edit.requested_by_name || "admin"}</strong> menunggu persetujuan Super Admin.
        {isSuper && <div className="mt-2 flex gap-2"><button className="rm-btn-primary inline-flex items-center gap-2 text-xs" disabled={editBusy} onClick={() => reviewMetadataEdit("approve")} data-testid="admin-release-metadata-approve"><CheckCircle2 className="h-3.5 w-3.5" /> Setujui & Terapkan</button><button className="rounded-md border border-red-500/30 px-3 py-1 text-xs font-bold text-red-300" disabled={editBusy} onClick={() => reviewMetadataEdit("reject")} data-testid="admin-release-metadata-reject">Tolak</button></div>}
      </div>}
      {showEdit && <div className="mt-3 space-y-3" data-testid="admin-release-metadata-form">
        <div className="grid gap-3 md:grid-cols-2">
          <label><span className="rm-label">Judul Rilisan</span><input className="rm-input" value={editForm.release_title || ""} onChange={(e) => setEditForm((f) => ({ ...f, release_title: e.target.value }))} data-testid="edit-release-title" /></label>
          <label><span className="rm-label">Nama Artis</span><input className="rm-input" value={editForm.artist_name || ""} onChange={(e) => setEditForm((f) => ({ ...f, artist_name: e.target.value }))} data-testid="edit-artist-name" /></label>
          <label><span className="rm-label">Tanggal Rilis</span><input type="date" className="rm-input" value={editForm.release_date || ""} onChange={(e) => setEditForm((f) => ({ ...f, release_date: e.target.value }))} data-testid="edit-release-date" /></label>
          <label><span className="rm-label">Genre</span><input className="rm-input" value={editForm.genre || ""} onChange={(e) => setEditForm((f) => ({ ...f, genre: e.target.value }))} data-testid="edit-genre" /></label>
          <label><span className="rm-label">Subgenre</span><input className="rm-input" value={editForm.subgenre || ""} onChange={(e) => setEditForm((f) => ({ ...f, subgenre: e.target.value }))} /></label>
          <label><span className="rm-label">Bahasa</span><input className="rm-input" value={editForm.language || ""} onChange={(e) => setEditForm((f) => ({ ...f, language: e.target.value }))} /></label>
          <label><span className="rm-label">Copyright (C-Line)</span><input className="rm-input" value={editForm.copyright_line || ""} onChange={(e) => setEditForm((f) => ({ ...f, copyright_line: e.target.value }))} /></label>
          <label><span className="rm-label">P-Line</span><input className="rm-input" value={editForm.p_line || ""} onChange={(e) => setEditForm((f) => ({ ...f, p_line: e.target.value }))} /></label>
        </div>
        <div className="space-y-2">
          <div className="text-[11px] font-bold uppercase tracking-widest text-zinc-500">Metadata Track</div>
          {(release.tracks || []).map((t) => <div key={t.id} className="grid gap-2 rounded-md border border-white/10 bg-white/[0.02] p-2 md:grid-cols-2">
            <label><span className="rm-label">Judul Track #{t.track_number}</span><input className="rm-input" value={editTracks[t.id]?.track_title || ""} onChange={(e) => setEditTracks((s) => ({ ...s, [t.id]: { ...s[t.id], track_title: e.target.value } }))} data-testid={`edit-track-title-${t.id}`} /></label>
            <label><span className="rm-label">ISRC</span><input className="rm-input font-mono uppercase" value={editTracks[t.id]?.isrc || ""} onChange={(e) => setEditTracks((s) => ({ ...s, [t.id]: { ...s[t.id], isrc: e.target.value } }))} data-testid={`edit-track-isrc-${t.id}`} /></label>
          </div>)}
        </div>
        <div className="flex justify-end"><button className="rm-btn-primary inline-flex items-center gap-2" disabled={editBusy} onClick={submitMetadataEdit} data-testid="admin-release-metadata-submit"><Save className="h-4 w-4" /> {isSuper ? "Simpan Perubahan" : "Ajukan Perubahan"}</button></div>
        <p className="text-[11px] text-zinc-500">{isSuper ? "Sebagai Super Admin, perubahan metadata langsung tersimpan meski rilisan sudah tayang (live)." : "Perubahan dikirim ke Super Admin untuk ditinjau sebelum diterapkan — berlaku juga saat rilisan sudah tayang."}</p>
      </div>}
    </div>}
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

    {(release.requires_ppr_payment || release.payment?.type === "pay_per_release" || release.covered_by_subscription === false) && <div className="mt-5 border-t border-white/10 pt-4 space-y-3" data-testid="admin-release-payment-proof">
      <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-zinc-400"><ReceiptText className="h-4 w-4" /> Bukti Pembayaran</div>
      {release.payment ? (() => {
        const pay = release.payment;
        const statusCls = pay.status === "paid" ? "bg-emerald-500/15 text-emerald-300" : pay.status === "pending" ? "bg-amber-500/15 text-amber-300" : "bg-white/[0.06] text-zinc-400";
        return <div className="rounded-lg border border-white/10 bg-white/[0.02] p-4 space-y-3" data-testid="admin-release-payment-proof-card">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="break-all text-sm font-semibold" data-testid="admin-release-payment-proof-invoice">Invoice {pay.reference_id || pay.id}</div>
              <div className="text-xs text-zinc-500" data-testid="admin-release-payment-proof-amount">Nominal {fmtIDR(pay.amount)}</div>
              {pay.paid_at && <div className="mt-0.5 text-xs text-emerald-300" data-testid="admin-release-payment-proof-paid-at">Dibayar {formatDateTime(pay.paid_at)}</div>}
            </div>
            <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${statusCls}`} data-testid="admin-release-payment-proof-status">{PAYMENT_STATUS[pay.status] || pay.status}</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {pay.xendit_invoice_url && <a href={pay.xendit_invoice_url} target="_blank" rel="noreferrer" className="rm-btn-primary inline-flex items-center gap-2 text-sm" data-testid="admin-release-payment-proof-open-xendit"><ExternalLink className="h-4 w-4" /> Buka Halaman Pembayaran</a>}
            <Link to={`/admin/payments?payment_id=${pay.id}`} className="rm-btn-ghost inline-flex items-center gap-2 text-sm" data-testid="admin-release-payment-proof-open-detail"><ArrowUpRight className="h-4 w-4" /> Lihat Detail Pembayaran</Link>
          </div>
          {!pay.xendit_invoice_url && pay.status !== "paid" && <p className="text-[11px] text-zinc-500" data-testid="admin-release-payment-proof-hint">Link halaman pembayaran Xendit tersedia setelah label membuka checkout. Anda tetap dapat memverifikasi status di Detail Pembayaran.</p>}
        </div>;
      })() : (
        <p className="text-sm text-zinc-500" data-testid="admin-release-payment-proof-empty">Invoice pembayaran belum dibuat. Gunakan "Kirim Tautan Pembayaran" untuk menagih pembayaran PPR.</p>
      )}
    </div>}

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
  </div>}</aside>;
};