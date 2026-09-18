import React, { useRef, useState } from "react";
import { CheckCircle2, FileWarning, Loader2, ShieldCheck, ZoomIn, ZoomOut, RotateCcw, Maximize2 } from "lucide-react";
import { api, fileUrl, formatApiError } from "@/api/client";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/sonner";

const Row = ({ label, value, testId }) => <div className="flex justify-between gap-4 border-b border-white/5 py-2.5 text-sm last:border-0"><span className="text-zinc-500">{label}</span><strong className="max-w-[65%] text-right text-zinc-200" data-testid={testId}>{value || "—"}</strong></div>;

export const KycReviewDetail = ({ detail, onReviewed, canReview = false }) => {
  const [rejectOpen, setRejectOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [ktpOpen, setKtpOpen] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragRef = useRef(null);
  const label = detail?.label;
  const kyc = detail?.kyc;
  if (!detail) return <div className="grid min-h-96 place-items-center border-y border-white/10 text-sm text-zinc-500" data-testid="admin-kyc-empty-detail">Pilih pengajuan untuk melihat detail.</div>;

  const ktpSrc = `/api/admin/kyc/${label.id}/ktp?v=${encodeURIComponent(kyc.document?.uploaded_at || "current")}`;
  const clampZoom = (z) => Math.min(5, Math.max(1, z));
  const resetView = () => { setZoom(1); setPan({ x: 0, y: 0 }); };
  const openKtp = () => { resetView(); setKtpOpen(true); };
  const adjustZoom = (delta) => setZoom((z) => { const nz = clampZoom(Number((z + delta).toFixed(2))); if (nz === 1) setPan({ x: 0, y: 0 }); return nz; });
  const onWheel = (e) => { e.preventDefault(); adjustZoom(e.deltaY < 0 ? 0.25 : -0.25); };
  const onPointerDown = (e) => { if (zoom <= 1) return; dragRef.current = { startX: e.clientX, startY: e.clientY, panX: pan.x, panY: pan.y }; e.currentTarget.setPointerCapture(e.pointerId); };
  const onPointerMove = (e) => { if (!dragRef.current) return; setPan({ x: dragRef.current.panX + (e.clientX - dragRef.current.startX), y: dragRef.current.panY + (e.clientY - dragRef.current.startY) }); };
  const onPointerUp = (e) => { dragRef.current = null; try { e.currentTarget.releasePointerCapture(e.pointerId); } catch { /* noop */ } };

  const review = async (action) => {
    setBusy(true); setError("");
    try {
      await api.post(`/admin/kyc/${label.id}/action`, { action, reason: action === "reject" ? reason : null });
      setRejectOpen(false); setReason(""); await onReviewed();
      toast.success(action === "approve" ? "Verifikasi Akun disetujui." : "Pengajuan Verifikasi Akun ditolak.");
    } catch (err) { setError(formatApiError(err.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  return <section className="space-y-6" data-testid="admin-kyc-review-detail">
    <div className="flex flex-wrap items-start justify-between gap-4"><div><div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Review Identitas</div><h2 className="mt-1 font-display text-2xl font-extrabold" data-testid="admin-kyc-detail-label-name">{label.label_name}</h2></div><span className="rm-badge border border-amber-400/30 bg-amber-400/10 text-amber-200" data-testid="admin-kyc-detail-status">{kyc.status}</span></div>
    {error && <div role="alert" className="rounded-lg border border-red-400/30 bg-red-400/10 p-3 text-sm text-red-200" data-testid="admin-kyc-review-error">{error}</div>}
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="border-y border-white/10 py-4"><Row label="PIC" value={label.pic_name || detail.user?.name} testId="admin-kyc-detail-pic" /><Row label="Email" value={detail.user?.email} testId="admin-kyc-detail-email" /><Row label="WhatsApp" value={label.whatsapp} testId="admin-kyc-detail-whatsapp" /><Row label="Alamat" value={[label.address, label.city].filter(Boolean).join(", ")} testId="admin-kyc-detail-address" /><Row label="Rekening" value={detail.bank ? `${detail.bank.bank_name} · ${detail.bank.account_number}` : "Belum tersedia"} testId="admin-kyc-detail-bank" /></div>
      <div className="overflow-hidden rounded-lg border border-white/10 bg-black/30 p-3" data-testid="admin-kyc-ktp-preview"><button type="button" onClick={openKtp} className="group relative block w-full cursor-zoom-in overflow-hidden rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40" data-testid="admin-kyc-ktp-open-button" aria-label="Perbesar foto KTP"><img src={ktpSrc} alt={`KTP ${label.label_name}`} className="mx-auto aspect-[1.58/1] max-h-72 w-full object-contain transition-transform duration-300 group-hover:scale-[1.02]" /><span className="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/0 opacity-0 transition-all duration-200 group-hover:bg-black/40 group-hover:opacity-100"><span className="inline-flex items-center gap-2 rounded-full bg-white/15 px-4 py-2 text-xs font-semibold text-white backdrop-blur"><Maximize2 className="h-4 w-4" /> Klik untuk perbesar</span></span></button></div>
    </div>
    {label.logo_url && <div className="flex items-center gap-3 text-sm text-zinc-400"><img src={fileUrl(label.logo_url)} alt={`Logo ${label.label_name}`} className="h-12 w-12 rounded-md border border-white/10 object-contain" data-testid="admin-kyc-logo-preview" /><span>Logo label terunggah</span></div>}
    {kyc.status === "pending_review" && canReview && <div className="flex flex-wrap justify-end gap-3 border-t border-white/10 pt-5"><button type="button" className="rm-btn-ghost inline-flex items-center gap-2 text-red-300" onClick={() => setRejectOpen(true)} disabled={busy} data-testid="admin-kyc-reject-button"><FileWarning className="h-4 w-4" /> Tolak</button><button type="button" className="rm-btn-primary inline-flex items-center gap-2" onClick={() => review("approve")} disabled={busy || !kyc.prerequisites_complete} data-testid="admin-kyc-approve-button">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />} Setujui Verifikasi</button></div>}
    <Dialog open={rejectOpen} onOpenChange={setRejectOpen}><DialogContent className="border-white/10 bg-[#0F0F0F] text-white" closeTestId="admin-kyc-reject-close"><DialogHeader><DialogTitle className="font-display text-xl">Tolak pengajuan Verifikasi Akun</DialogTitle><DialogDescription className="text-zinc-400">Alasan akan dikirim ke label dan wajib menjelaskan data yang perlu diperbaiki.</DialogDescription></DialogHeader><Textarea value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Contoh: Foto KTP buram dan nomor identitas tidak terbaca." className="min-h-28 border-white/10 bg-white/[0.04]" data-testid="admin-kyc-rejection-reason-input" /><DialogFooter><button type="button" className="rm-btn-ghost" onClick={() => setRejectOpen(false)} data-testid="admin-kyc-reject-cancel">Batal</button><button type="button" className="rounded-full bg-red-500 px-6 py-2.5 text-sm font-bold text-white transition-colors hover:bg-red-400 disabled:opacity-40" onClick={() => review("reject")} disabled={busy || !reason.trim()} data-testid="admin-kyc-reject-confirm">{busy ? "Memproses…" : "Konfirmasi Penolakan"}</button></DialogFooter></DialogContent></Dialog>
    <Dialog open={ktpOpen} onOpenChange={(o) => { setKtpOpen(o); if (!o) resetView(); }}>
      <DialogContent className="max-w-4xl border-white/10 bg-[#0A0A0A] p-0 text-white" closeTestId="admin-kyc-ktp-close">
        <DialogHeader className="border-b border-white/10 px-5 py-4">
          <DialogTitle className="font-display text-lg">Foto KTP · {label.label_name}</DialogTitle>
          <DialogDescription className="text-zinc-500">Gulir untuk zoom, seret gambar untuk menggeser saat diperbesar.</DialogDescription>
        </DialogHeader>
        <div className="relative select-none overflow-hidden bg-[radial-gradient(circle_at_center,#1a1a1a,#000)]" style={{ height: "min(70vh, 560px)" }} onWheel={onWheel} data-testid="admin-kyc-ktp-lightbox">
          <img
            src={ktpSrc}
            alt={`KTP ${label.label_name} ukuran penuh`}
            draggable={false}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            className="mx-auto h-full w-full object-contain transition-transform duration-100"
            style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, cursor: zoom > 1 ? (dragRef.current ? "grabbing" : "grab") : "default" }}
            data-testid="admin-kyc-ktp-fullimage"
          />
          <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 items-center gap-1 rounded-full border border-white/10 bg-black/60 px-2 py-1.5 backdrop-blur">
            <button type="button" onClick={() => adjustZoom(-0.25)} disabled={zoom <= 1} className="grid h-8 w-8 place-items-center rounded-full text-white/80 transition-colors hover:bg-white/10 disabled:opacity-30" data-testid="admin-kyc-ktp-zoom-out" aria-label="Perkecil"><ZoomOut className="h-4 w-4" /></button>
            <span className="min-w-14 text-center text-xs font-semibold tabular-nums text-white/80" data-testid="admin-kyc-ktp-zoom-level">{Math.round(zoom * 100)}%</span>
            <button type="button" onClick={() => adjustZoom(0.25)} disabled={zoom >= 5} className="grid h-8 w-8 place-items-center rounded-full text-white/80 transition-colors hover:bg-white/10 disabled:opacity-30" data-testid="admin-kyc-ktp-zoom-in" aria-label="Perbesar"><ZoomIn className="h-4 w-4" /></button>
            <span className="mx-1 h-5 w-px bg-white/10" />
            <button type="button" onClick={resetView} className="grid h-8 w-8 place-items-center rounded-full text-white/80 transition-colors hover:bg-white/10" data-testid="admin-kyc-ktp-reset" aria-label="Atur ulang"><RotateCcw className="h-4 w-4" /></button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  </section>;
};