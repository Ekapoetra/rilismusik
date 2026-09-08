import React, { useState } from "react";
import { ChevronDown, ChevronUp, Undo2 } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { AlertDialog, AlertDialogContent, AlertDialogHeader, AlertDialogTitle, AlertDialogDescription, AlertDialogCancel, AlertDialogFooter } from "@/components/ui/alert-dialog";
import { formatIDR } from "./AdjustmentDialog";

export const AdjustmentHistory = ({ items, labelId, onChanged }) => {
  const [expanded, setExpanded] = useState(null);
  const [target, setTarget] = useState(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const voidEntry = async () => {
    if (busy) return; setBusy(true); setError("");
    try { await api.post(`/royalty/admin/adjustments/labels/${labelId}/${target.id}/void`, { reason }); toast.success("Penyesuaian dibatalkan. Catatan audit tetap tersimpan."); setTarget(null); onChanged(); }
    catch (e) { setError(formatApiError(e.response?.data?.detail) || "Penyesuaian belum dapat dibatalkan."); }
    finally { setBusy(false); }
  };
  return <>
    <div className="divide-y divide-white/10" data-testid="adjustment-history">
      {items.length === 0 ? <p className="py-6 text-sm text-zinc-500" data-testid="adjustment-history-empty">Belum ada penyesuaian yang sesuai.</p> : items.map((item) => <article key={item.id} className="py-4" data-testid={`adjustment-history-${item.id}`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <button type="button" onClick={() => setExpanded(expanded === item.id ? null : item.id)} className="flex min-w-0 items-center gap-3 text-left transition-colors hover:text-emerald-300" aria-expanded={expanded === item.id} data-testid={`adjustment-audit-toggle-${item.id}`}>
            {expanded === item.id ? <ChevronUp className="h-4 w-4 shrink-0" /> : <ChevronDown className="h-4 w-4 shrink-0" />}
            <span className="min-w-0"><span className="block break-all font-mono text-xs text-zinc-400">{item.id}</span><span className="mt-1 block break-words text-lg font-bold text-emerald-300" data-testid={`adjustment-history-amount-${item.id}`}>+ {formatIDR(item.amount_idr)}</span><span className="block break-words text-xs text-zinc-500">{item.created_by_name} · {new Date(item.created_at).toLocaleString("id-ID")}</span></span>
          </button>
          <div className="flex items-center gap-3"><span className={`text-xs ${item.status === "voided" ? "text-red-300" : "text-emerald-300"}`} data-testid={`adjustment-history-status-${item.id}`}>{item.status === "voided" ? "Dibatalkan" : item.withdrawal_status === "paid" ? "Aktif · Sudah ditarik" : item.withdrawal_id ? "Aktif · Dalam penarikan" : "Aktif"}</span>{item.can_void && <button type="button" className="inline-flex items-center gap-1.5 text-xs text-red-300 transition-colors hover:text-red-200" onClick={() => { setTarget(item); setReason(""); setError(""); }} data-testid={`adjustment-void-${item.id}`}><Undo2 className="h-4 w-4" /> Batalkan</button>}</div>
        </div>
        {expanded === item.id && <dl className="mt-4 grid gap-3 border-l border-white/10 pl-4 text-sm sm:grid-cols-2" data-testid={`adjustment-audit-${item.id}`}>
          {[["type", "Jenis / Sumber", "LEGACY_RECONCILIATION / ADMIN_ADJUSTMENT"], ["reason", "Alasan", item.reason], ["reference", "Referensi", item.reference], ["period", "Batas legacy", item.legacy_period_to], ["legacy", "Saldo legacy sebelumnya", formatIDR(item.legacy_balance_before_idr)], ["reference-amount", "Nilai acuan Believe", item.reference_amount_idr === null ? "—" : formatIDR(item.reference_amount_idr)], ["before", "Saldo sebelum penyesuaian", formatIDR(item.balance_before_idr)], ["after", "Saldo setelah penyesuaian", formatIDR(item.balance_after_idr)], ...(item.voided_at ? [["void-reason", "Alasan pembatalan", item.void_reason], ["void-actor", "Dibatalkan oleh", `${item.voided_by_name} · ${new Date(item.voided_at).toLocaleString("id-ID")}`], ["void-balances", "Saldo saat pembatalan", `${formatIDR(item.void_balance_before_idr)} → ${formatIDR(item.void_balance_after_idr)}`]] : [])].map(([key, title, value]) => <div key={key} className="min-w-0"><dt className="text-xs text-zinc-500">{title}</dt><dd className="mt-1 break-words" data-testid={`adjustment-audit-${key}-${item.id}`}>{value}</dd></div>)}
        </dl>}
      </article>)}
    </div>
    <AlertDialog open={Boolean(target)} onOpenChange={(open) => !open && !busy && setTarget(null)}><AlertDialogContent className="w-[calc(100%-2rem)] max-h-[90dvh] overflow-y-auto rounded-lg border-white/15 bg-zinc-950 text-white" data-testid="adjustment-void-dialog"><AlertDialogHeader><AlertDialogTitle data-testid="adjustment-void-title">Batalkan penyesuaian?</AlertDialogTitle><AlertDialogDescription data-testid="adjustment-void-description" className="text-zinc-400">Saldo tersedia akan berkurang {formatIDR(target?.amount_idr)}. Catatan asli tetap tersimpan.</AlertDialogDescription></AlertDialogHeader><label htmlFor="adjustment-void-reason" className="text-sm text-zinc-400">Alasan pembatalan</label><textarea id="adjustment-void-reason" className="rm-input min-h-20 w-full" maxLength={1000} value={reason} onChange={(e) => setReason(e.target.value)} data-testid="adjustment-void-reason" />{error && <p role="alert" className="text-sm text-red-300" data-testid="adjustment-void-error">{error}</p>}<AlertDialogFooter><AlertDialogCancel disabled={busy} data-testid="adjustment-void-cancel" className="border-white/15 bg-transparent hover:bg-white/10 hover:text-white">Kembali</AlertDialogCancel><button type="button" className="rounded-md bg-red-600 px-4 py-2 text-sm font-semibold transition-colors hover:bg-red-500 disabled:opacity-50" disabled={busy || reason.trim().length < 5} onClick={voidEntry} data-testid="adjustment-void-confirm">{busy ? "Membatalkan…" : "Konfirmasi Pembatalan"}</button></AlertDialogFooter></AlertDialogContent></AlertDialog>
  </>;
};