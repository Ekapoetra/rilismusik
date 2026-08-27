import React from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, ArrowLeft, CheckCircle2, Download, FileSpreadsheet, Loader2, RefreshCw, Upload } from "lucide-react";
import { useLabelRateImport } from "@/hooks/useLabelRateImport";

const STATUS_META = {
  matched: ["Siap update", "text-emerald-300 bg-emerald-500/15"],
  unchanged: ["Tidak berubah", "text-zinc-300 bg-white/10"],
  unmatched: ["Tidak ditemukan", "text-amber-300 bg-amber-500/15"],
  ambiguous: ["Nama ambigu", "text-orange-300 bg-orange-500/15"],
  invalid: ["Tidak valid", "text-red-300 bg-red-500/15"],
  duplicate_conflict: ["Duplikat konflik", "text-red-300 bg-red-500/15"],
  duplicate_redundant: ["Duplikat sama", "text-zinc-400 bg-white/5"],
  blocked_withdraw: ["Withdraw aktif", "text-rose-300 bg-rose-500/15"],
};

const SUMMARY_ITEMS = [
  ["will_update", "Akan diperbarui", "text-emerald-300"],
  ["unchanged", "Sudah sama", "text-zinc-200"],
  ["unmatched", "Tidak ditemukan", "text-amber-300"],
  ["ambiguous", "Nama ambigu", "text-orange-300"],
  ["duplicate_conflict", "Duplikat konflik", "text-red-300"],
  ["blocked_withdraw", "Withdraw aktif", "text-rose-300"],
];

