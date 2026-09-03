import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, CheckCircle2, LoaderCircle, PlayCircle } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  formatDateTime, formatIDR, paymentMethodLabel, PAYMENT_STATUS, PAYMENT_TYPES, SERVICE_STATUS,
} from "./paymentPresentation";

function DetailRow({ label, value, testId, strong = false }) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] gap-4 border-b border-white/5 py-3 last:border-0">
      <dt className="text-xs text-zinc-500">{label}</dt>
      <dd className={`break-words text-right text-sm ${strong ? "font-bold text-white" : "text-zinc-300"}`} data-testid={testId}>{value || "—"}</dd>
    </div>
  );
}

function PaymentActionPanel({ payment, busy, onAction }) {
  if (payment.status !== "paid") return null;
  if (payment.type === "pay_per_release") {
    return (
      <div className="border-t border-white/10 pt-4" data-testid="payment-detail-release-action">
        <p className="mb-3 text-sm text-zinc-300">Pembayaran sudah diterima. Rilisan dapat dilanjutkan ke proses distribusi.</p>
        {payment.admin_action_path && <Link className="rm-btn-primary inline-flex items-center gap-2" to={payment.admin_action_path} data-testid="payment-detail-open-release-button">Buka Release <ArrowUpRight className="h-4 w-4" /></Link>}
      </div>
    );
  }
  if (payment.type === "custom_service") {
    const completed = payment.service_status === "completed";
    return (
      <div className="border-t border-white/10 pt-4" data-testid="payment-detail-custom-action">
        <p className="mb-3 text-sm text-zinc-300">Perbarui progres agar tim admin mengetahui pekerjaan yang masih aktif.</p>
        {completed ? (
          <div className="flex items-center gap-2 text-sm font-semibold text-emerald-300" data-testid="payment-detail-custom-completed"><CheckCircle2 className="h-4 w-4" /> Layanan selesai</div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {payment.service_status !== "in_progress" && <button type="button" className="rm-btn-ghost inline-flex items-center gap-2" disabled={busy} onClick={() => onAction("in_progress")} data-testid="payment-detail-mark-in-progress-button"><PlayCircle className="h-4 w-4" /> Tandai Sedang Dikerjakan</button>}
            <button type="button" className="rm-btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => onAction("completed")} data-testid="payment-detail-mark-completed-button">{busy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />} Tandai Selesai</button>
          </div>
        )}
      </div>
    );
  }
  if (payment.type === "wami_addon") {
    return <div className="border-t border-white/10 pt-4"><Link className="rm-btn-primary inline-flex items-center gap-2" to="/admin/wami" data-testid="payment-detail-open-wami-button">Buka WAMI <ArrowUpRight className="h-4 w-4" /></Link></div>;
  }
  return <div className="border-t border-white/10 pt-4 text-sm text-emerald-300" data-testid="payment-detail-automatic-info"><CheckCircle2 className="mr-2 inline h-4 w-4" />Langganan telah aktif otomatis. Tidak ada tindakan manual.</div>;
}

export default function PaymentDetailDialog({ payment, onClose, onUpdated, onMessage }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (!payment) return null;

  const updateAction = async (action) => {
    setBusy(true); setError("");
    try {
      const { data } = await api.post(`/payments/admin/${payment.id}/action`, { action });
      onUpdated(data);
      onMessage(action === "completed" ? "Layanan ditandai selesai." : "Layanan sedang dikerjakan.");
    } catch (requestError) {
      setError(formatApiError(requestError.response?.data?.detail));
    } finally { setBusy(false); }
  };

  return (
    <Dialog open onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-h-[88vh] max-w-2xl overflow-y-auto border-white/10 bg-zinc-950 text-zinc-100" closeTestId="payment-detail-close-button" data-testid="payment-detail-dialog">
        <DialogHeader>
          <DialogTitle className="font-display text-2xl font-extrabold">Detail Pembayaran</DialogTitle>
          <DialogDescription className="text-zinc-400">Invoice dan tindak lanjut operasional.</DialogDescription>
        </DialogHeader>
        {error && <div className="rounded-md bg-red-500/15 px-4 py-3 text-sm text-red-300" data-testid="payment-detail-error">{error}</div>}
        <dl className="border-y border-white/10">
          <DetailRow label="Invoice" value={payment.reference_id || payment.id} testId="payment-detail-invoice" />
          <DetailRow label="Label" value={payment.label_name} testId="payment-detail-label" strong />
          <DetailRow label="Email label" value={payment.label_email} testId="payment-detail-label-email" />
          <DetailRow label="Jenis layanan" value={PAYMENT_TYPES[payment.type] || payment.type} testId="payment-detail-type" />
          <DetailRow label="Layanan" value={payment.description} testId="payment-detail-description" />
          <DetailRow label="Metode pembayaran" value={paymentMethodLabel(payment.payment_method)} testId="payment-detail-method" />
          <DetailRow label="Nominal" value={formatIDR(payment.amount)} testId="payment-detail-amount" strong />
          <DetailRow label="Status pembayaran" value={PAYMENT_STATUS[payment.status] || payment.status} testId="payment-detail-status" />
          <DetailRow label="Status tindakan" value={SERVICE_STATUS[payment.admin_action_status] || payment.admin_action_status} testId="payment-detail-action-status" />
          <DetailRow label="Dibuat" value={formatDateTime(payment.created_at)} testId="payment-detail-created-at" />
          <DetailRow label="Dibayar" value={formatDateTime(payment.paid_at)} testId="payment-detail-paid-at" />
        </dl>
        {payment.line_items?.length > 0 && <div data-testid="payment-detail-line-items"><h3 className="mb-2 text-xs font-bold uppercase text-zinc-500">Rincian Invoice</h3><div className="divide-y divide-white/5">{payment.line_items.map((item, index) => <div className="flex items-start justify-between gap-4 py-2 text-sm" key={`${item.reference_id || item.name}-${index}`}><span className="text-zinc-300">{item.name}</span><strong className="whitespace-nowrap">{formatIDR((item.amount || 0) * (item.quantity || 1))}</strong></div>)}</div></div>}
        <PaymentActionPanel payment={payment} busy={busy} onAction={updateAction} />
        <DialogFooter><button type="button" className="rm-btn-ghost" onClick={onClose} data-testid="payment-detail-footer-close-button">Tutup</button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}