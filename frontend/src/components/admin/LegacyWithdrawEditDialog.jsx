import React, { useEffect, useRef, useState } from "react";
import { AlertTriangle, ArrowRight, CheckCircle2, Loader2 } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";

const fmtIDR = (value) => new Intl.NumberFormat("id-ID", {
  style: "currency", currency: "IDR", maximumFractionDigits: 0,
}).format(value || 0);

function ChangeRow({ label, before, after, testId }) {
  return <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4 border-b border-white/5 py-3 last:border-0"><span className="text-xs text-zinc-500">{label}</span><div className="flex min-w-0 items-center gap-2 text-sm font-semibold" data-testid={testId}><span className="text-zinc-500">{before}</span><ArrowRight className="h-3.5 w-3.5 shrink-0 text-zinc-600" /><span className="break-words text-right text-white">{after}</span></div></div>;
}

export const LegacyWithdrawEditDialog = ({ withdrawal, onClose, onComplete }) => {
  const [periodTo, setPeriodTo] = useState(withdrawal?.period_to || "");
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [job, setJob] = useState(null);
  const pollRef = useRef(null);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);
  useEffect(() => {
    if (!withdrawal || !periodTo || periodTo === withdrawal.period_to || busy || job?.status === "done") return undefined;
    setPreview(null); setError("");
    const timer = setTimeout(async () => {
      try {
        const { data } = await api.post(`/withdraw/admin/${withdrawal.id}/legacy-edit/preview`, { period_to: periodTo });
        setPreview(data);
      } catch (requestError) { setError(formatApiError(requestError.response?.data?.detail)); }
    }, 350);
    return () => clearTimeout(timer);
  }, [periodTo, withdrawal, busy, job?.status]);

  const pollJob = (jobId) => {
    if (pollRef.current) clearInterval(pollRef.current);
    const check = async () => {
      try {
        const { data } = await api.get(`/admin/migrate/jobs/${jobId}`);
        setJob(data);
        if (["done", "error"].includes(data.status)) {
          clearInterval(pollRef.current); pollRef.current = null; setBusy(false);
          if (data.status === "error") {
            setError(data.error_message || "Perubahan gagal diproses");
            setPreview(null);
          } else await onComplete(data.result);
        }
      } catch (requestError) {
        clearInterval(pollRef.current); pollRef.current = null; setBusy(false);
        setError(formatApiError(requestError.response?.data?.detail));
      }
    };
    pollRef.current = setInterval(check, 2000); check();
  };

  const save = async () => {
    setBusy(true); setError("");
    try {
      const { data } = await api.post(`/withdraw/admin/${withdrawal.id}/legacy-edit`, { preview_id: preview.preview_id });
      setJob(data); pollJob(data.job_id);
    } catch (requestError) { setBusy(false); setPreview(null); setError(formatApiError(requestError.response?.data?.detail)); }
  };

  if (!withdrawal) return null;
  const changedLines = (preview?.lines_to_restore || 0) + (preview?.lines_to_settle || 0);
  return <Dialog open onOpenChange={(open) => { if (!open && !busy) onClose(); }}>
    <DialogContent className="max-h-[90vh] max-w-xl overflow-y-auto border-white/10 bg-zinc-950 text-white" closeTestId="legacy-withdraw-edit-close-button" data-testid="legacy-withdraw-edit-dialog">
      <DialogHeader><DialogTitle className="font-display text-2xl font-extrabold">Edit Bulan Laporan Legacy</DialogTitle><DialogDescription className="text-zinc-400">Hanya cutoff riwayat legacy yang berubah. Withdrawal melalui web tetap dikunci.</DialogDescription></DialogHeader>
      <div className="rounded-md border border-amber-400/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-100" data-testid="legacy-withdraw-edit-warning"><AlertTriangle className="mr-2 inline h-4 w-4" />Perubahan ini menghitung ulang saldo berdasarkan royalty lines.</div>
      {error && <div className="rounded-md bg-red-500/15 px-4 py-3 text-sm text-red-300" role="alert" data-testid="legacy-withdraw-edit-error">{error}</div>}
      <div><label className="rm-label" htmlFor="legacy-withdraw-period-to">Bulan Laporan Terakhir</label><input id="legacy-withdraw-period-to" type="month" className="rm-input" value={periodTo} min={withdrawal.period_from || undefined} onChange={(event) => setPeriodTo(event.target.value)} disabled={busy || job?.status === "done"} data-testid="legacy-withdraw-edit-period-to" /></div>
      {!preview && periodTo === withdrawal.period_to && <p className="text-xs text-zinc-500" data-testid="legacy-withdraw-edit-unchanged">Pilih bulan berbeda untuk melihat dampak.</p>}
      {!preview && periodTo !== withdrawal.period_to && !error && job?.status !== "done" && <div className="flex items-center gap-2 text-sm text-zinc-400" data-testid="legacy-withdraw-edit-loading"><Loader2 className="h-4 w-4 animate-spin" /> Menghitung dampak saldo…</div>}
      {preview && <div className="border-y border-white/10" data-testid="legacy-withdraw-edit-preview">
        <ChangeRow label="Cutoff laporan label" before={preview.old_cutoff || "—"} after={preview.new_cutoff || "—"} testId="legacy-withdraw-edit-cutoff-change" />
        <ChangeRow label="Saldo pending" before={fmtIDR(preview.balance_before.pending_idr)} after={fmtIDR(preview.balance_after.pending_idr)} testId="legacy-withdraw-edit-pending-change" />
        <ChangeRow label="Saldo tersedia" before={fmtIDR(preview.balance_before.available_idr)} after={fmtIDR(preview.balance_after.available_idr)} testId="legacy-withdraw-edit-available-change" />
        <ChangeRow label="Baris royalti berubah" before="—" after={changedLines.toLocaleString("id-ID")} testId="legacy-withdraw-edit-lines-change" />
      </div>}
      {preview?.direction === "unchanged" && <p className="text-xs text-amber-300" data-testid="legacy-withdraw-edit-no-cutoff-impact">Riwayat lain memiliki cutoff lebih akhir, sehingga saldo tidak berubah.</p>}
      {job && busy && <div className="flex items-center gap-2 text-sm text-sky-300" data-testid="legacy-withdraw-edit-job"><Loader2 className="h-4 w-4 animate-spin" /> {job.progress_phase || job.status} — proses berjalan di background.</div>}
      {job?.status === "done" && <div className="flex items-center gap-2 text-sm text-emerald-300" data-testid="legacy-withdraw-edit-complete"><CheckCircle2 className="h-4 w-4" /> Perubahan berhasil disimpan.</div>}
      <DialogFooter>{job?.status === "done" ? <button type="button" className="rm-btn-primary" onClick={onClose} data-testid="legacy-withdraw-edit-done-close-button">Tutup</button> : <><button type="button" className="rm-btn-ghost" disabled={busy} onClick={onClose} data-testid="legacy-withdraw-edit-cancel-button">Batal</button><button type="button" className="rm-btn-primary" disabled={!preview || busy} onClick={save} data-testid="legacy-withdraw-edit-submit-button">{busy ? "Memproses…" : "Simpan Perubahan"}</button></>}</DialogFooter>
    </DialogContent>
  </Dialog>;
};