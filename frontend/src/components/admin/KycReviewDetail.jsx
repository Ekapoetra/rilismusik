import React, { useState } from "react";
import { CheckCircle2, FileWarning, Loader2, ShieldCheck } from "lucide-react";
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
  const label = detail?.label;
  const kyc = detail?.kyc;
  if (!detail) return <div className="grid min-h-96 place-items-center border-y border-white/10 text-sm text-zinc-500" data-testid="admin-kyc-empty-detail">Pilih pengajuan untuk melihat detail.</div>;

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
      <div className="overflow-hidden rounded-lg border border-white/10 bg-black/30 p-3" data-testid="admin-kyc-ktp-preview"><img src={`/api/admin/kyc/${label.id}/ktp?v=${encodeURIComponent(kyc.document?.uploaded_at || "current")}`} alt={`KTP ${label.label_name}`} className="mx-auto aspect-[1.58/1] max-h-72 w-full object-contain" /></div>
    </div>
    {label.logo_url && <div className="flex items-center gap-3 text-sm text-zinc-400"><img src={fileUrl(label.logo_url)} alt={`Logo ${label.label_name}`} className="h-12 w-12 rounded-md border border-white/10 object-contain" data-testid="admin-kyc-logo-preview" /><span>Logo label terunggah</span></div>}
    {kyc.status === "pending_review" && canReview && <div className="flex flex-wrap justify-end gap-3 border-t border-white/10 pt-5"><button type="button" className="rm-btn-ghost inline-flex items-center gap-2 text-red-300" onClick={() => setRejectOpen(true)} disabled={busy} data-testid="admin-kyc-reject-button"><FileWarning className="h-4 w-4" /> Tolak</button><button type="button" className="rm-btn-primary inline-flex items-center gap-2" onClick={() => review("approve")} disabled={busy || !kyc.prerequisites_complete} data-testid="admin-kyc-approve-button">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />} Setujui Verifikasi</button></div>}
    <Dialog open={rejectOpen} onOpenChange={setRejectOpen}><DialogContent className="border-white/10 bg-[#0F0F0F] text-white" closeTestId="admin-kyc-reject-close"><DialogHeader><DialogTitle className="font-display text-xl">Tolak pengajuan Verifikasi Akun</DialogTitle><DialogDescription className="text-zinc-400">Alasan akan dikirim ke label dan wajib menjelaskan data yang perlu diperbaiki.</DialogDescription></DialogHeader><Textarea value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Contoh: Foto KTP buram dan nomor identitas tidak terbaca." className="min-h-28 border-white/10 bg-white/[0.04]" data-testid="admin-kyc-rejection-reason-input" /><DialogFooter><button type="button" className="rm-btn-ghost" onClick={() => setRejectOpen(false)} data-testid="admin-kyc-reject-cancel">Batal</button><button type="button" className="rounded-full bg-red-500 px-6 py-2.5 text-sm font-bold text-white transition-colors hover:bg-red-400 disabled:opacity-40" onClick={() => review("reject")} disabled={busy || !reason.trim()} data-testid="admin-kyc-reject-confirm">{busy ? "Memproses…" : "Konfirmasi Penolakan"}</button></DialogFooter></DialogContent></Dialog>
  </section>;
};