function downloadTemplate() {
  const blob = new Blob(["No.,Nama Label,Rate\n1,Contoh Label,60\n"], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url; link.download = "template-rate-label.csv"; link.click();
  URL.revokeObjectURL(url);
}

export default function LabelRateImport() {
  const state = useLabelRateImport();
  const progress = jobProgress(state.job);
  const complete = ["done", "done_with_errors"].includes(state.job?.status);

  return (
    <div className="space-y-7" data-testid="admin-label-rate-import-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link to="/admin/labels" className="inline-flex items-center gap-2 text-xs text-zinc-500 hover:text-zinc-200 mb-3" data-testid="admin-label-rate-import-back"><ArrowLeft className="w-3.5 h-3.5" /> Label Management</Link>
          <div className="text-xs uppercase tracking-widest text-cyan-400 font-bold">Finance Operations</div>
          <h1 className="font-display text-3xl sm:text-4xl font-extrabold tracking-normal mt-1">Impor Rate Label</h1>
          <p className="text-sm text-zinc-400 mt-2 max-w-2xl">Sinkronkan persentase label dari XLSX/CSV. Sistem hanya mengubah label yang cocok dan menghitung ulang royalti unsettled setelah konfirmasi.</p>
        </div>
        <button onClick={downloadTemplate} className="rm-btn-ghost flex items-center gap-2" data-testid="admin-label-rate-download-template"><Download className="w-4 h-4" /> Template CSV</button>
      </div>

      <section className="border-y border-white/10 py-6 grid lg:grid-cols-[1fr_auto] gap-5 items-end">
        <div>
          <label className="rm-label">File Rate Label</label>
          <input
            type="file" accept=".xlsx,.csv,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            className="rm-input" disabled={state.busy || Boolean(state.preview)}
            onChange={(event) => state.setFile(event.target.files?.[0] || null)}
            data-testid="admin-label-rate-file"
          />
          <div className="text-[11px] text-zinc-500 mt-2">Kolom wajib: <b>Nama Label</b> dan <b>Rate</b> (0–100). Kolom No. diabaikan. Maksimal 5.000 baris / 10 MB.</div>
        </div>
        {!state.preview ? (
          <button onClick={state.createPreview} disabled={!state.file || state.busy} className="rm-btn-primary flex items-center gap-2 justify-center min-w-40" data-testid="admin-label-rate-preview">
            {state.busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileSpreadsheet className="w-4 h-4" />} Preview
          </button>
        ) : (
          <button onClick={state.reset} disabled={state.busy} className="rm-btn-ghost flex items-center gap-2 justify-center" data-testid="admin-label-rate-reset"><RefreshCw className="w-4 h-4" /> File lain</button>
        )}
      </section>

      {state.error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200" data-testid="admin-label-rate-error"><AlertTriangle className="w-4 h-4 inline mr-2" />{state.error}</div>}

      {state.preview && (
        <>
          <section className="space-y-3" data-testid="admin-label-rate-summary">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div><div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Hasil pencocokan</div><div className="text-sm text-zinc-300 mt-1">{state.preview.filename} · {state.preview.summary.total_rows} baris</div></div>
              <select value={state.statusFilter} onChange={(event) => state.setStatusFilter(event.target.value)} className="rm-input w-auto min-w-44" data-testid="admin-label-rate-status-filter">
                <option value="all">Semua status</option>
                {Object.entries(STATUS_META).map(([value, meta]) => <option value={value} key={value}>{meta[0]}</option>)}
              </select>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 border border-white/10 rounded-lg overflow-hidden">
              {SUMMARY_ITEMS.map(([key, label, color]) => <div key={key} className="px-4 py-3 border-r border-b xl:border-b-0 border-white/10 last:border-r-0" data-testid={`admin-label-rate-summary-${key}`}><div className={`text-2xl font-bold ${color}`}>{state.preview.summary[key] || 0}</div><div className="text-[11px] text-zinc-500 mt-1">{label}</div></div>)}
            </div>
          </section>

          <section className="border border-white/10 rounded-lg overflow-hidden" data-testid="admin-label-rate-preview-table">
            <div className="overflow-x-auto max-h-[430px] overflow-y-auto">
              <table className="w-full min-w-[850px] text-sm">
                <thead className="sticky top-0 bg-[#111318] text-[11px] uppercase text-zinc-500"><tr><th className="text-left px-4 py-3">Baris</th><th className="text-left px-4 py-3">Nama dari file</th><th className="text-left px-4 py-3">Label sistem</th><th className="text-right px-4 py-3">Rate lama</th><th className="text-right px-4 py-3">Rate baru</th><th className="text-left px-4 py-3">Status</th></tr></thead>
                <tbody>{state.visibleRows.map((row) => <RateRow key={`${row.row_number}-${row.status}`} row={row} />)}</tbody>
              </table>
            </div>
            {(state.preview.rows || []).length > 250 && <div className="px-4 py-2 text-[11px] text-zinc-500 border-t border-white/10">Menampilkan maksimal 250 baris. Gunakan filter status untuk meninjau hasil.</div>}
          </section>

          {!state.job && (
            <section className="border-y border-white/10 py-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              <label className="flex items-start gap-3 text-sm text-zinc-300 cursor-pointer" data-testid="admin-label-rate-confirm-label">
                <input type="checkbox" checked={state.confirmed} onChange={(event) => state.setConfirmed(event.target.checked)} className="mt-1 accent-emerald-400" data-testid="admin-label-rate-confirm" />
                <span>Saya sudah memeriksa unmatched, duplikat, dan perubahan rate. Lanjutkan update <b>{state.preview.summary.will_update}</b> label serta recalculation royalti pending/available.</span>
              </label>
              <button onClick={state.commit} disabled={!state.confirmed || !state.preview.summary.will_update || state.busy} className="rm-btn-primary flex items-center gap-2 justify-center min-w-48" data-testid="admin-label-rate-commit"><Upload className="w-4 h-4" /> Sinkronkan Rate</button>
            </section>
          )}
        </>
      )}

      {state.job && (
        <section className={`rounded-lg border px-5 py-4 space-y-3 ${complete ? "border-emerald-500/30 bg-emerald-500/10" : "border-cyan-500/30 bg-cyan-500/10"}`} data-testid="admin-label-rate-job-status">
          <div className="flex items-center justify-between gap-4"><div className="flex items-center gap-2 font-bold text-sm">{complete ? <CheckCircle2 className="w-4 h-4 text-emerald-300" /> : <Loader2 className="w-4 h-4 text-cyan-300 animate-spin" />}{complete ? "Sinkronisasi selesai" : "Update rate dan recalculation berjalan di background"}</div><span className="font-mono text-sm" data-testid="admin-label-rate-job-progress">{progress}%</span></div>
          <div className="h-2 rounded-full bg-white/10 overflow-hidden"><div className="h-full bg-gradient-to-r from-cyan-400 to-emerald-400 transition-all" style={{ width: `${progress}%` }} /></div>
          <div className="text-xs text-zinc-400">{state.job.progress_labels_done || 0} / {state.job.progress_labels_total || 0} label diproses · fase {state.job.phase || state.job.status}</div>
          {state.job.result && <div className="grid sm:grid-cols-3 gap-3 pt-2 text-xs" data-testid="admin-label-rate-job-result"><Result label="Label diperbarui" value={state.job.result.labels_updated} /><Result label="Baris royalti dihitung ulang" value={(state.job.result.lines_recalculated || 0).toLocaleString("id-ID")} /><Result label="Gagal" value={state.job.result.rows_failed} /></div>}
        </section>
      )}
    </div>
  );
}

function RateRow({ row }) {
  const meta = STATUS_META[row.status] || [row.status, "text-zinc-300 bg-white/10"];
  return <tr className="border-t border-white/5" data-testid={`admin-label-rate-row-${row.row_number}`}><td className="px-4 py-3 text-zinc-500 font-mono">{row.row_number}</td><td className="px-4 py-3 font-medium">{row.input_label_name || "—"}</td><td className="px-4 py-3 text-zinc-400">{row.matched_label_name || row.candidate_labels?.map((item) => item.label_name).join(", ") || "—"}<div className="text-[10px] text-zinc-600 mt-1">{row.reason}</div></td><td className="px-4 py-3 text-right font-mono">{row.current_rate == null ? "—" : `${row.current_rate}%`}</td><td className="px-4 py-3 text-right font-mono text-cyan-300">{row.input_rate == null ? "—" : `${row.input_rate}%`}</td><td className="px-4 py-3"><span className={`px-2 py-1 rounded-full text-[10px] font-bold ${meta[1]}`}>{meta[0]}</span></td></tr>;
}

function Result({ label, value }) {
  return <div className="border-l border-white/15 pl-3"><div className="text-lg font-bold text-white">{value || 0}</div><div className="text-zinc-500">{label}</div></div>;
}

function jobProgress(job) {
  if (!job) return 0;
  if (["done", "done_with_errors"].includes(job.status)) return 100;
  return Math.round(((job.progress_labels_done || 0) / Math.max(job.progress_labels_total || 1, 1)) * 100);
}