import React, { useEffect, useState } from "react";
import { CheckCircle2, CreditCard, RadioTower, Send, ShieldCheck, SquareArrowOutUpRight, XCircle, History } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { releaseStatusLabel } from "@/utils/releasePresentation";

const OVERRIDE_STATUSES = ["draft", "submitted", "under_review", "approved", "delivered", "live", "need_revision", "rejected", "taken_down"];

export const AdminReleaseWorkflow = ({ release, onUpdated, setMessage, setError }) => {
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [upc, setUpc] = useState(release.upc || "");
  const [isrcs, setIsrcs] = useState({});
  const [showOverride, setShowOverride] = useState(false);
  const [targetStatus, setTargetStatus] = useState("");
  useEffect(() => { setUpc(release.upc || ""); setIsrcs(Object.fromEntries((release.tracks || []).map((track) => [track.id, track.isrc || ""]))); }, [release]);
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
  return <aside className="sticky bottom-4 border border-white/15 bg-zinc-950/95 p-4 shadow-2xl backdrop-blur" data-testid="admin-release-workflow"><div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between"><div><div className="text-xs font-bold uppercase text-zinc-500">Tindakan Berikutnya</div><div className="mt-1 text-sm text-zinc-300" data-testid="admin-release-workflow-status">Status saat ini: <strong className="text-white">{releaseStatusLabel(status)}</strong></div></div>
    {["submitted", "under_review", "need_revision", "live"].includes(status) && <label className="min-w-72 flex-1 lg:max-w-xl"><span className="rm-label">Catatan / alasan</span><textarea className="rm-input min-h-20" value={note} onChange={(event) => setNote(event.target.value)} data-testid="admin-release-note-input" /></label>}
    <div className="flex flex-wrap gap-2">
      {status === "submitted" && <><button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => action("start_review")} data-testid="admin-release-start-review-button"><ShieldCheck className="h-4 w-4" /> Mulai Pemeriksaan</button><button className="rm-btn-ghost" disabled={busy || !note.trim()} onClick={() => action("need_revision")} data-testid="admin-release-need-revision-button">Minta Revisi</button><button className="rounded-md border border-red-500/30 px-4 py-2 text-sm font-bold text-red-300" disabled={busy || !note.trim()} onClick={() => action("reject")} data-testid="admin-release-reject-button"><XCircle className="mr-2 inline h-4 w-4" /> Tolak</button></>}
      {status === "under_review" && <>{release.billing_flow === "pay_per_release" || release.payment_status === "not_generated" ? <button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => action("send_payment")} data-testid="admin-release-send-payment-button"><CreditCard className="h-4 w-4" /> Kirim Tautan Pembayaran</button> : <button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => action("approve")} data-testid="admin-release-approve-button"><CheckCircle2 className="h-4 w-4" /> Setujui</button>}<button className="rm-btn-ghost" disabled={busy || !note.trim()} onClick={() => action("need_revision")} data-testid="admin-release-need-revision-button">Minta Revisi</button><button className="rounded-md border border-red-500/30 px-4 py-2 text-sm font-bold text-red-300" disabled={busy || !note.trim()} onClick={() => action("reject")} data-testid="admin-release-reject-button">Tolak</button></>}
      {status === "awaiting_payment" && <div className="flex items-center gap-2 text-sm text-amber-300" data-testid="admin-release-awaiting-payment"><CreditCard className="h-4 w-4" /> Menunggu pembayaran label</div>}
      {status === "paid" && <button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => action("approve")} data-testid="admin-release-approve-button"><CheckCircle2 className="h-4 w-4" /> Setujui</button>}
      {status === "approved" && <button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => action("deliver")} data-testid="admin-release-deliver-button"><SquareArrowOutUpRight className="h-4 w-4" /> Kirim ke Believe</button>}
      {status === "live" && <button className="rounded-md border border-red-500/30 px-4 py-2 text-sm font-bold text-red-300" disabled={busy || !note.trim()} onClick={() => action("takedown")} data-testid="admin-release-takedown-button"><RadioTower className="mr-2 inline h-4 w-4" /> Turunkan Rilisan</button>}
      {status === "need_revision" && <button className="rounded-md border border-red-500/30 px-4 py-2 text-sm font-bold text-red-300" disabled={busy || !note.trim()} onClick={() => action("reject")} data-testid="admin-release-reject-button">Tolak</button>}
      {["rejected", "taken_down"].includes(status) && <span className="text-sm text-zinc-500" data-testid="admin-release-no-action">Tidak ada tindakan lanjutan saat ini.</span>}
    </div></div>
    {status === "delivered" && <div className="mt-5 border-t border-white/10 pt-5" data-testid="admin-release-live-identifiers"><div className="grid gap-3 md:grid-cols-2"><label><span className="rm-label">UPC Rilisan</span><input className="rm-input font-mono uppercase" value={upc} onChange={(event) => setUpc(event.target.value)} data-testid="admin-release-upc-input" /></label>{release.tracks?.map((track) => <label key={track.id}><span className="rm-label">ISRC — {track.track_title}</span><input className="rm-input font-mono uppercase" value={isrcs[track.id] || ""} onChange={(event) => setIsrcs((current) => ({ ...current, [track.id]: event.target.value }))} data-testid={`admin-release-track-isrc-input-${track.id}`} /></label>)}</div><div className="mt-4 flex justify-end"><button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => action("mark_live", { upc, track_isrcs: isrcs })} data-testid="admin-release-live-button"><Send className="h-4 w-4" /> Simpan ISRC/UPC & Tandai Tayang</button></div></div>}
    <div className="mt-5 border-t border-white/10 pt-4" data-testid="admin-release-override-section">
      <button type="button" className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-zinc-400 hover:text-white" onClick={() => setShowOverride((value) => !value)} data-testid="admin-release-override-toggle"><History className="h-4 w-4" /> Koreksi / Mundurkan Status {showOverride ? "▲" : "▼"}</button>
      {showOverride && <div className="mt-3 grid gap-3 md:grid-cols-2">
        <label><span className="rm-label">Ubah status ke (jika salah pilih)</span><select className="rm-input" value={targetStatus} onChange={(event) => setTargetStatus(event.target.value)} data-testid="admin-release-override-select"><option value="">— Pilih status tujuan —</option>{OVERRIDE_STATUSES.filter((s) => s !== status).map((s) => <option key={s} value={s}>{releaseStatusLabel(s)}</option>)}</select></label>
        <label><span className="rm-label">Alasan koreksi (wajib)</span><input className="rm-input" value={note} onChange={(event) => setNote(event.target.value)} placeholder="Contoh: salah pilih status" data-testid="admin-release-override-note" /></label>
        <div className="md:col-span-2 flex justify-end"><button className="rm-btn-primary inline-flex items-center gap-2" disabled={busy || !targetStatus || !note.trim()} onClick={() => action("override_status", { target_status: targetStatus })} data-testid="admin-release-override-apply"><History className="h-4 w-4" /> Terapkan Perubahan Status</button></div>
        <p className="md:col-span-2 text-xs text-zinc-500">Koreksi manual tidak memicu pembayaran/pengiriman otomatis. Gunakan hanya untuk memperbaiki status yang salah dipilih.</p>
      </div>}
    </div>
  </aside>;
};