import React, { useState } from "react";
import { ArrowLeft, Check, Loader2 } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";

export const formatIDR = (value) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(value || 0);
export const AdjustmentDialog = ({ label, boundary, onClose, onChanged }) => {
  const storageKey = `royalty-adjustment-preview:${label.id}`;
  const [preview, setPreview] = useState(() => {
    try { const saved = JSON.parse(sessionStorage.getItem(storageKey)); return saved?.label_id === label.id && new Date(saved.expires_at) > new Date() ? saved : null; } catch { return null; }
  });
  const [form, setForm] = useState({ amount_idr: "", reference_amount_idr: "", reason: "", reference: "", legacy_period_to: boundary || "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const base = `/royalty/admin/adjustments/labels/${label.id}`;
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  const review = async (event) => {
    event.preventDefault(); if (busy) return;
    setError(""); setBusy(true);
    try {
      const { data } = await api.post(`${base}/preview`, { ...form, amount_idr: Number(form.amount_idr), reference_amount_idr: form.reference_amount_idr === "" ? null : Number(form.reference_amount_idr), currency: "IDR", adjustment_type: "LEGACY_RECONCILIATION" });
      setPreview(data); sessionStorage.setItem(storageKey, JSON.stringify(data));
    } catch (e) { setError(formatApiError(e.response?.data?.detail) || "Pratinjau belum dapat dibuat."); }
    finally { setBusy(false); }
  };
  const confirm = async () => {
    if (busy) return; setBusy(true); setError("");
    try {
      const { data } = await api.post(base, { preview_id: preview.preview_id });
      sessionStorage.removeItem(storageKey);
      toast.success(`${data.replayed ? "Penyesuaian sudah tercatat" : "Penyesuaian berhasil dicatat"}. Saldo tersedia ${formatIDR(data.balance_available_idr)}.`);
      onClose(); onChanged();
    } catch (e) { setError(formatApiError(e.response?.data?.detail) || "Konfirmasi belum diterima. Coba kembali dengan pratinjau yang sama."); }
    finally { setBusy(false); }
  };
  return <Dialog open onOpenChange={(value) => !value && !busy && onClose()}>
    <DialogContent className="w-[calc(100%-2rem)] max-h-[90dvh] overflow-y-auto max-w-xl rounded-lg border-white/15 bg-zinc-950 text-white data-[state=open]:animate-none" data-testid="adjustment-dialog" data-step={preview ? "preview" : "input"} aria-busy={busy} closeTestId="adjustment-dialog-close">
      <DialogHeader className="text-left"><DialogTitle data-testid="adjustment-dialog-title">{preview ? "Konfirmasi Penyesuaian Royalti" : "Inject Saldo"}</DialogTitle><DialogDescription className="break-words text-zinc-400" data-testid="adjustment-target-label">{label.label_name} · Rekonsiliasi Legacy</DialogDescription></DialogHeader>
      {preview ? <div className="space-y-4" data-testid="adjustment-preview">
        <dl className="divide-y divide-white/10 text-sm" data-testid="adjustment-preview-balances">
          {[["before", "Saldo tersedia saat ini", preview.balance_before_idr], ["amount", "Penambahan saldo", preview.amount_idr], ["after", "Saldo tersedia setelah penyesuaian", preview.balance_after_idr]].map(([key, title, amount]) => <div key={key} className="flex flex-wrap justify-between gap-2 py-3"><dt className="text-zinc-400">{title}</dt><dd className={`break-words font-mono font-bold ${key === "after" ? "text-emerald-300" : "text-white"}`} data-testid={`adjustment-preview-${key}`}>{key === "amount" ? "+ " : ""}{formatIDR(amount)}</dd></div>)}
        </dl>
        <div className="space-y-2 break-words text-sm text-zinc-300">
          <p data-testid="adjustment-preview-legacy-balance"><span className="text-zinc-500">Believe legacy:</span> {formatIDR(preview.legacy_balance_before_idr)}</p>
          <p data-testid="adjustment-preview-new-royalty"><span className="text-zinc-500">Royalti setelah batas legacy:</span> {formatIDR(preview.new_royalty_before_idr)}</p>
          <p data-testid="adjustment-preview-existing-adjustments"><span className="text-zinc-500">Penyesuaian sebelumnya, belum ditarik:</span> {formatIDR(preview.existing_adjustment_idr)}</p>
          <p data-testid="adjustment-preview-boundary"><span className="text-zinc-500">Batas legacy:</span> {preview.legacy_period_to}</p>
          <p data-testid="adjustment-preview-reason"><span className="text-zinc-500">Alasan:</span> {preview.reason}</p>
          <p data-testid="adjustment-preview-reference"><span className="text-zinc-500">Referensi:</span> {preview.reference}</p>
          {preview.reference_amount_idr !== null && <p data-testid="adjustment-preview-reference-amount"><span className="text-zinc-500">Nilai acuan Believe:</span> {formatIDR(preview.reference_amount_idr)}</p>}
        </div>
        <div className="flex flex-wrap justify-between gap-3 pt-2"><button type="button" className="rm-btn-ghost inline-flex items-center gap-2" disabled={busy} data-testid="adjustment-preview-back" onClick={() => { setForm({ amount_idr: String(preview.amount_idr), reference_amount_idr: preview.reference_amount_idr === null ? "" : String(preview.reference_amount_idr), reason: preview.reason, reference: preview.reference, legacy_period_to: preview.legacy_period_to }); setPreview(null); setError(""); sessionStorage.removeItem(storageKey); }}><ArrowLeft className="h-4 w-4" /> Ubah</button><button type="button" className="rm-btn-primary inline-flex items-center gap-2 disabled:opacity-50" disabled={busy} onClick={confirm} data-testid="adjustment-confirm">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}{busy ? "Mencatat…" : "Konfirmasi Penyesuaian"}</button></div>
      </div> : <form onSubmit={review} className="space-y-4" data-testid="adjustment-form">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Penambahan saldo (Rp)" id="adjustment-amount"><input id="adjustment-amount" data-testid="adjustment-amount" className="rm-input w-full min-w-0" type="number" inputMode="numeric" min="1" max="999999999999" step="1" required value={form.amount_idr} onChange={(e) => update("amount_idr", e.target.value)} /></Field>
          <Field label="Bulan terakhir legacy" id="adjustment-legacy-period"><input id="adjustment-legacy-period" data-testid="adjustment-legacy-period" className="rm-input w-full min-w-0" type="month" required value={form.legacy_period_to} onChange={(e) => update("legacy_period_to", e.target.value)} /></Field>
        </div>
        <Field label="Nilai acuan Believe (Rp, opsional)" id="adjustment-reference-amount"><input id="adjustment-reference-amount" data-testid="adjustment-reference-amount" className="rm-input w-full" type="number" inputMode="numeric" min="0" max="999999999999" step="1" value={form.reference_amount_idr} onChange={(e) => update("reference_amount_idr", e.target.value)} /></Field>
        <Field label="Alasan penyesuaian" id="adjustment-reason"><textarea id="adjustment-reason" data-testid="adjustment-reason" className="rm-input min-h-20 w-full" minLength={5} maxLength={1000} required value={form.reason} onChange={(e) => update("reason", e.target.value)} /></Field>
        <Field label="Referensi / sumber verifikasi" id="adjustment-reference"><input id="adjustment-reference" data-testid="adjustment-reference" className="rm-input w-full" minLength={3} maxLength={240} required value={form.reference} onChange={(e) => update("reference", e.target.value)} /></Field>
        <div className="flex flex-wrap justify-end gap-3"><button type="button" className="rm-btn-ghost" disabled={busy} onClick={onClose} data-testid="adjustment-cancel">Batal</button><button type="submit" disabled={busy} className="rm-btn-primary disabled:opacity-50" data-testid="adjustment-preview-submit">{busy ? "Memeriksa…" : "Tinjau Penyesuaian"}</button></div>
      </form>}
      {error && <p role="alert" className="break-words rounded-md bg-red-500/10 p-3 text-sm text-red-300" data-testid="adjustment-error">{error}</p>}
    </DialogContent>
  </Dialog>;
};
const Field = ({ id, label, children }) => <div className="min-w-0"><label htmlFor={id} className="mb-1.5 block text-sm text-zinc-400">{label}</label>{children}</div>;