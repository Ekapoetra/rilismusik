import React from "react";
import { AlertTriangle, CheckCircle2, Loader2, RefreshCw, Scale } from "lucide-react";
import { useBalanceAudit } from "@/hooks/useBalanceAudit";

const fmtIDR = (value) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(value || 0);
const fmtPeriod = (value) => value || "—";

export default function BalanceAuditPanel() {
  const audit = useBalanceAudit();
  const previewDone = audit.previewJob?.status === "done";
  const commitDone = ["done", "done_with_errors"].includes(audit.commitJob?.status);
  const job = audit.commitJob && !commitDone ? audit.commitJob : audit.previewJob;
  const progress = jobProgress(job);
  const summary = audit.previewJob?.summary;

  return (
    <div className="space-y-5" data-testid="admin-balance-audit-panel">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-widest text-cyan-400 font-bold">Financial Integrity</div>
          <h3 className="font-display font-bold text-xl tracking-normal mt-1">Audit Saldo Semua Label</h3>
          <p className="text-xs text-zinc-400 mt-1 max-w-3xl">Bandingkan saldo dengan laporan royalti, temukan data yang salah berstatus sudah ditarik, dan lindungi riwayat penarikan yang belum lengkap.</p>
        </div>
        <button onClick={audit.startPreview} disabled={audit.busy} className="rm-btn-primary flex items-center gap-2" data-testid="admin-balance-audit-start">
          {audit.busy && !previewDone ? <Loader2 className="w-4 h-4 animate-spin" /> : <Scale className="w-4 h-4" />}
          {previewDone ? "Audit Ulang" : "Mulai Preview Audit"}
        </button>
      </div>

      {audit.error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200" data-testid="admin-balance-audit-error"><AlertTriangle className="w-4 h-4 inline mr-2" />{audit.error}</div>}

      {job && !["done", "done_with_errors", "error"].includes(job.status) && (
        <div className="rounded-lg border border-cyan-500/25 bg-cyan-500/10 px-4 py-3 space-y-2" data-testid="admin-balance-audit-progress">
          <div className="flex justify-between gap-3 text-sm"><span className="text-cyan-200 flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> {job.phase || job.status}</span><span className="font-mono" data-testid="admin-balance-audit-progress-percent">{progress}%</span></div>
          <div className="h-1.5 rounded-full bg-white/10 overflow-hidden"><div className="h-full bg-cyan-400 transition-all" style={{ width: `${progress}%` }} /></div>
          <div className="text-[11px] text-zinc-500">{job.progress_labels_done || 0} / {job.progress_labels_total || 0} label</div>
        </div>
      )}

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 border border-white/10 rounded-lg overflow-hidden" data-testid="admin-balance-audit-summary">
          <Summary label="Total label" value={summary.total_labels} testId="total" />
          <Summary label="Perlu koreksi" value={summary.drift_labels} tone="text-amber-300" testId="drift" />
          <Summary label="Saldo negatif" value={summary.negative_balance_labels} tone="text-red-300" testId="negative" />
          <Summary label="Royalti salah status" value={(summary.wrongly_settled_lines || 0).toLocaleString("id-ID")} tone="text-orange-300" testId="orphan-lines" />
          <Summary label="Nilai belum masuk saldo" value={fmtIDR(summary.wrongly_settled_idr)} tone="text-orange-200" testId="orphan-amount" />
          <Summary label="Data sebelum batas tarik" value={(summary.stale_cutoff_lines || 0).toLocaleString("id-ID")} tone="text-rose-300" testId="stale" />
          <Summary label="Withdraw aktif" value={summary.blocked_active_withdraw} tone="text-sky-300" testId="blocked" />
          <Summary label="Riwayat belum lengkap" value={summary.blocked_withdraw_history} tone="text-fuchsia-300" testId="blocked-history" />
          <Summary label="Sudah sesuai" value={summary.clean_labels} tone="text-emerald-300" testId="clean" />
          <Summary label="Batas tarik diperbarui" value={summary.cutoff_sync_labels} tone="text-cyan-300" testId="cutoff-sync" />
        </div>
      )}

      {previewDone && (
        <>
          <div className="flex flex-wrap gap-3 items-end">
            <div><label className="rm-label">Status</label><select value={audit.filter} onChange={(event) => audit.applyFilter(event.target.value)} className="rm-input min-w-44" data-testid="admin-balance-audit-filter"><option value="">Semua</option><option value="drift">Perlu koreksi</option><option value="clean">Sudah sesuai</option><option value="blocked_active_withdraw">Withdraw aktif</option><option value="blocked_withdraw_history">Riwayat belum lengkap</option></select></div>
            <div className="flex-1 min-w-56"><label className="rm-label">Cari label</label><input value={audit.search} onChange={(event) => audit.setSearch(event.target.value)} onKeyDown={(event) => event.key === "Enter" && audit.applySearch()} className="rm-input" placeholder="Poetra Studio" data-testid="admin-balance-audit-search" /></div>
            <button onClick={audit.applySearch} className="rm-btn-ghost" data-testid="admin-balance-audit-search-button">Cari</button>
            <div className="text-xs text-zinc-500 ml-auto" data-testid="admin-balance-audit-row-count">{audit.totalRows} label</div>
          </div>

          <div className="border border-white/10 rounded-lg overflow-hidden" data-testid="admin-balance-audit-table">
            <div className="overflow-x-auto max-h-[480px] overflow-y-auto">
              <table className="w-full min-w-[1460px] text-xs">
                <thead className="sticky top-0 bg-[#111318] text-[10px] uppercase text-zinc-500"><tr><th className="text-left px-3 py-3">Label</th><th className="text-left px-3 py-3">Batas tarik label</th><th className="text-left px-3 py-3">Batas tarik terverifikasi</th><th className="text-left px-3 py-3">Laporan terbaru</th><th className="text-left px-3 py-3">Periode belum ditarik</th><th className="text-right px-3 py-3">Pending lama → benar</th><th className="text-right px-3 py-3">Tersedia lama → perkiraan</th><th className="text-right px-3 py-3">Royalti salah status</th><th className="text-right px-3 py-3">Data sebelum batas</th><th className="text-left px-3 py-3">Status</th></tr></thead>
                <tbody>{audit.rows.map((row) => <AuditRow row={row} key={row.label_id} />)}</tbody>
              </table>
            </div>
            {audit.rows.length === 0 && <div className="text-center text-sm text-zinc-500 py-8" data-testid="admin-balance-audit-empty">Tidak ada label pada filter ini.</div>}
          </div>

          {!audit.commitJob && summary.drift_labels > 0 && (
            <div className="border-y border-white/10 py-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              <label className="flex gap-3 items-start text-sm text-zinc-300 cursor-pointer" data-testid="admin-balance-audit-confirm-label"><input type="checkbox" checked={audit.confirmed} onChange={(event) => audit.setConfirmed(event.target.checked)} className="mt-1 accent-emerald-400" data-testid="admin-balance-audit-confirm" /><span>Saya sudah memeriksa hasil sementara. Perbarui batas penarikan, rapikan data lama, kembalikan royalti yang salah berstatus sudah ditarik, hitung ulang persentase label, lalu perbarui saldo. Label dengan penarikan aktif atau riwayat tanpa periode akan dilewati.</span></label>
              <button onClick={audit.commit} disabled={!audit.confirmed || audit.busy} className="rm-btn-primary flex items-center gap-2 justify-center min-w-52" data-testid="admin-balance-audit-commit"><CheckCircle2 className="w-4 h-4" /> Rekonsiliasi Semua</button>
            </div>
          )}
        </>
      )}

      {commitDone && <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-4" data-testid="admin-balance-audit-complete"><div className="font-bold text-emerald-300 flex items-center gap-2"><CheckCircle2 className="w-4 h-4" /> Koreksi saldo selesai</div><div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3 mt-3 text-xs"><Result label="Label dikoreksi" value={audit.commitJob.result?.labels_reconciled} /><Result label="Data salah status dipulihkan" value={(audit.commitJob.result?.orphan_lines_restored || 0).toLocaleString("id-ID")} /><Result label="Data dihitung ulang" value={(audit.commitJob.result?.orphan_lines_recalculated || 0).toLocaleString("id-ID")} /><Result label="Data lama dirapikan" value={(audit.commitJob.result?.stale_lines_settled || 0).toLocaleString("id-ID")} /><Result label="Gagal" value={audit.commitJob.result?.labels_failed} /></div><button onClick={audit.startPreview} className="rm-btn-ghost mt-4 flex items-center gap-2" data-testid="admin-balance-audit-verify"><RefreshCw className="w-4 h-4" /> Audit ulang untuk verifikasi</button></div>}
    </div>
  );
}

