import React from "react";
import { AlertTriangle, CopyCheck, Loader2, ShieldCheck, X } from "lucide-react";
import { useRoyaltyDuplicateAudit } from "@/hooks/useRoyaltyDuplicateAudit";

const eur = (value) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "EUR", maximumFractionDigits: 4 }).format(value || 0);
const idr = (value) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(value || 0);
const phaseLabel = (phase) => ({ menunggu_proses: "Menunggu proses", mencari_duplikat: "Mencari file ganda", menghitung_dampak: "Menghitung dampak", queued: "Menunggu proses", processing: "Sedang memeriksa" }[phase] || "Sedang memeriksa");

export const RoyaltyDuplicateAuditPanel = ({ onClose }) => {
  const audit = useRoyaltyDuplicateAudit();
  const summary = audit.job?.summary || {};
  return <section className="border border-white/10 bg-white/[0.02] p-5 space-y-5" data-testid="royalty-duplicate-audit-panel">
    <div className="flex items-start justify-between gap-4">
      <div><h2 className="font-display text-xl font-extrabold flex items-center gap-2"><CopyCheck className="w-5 h-5 text-amber-300" /> Audit File Ganda</h2><p className="text-xs text-zinc-400 mt-1">Hanya membaca data. Tidak menghapus file dan tidak mengubah saldo.</p></div>
      <button onClick={onClose} className="rm-btn-ghost p-2" aria-label="Tutup audit file ganda" data-testid="royalty-duplicate-audit-close"><X className="w-4 h-4" /></button>
    </div>
    <button onClick={audit.start} disabled={audit.busy} className="rm-btn-primary flex items-center gap-2" data-testid="royalty-duplicate-audit-start">{audit.busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}{audit.busy ? "Memeriksa…" : "Mulai Audit File Ganda"}</button>
    {audit.error && <div className="text-sm text-red-300 bg-red-500/10 border border-red-500/20 p-3" data-testid="royalty-duplicate-audit-error">{audit.error}</div>}
    {audit.warning && <div className="text-xs text-amber-200 bg-amber-500/10 border border-amber-500/20 p-3" data-testid="royalty-duplicate-audit-warning">{audit.warning}</div>}
    {audit.job && audit.job.status !== "done" && <div className="text-sm text-sky-200" data-testid="royalty-duplicate-audit-progress">{phaseLabel(audit.job.phase || audit.job.status)}{audit.job.progress_groups_total > 0 ? ` · ${(audit.job.progress_groups_done || 0).toLocaleString("id-ID")}/${audit.job.progress_groups_total.toLocaleString("id-ID")}` : ""}</div>}
    {audit.job?.status === "done" && <>
      <div className="grid grid-cols-2 lg:grid-cols-4 border border-white/10" data-testid="royalty-duplicate-audit-summary">
        <Metric label="Pasangan file ganda" value={summary.duplicate_pairs || 0} />
        <Metric label="Baris terduplikasi" value={(summary.duplicate_lines || 0).toLocaleString("id-ID")} />
        <Metric label="Nilai EUR terduplikasi" value={eur(summary.duplicate_revenue_eur)} />
        <Metric label="Dampak saldo aktif" value={idr(summary.active_balance_impact_idr)} />
      </div>
      {audit.rows.length === 0 ? <div className="text-sm text-emerald-300" data-testid="royalty-duplicate-audit-empty">Tidak ditemukan file ganda.</div> : audit.rows.map((row) => <DuplicatePair key={row.id} row={row} />)}
    </>}
  </section>;
};

const Metric = ({ label, value }) => <div className="p-4 border-r border-b border-white/10 last:border-r-0"><div className="text-[10px] uppercase text-zinc-500">{label}</div><div className="font-mono font-bold mt-1">{value}</div></div>;

const DuplicatePair = ({ row }) => <article className="border border-amber-500/25 bg-amber-500/[0.04] p-4 space-y-4" data-testid={`royalty-duplicate-pair-${row.id}`}>
  <div className="flex items-center gap-2 text-amber-200 font-bold"><AlertTriangle className="w-4 h-4" /> Data yang sama terunggah dua kali</div>
  <div className="grid md:grid-cols-2 gap-4 text-sm">
    <FileInfo title="Disarankan dipertahankan" data={row.canonical_import} tone="text-emerald-300" />
    <FileInfo title="Salinan yang perlu ditinjau" data={row.duplicate_import} tone="text-amber-300" />
  </div>
  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
    <Impact label="Periode sama persis" value={row.comparison?.exact_period_match ? "Ya" : "Tidak"} />
    <Impact label="Label terdampak" value={row.impact?.affected_labels || 0} />
    <Impact label="Saldo aktif dari salinan" value={idr(row.impact?.active_balance_idr)} />
    <Impact label="Riwayat/perlu pemeriksaan" value={idr(row.impact?.historical_or_excluded_idr)} />
  </div>
  <div className="text-xs text-zinc-400" data-testid={`royalty-duplicate-recommendation-${row.id}`}>{row.recommendation}</div>
</article>;

const FileInfo = ({ title, data, tone }) => <div className="border-l-2 border-white/10 pl-3"><div className={`text-xs font-bold ${tone}`}>{title}</div><div className="font-semibold mt-1">{data?.filename}</div><div className="text-zinc-500 text-xs mt-1">{(data?.total_lines || 0).toLocaleString("id-ID")} baris · {eur(data?.total_revenue_eur)} · kurs Rp {(data?.exchange_rate_eur_idr || 0).toLocaleString("id-ID")}</div><div className="text-zinc-600 text-[10px] mt-1">{data?.period_start} → {data?.period_end}</div></div>;
const Impact = ({ label, value }) => <div><div className="text-zinc-500">{label}</div><div className="font-mono font-bold mt-1">{value}</div></div>;