function AuditRow({ row }) {
  const status = row.audit_status === "drift" ? ["Perlu koreksi", "text-amber-300 bg-amber-500/15"] : row.audit_status === "blocked_active_withdraw" ? ["Withdraw aktif", "text-sky-300 bg-sky-500/15"] : row.audit_status === "blocked_withdraw_history" ? ["Riwayat belum lengkap", "text-fuchsia-300 bg-fuchsia-500/15"] : ["Sesuai", "text-emerald-300 bg-emerald-500/15"];
  return <tr className="border-t border-white/5" data-testid={`admin-balance-audit-row-${row.label_id}`}><td className="px-3 py-3 font-semibold">{row.label_name}</td><td className="px-3 py-3 font-mono">{fmtPeriod(row.last_withdrawn_period)}</td><td className="px-3 py-3 font-mono">{fmtPeriod(row.effective_withdraw_cutoff)}</td><td className="px-3 py-3 font-mono">{fmtPeriod(row.latest_report_period)}</td><td className="px-3 py-3 font-mono">{row.eligible_period_from ? `${row.eligible_period_from} → ${row.eligible_period_to}` : "Kosong"}</td><td className="px-3 py-3 text-right font-mono"><span className={row.current_pending_idr < 0 ? "text-red-300" : "text-zinc-400"}>{fmtIDR(row.current_pending_idr)}</span><span className="text-zinc-600 mx-1">→</span><span className="text-white">{fmtIDR(row.expected_pending_idr)}</span></td><td className="px-3 py-3 text-right font-mono"><span className="text-zinc-400">{fmtIDR(row.current_available_idr)}</span><span className="text-zinc-600 mx-1">→</span><span className="text-white">{fmtIDR(row.expected_available_idr)}</span></td><td className="px-3 py-3 text-right font-mono"><div>{(row.wrongly_settled_lines || 0).toLocaleString("id-ID")} baris</div><div className="text-orange-300">{fmtIDR(row.wrongly_settled_idr)}</div>{row.orphan_legacy_settled_lines > 0 && <div className="text-[10px] text-zinc-500">{row.orphan_legacy_settled_lines.toLocaleString("id-ID")} bertanda sudah dibayar</div>}</td><td className="px-3 py-3 text-right font-mono">{(row.stale_cutoff_lines || 0).toLocaleString("id-ID")}</td><td className="px-3 py-3"><span className={`px-2 py-1 rounded-full text-[10px] font-bold ${status[1]}`}>{status[0]}</span></td></tr>;
}

function Summary({ label, value, tone = "text-zinc-100", testId }) { return <div className="px-4 py-3 border-r border-b xl:border-b-0 border-white/10" data-testid={`admin-balance-audit-summary-${testId}`}><div className={`text-2xl font-bold ${tone}`}>{value || 0}</div><div className="text-[11px] text-zinc-500 mt-1">{label}</div></div>; }
function Result({ label, value }) { return <div className="border-l border-white/15 pl-3"><div className="text-lg font-bold">{value || 0}</div><div className="text-zinc-500">{label}</div></div>; }
function jobProgress(job) { if (!job) return 0; if (["done", "done_with_errors"].includes(job.status)) return 100; return Math.round(((job.progress_labels_done || 0) / Math.max(job.progress_labels_total || 1, 1)) * 100); }