import React from "react";
import { Link } from "react-router-dom";
import { useRoyaltyImports } from "@/hooks/useRoyaltyImports";
import { RoyaltyDuplicateAuditPanel } from "@/components/admin/RoyaltyDuplicateAuditPanel";
import { Upload, FileSpreadsheet, CheckCircle2, Banknote, AlertTriangle, Trash2, Loader2, RefreshCw, XCircle, Zap, CopyCheck } from "lucide-react";
import { useAuth } from "@/api/AuthContext";

function fmtIDR(n) { return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0); }
function fmtEUR(n) { return new Intl.NumberFormat("en-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 2 }).format(n || 0); }

export default function AdminRoyaltyImport() {
  const { hasPermission } = useAuth();
  const canImport = hasPermission("royalty.import");
  const canManage = hasPermission("royalty.manage");
  const canDelete = hasPermission("royalty.delete");
  const [showDuplicateAudit, setShowDuplicateAudit] = React.useState(false);
  const {
    user, imports, open, setOpen, resetOpen, setResetOpen, resetConfirm, setResetConfirm,
    form, setForm, busy, uploadStage, uploadPct, err, msg, recalcBusy, recalcJob,
    retry, forceFinalize, remove, submit, submitReset, recalculateAll,
  } = useRoyaltyImports();

  return (
    <div className="min-w-0 space-y-5">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Finance</div>
          <h1 className="break-words font-display text-3xl font-extrabold tracking-tighter">Impor Royalti</h1>
          <p className="text-sm text-zinc-400 mt-1">Upload CSV Believe (EUR). Periode wajib dibaca dari kolom Bulan laporan.</p>
        </div>
        <div className="flex w-full min-w-0 flex-wrap gap-2 sm:w-auto sm:justify-end">
          {canManage && (
            <button className="rm-btn-ghost flex max-w-full items-center gap-2 whitespace-normal text-left text-amber-300" onClick={() => setShowDuplicateAudit((value) => !value)} data-testid="admin-royalty-duplicate-audit-button">
              <CopyCheck className="w-4 h-4" /> Audit File Ganda
            </button>
          )}
          {canManage && (
            <button
              className="rm-btn-ghost flex max-w-full items-center gap-2 whitespace-normal text-left text-sky-300"
              onClick={recalculateAll}
              disabled={recalcBusy}
              data-testid="admin-royalty-recalculate-all-button"
              title="Hitung ulang seluruh royalti aktif tanpa upload CSV ulang"
            >
              <RefreshCw className={`w-4 h-4 ${recalcBusy ? "animate-spin" : ""}`} /> {recalcBusy ? "Menghitung…" : "Hitung Ulang Tanpa Fee"}
            </button>
          )}
          {canDelete && <button
            className="rm-btn-ghost flex max-w-full items-center gap-2 whitespace-normal text-left text-red-300 hover:text-red-200"
            onClick={() => setResetOpen(true)}
            data-testid="admin-royalty-reset-button"
            title="Hapus semua data royalti (dummy) sebelum production"
          >
            <Trash2 className="w-4 h-4" /> Reset Data Demo
          </button>}
          {canImport && <button className="rm-btn-primary flex max-w-full items-center gap-2 whitespace-normal" onClick={() => setOpen(true)} data-testid="admin-royalty-upload-button">
            <Upload className="w-4 h-4" /> Upload CSV
          </button>}
        </div>
      </div>

      {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm">{err}</div>}
      {msg && <div className="rounded-2xl bg-emerald-500/15 text-emerald-300 px-4 py-3 text-sm">{msg}</div>}
      {recalcJob && recalcJob.status === "processing" && (
        <div className="rounded-2xl bg-sky-500/10 border border-sky-500/20 text-sky-200 px-4 py-3 text-sm" data-testid="admin-royalty-recalculation-status">
          Rekalkulasi: {(recalcJob.progress_labels_done || 0).toLocaleString("id-ID")} / {(recalcJob.progress_labels_total || 0).toLocaleString("id-ID")} label
        </div>
      )}

      {showDuplicateAudit && <RoyaltyDuplicateAuditPanel onClose={() => setShowDuplicateAudit(false)} />}

      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5">
          <div className="col-span-2">File / Periode</div>
          <div className="col-span-2">Kurs</div>
          <div className="col-span-2">Total File EUR (Semua Bulan)</div>
          <div className="col-span-2">Bagian Label IDR</div>
          <div className="col-span-2">Lines (matched/total)</div>
          <div className="col-span-2">Status</div>
        </div>
        {imports.length === 0 ? <div className="p-10 text-center text-zinc-500 text-sm">Belum ada import. Klik &quot;Upload CSV&quot; untuk mulai.</div> : imports.map((i) => (
          <Link key={i.id} to={`/admin/royalty/${i.id}`} className="grid min-w-0 grid-cols-12 items-center gap-3 border-b border-white/5 px-4 py-4 last:border-0 hover:bg-white/[0.02] sm:px-5" data-testid={`royalty-import-row-${i.id}`}>
            <div className="col-span-12 md:col-span-2 flex items-center gap-3">
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-amber-500/15 text-amber-300"><FileSpreadsheet className="w-4 h-4" /></div>
              <div className="min-w-0">
                <div className="font-display font-bold text-xs break-all">{i.filename || i.period}</div>
                <div className="text-[10px] text-zinc-500">{i.is_multi_period ? `${i.period_start} → ${i.period_end}` : i.period}</div>
              </div>
            </div>
            <div className="col-span-6 md:col-span-2 text-sm">Rp {i.exchange_rate_eur_idr?.toLocaleString("id-ID")}/€</div>
            <div className="col-span-6 md:col-span-2 text-sm">{fmtEUR(i.total_revenue_eur)}</div>
            <div className="col-span-6 md:col-span-2 text-sm font-semibold">{fmtIDR(i.total_label_idr)}</div>
            <div className="col-span-6 md:col-span-2 text-xs">
              {i.status === "processing" ? (
                <div data-testid={`royalty-import-progress-${i.id}`}>
                  <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                    <div className="h-full bg-sky-400 transition-all" style={{ width: `${i.progress_pct || 0}%` }} />
                  </div>
                  <div className="text-[10px] text-zinc-500 mt-1">{(i.processed_lines || 0).toLocaleString("id-ID")} baris • {i.progress_pct || 0}%</div>
                </div>
              ) : (
                <>
                  <span className="text-emerald-300 font-bold">{i.matched_lines}</span> / {i.total_lines}
                  {i.unmatched_lines > 0 && <span className="text-amber-300"> ({i.unmatched_lines} unmatched)</span>}
                </>
              )}
            </div>
            <div className="col-span-12 md:col-span-2 flex items-center gap-2 flex-wrap">
              <StatusBadge s={i.status} />
              {canManage && (i.status === "processing" || i.status === "error") && (
                <button
                  onClick={(e) => retry(i.id, e)}
                  className="rm-btn-ghost flex items-center gap-1 text-[10px] px-2 py-1"
                  data-testid={`royalty-import-retry-${i.id}`}
                  title="Retry background processing (re-process dari awal)"
                >
                  <RefreshCw className="w-3 h-3" /> Retry
                </button>
              )}
              {canManage && (i.status === "processing" || i.status === "error") && (
                <button
                  onClick={(e) => forceFinalize(i.id, e)}
                  className="rm-btn-ghost text-amber-300 hover:bg-amber-500/10 flex items-center gap-1 text-[10px] px-2 py-1"
                  data-testid={`royalty-import-force-finalize-${i.id}`}
                  title="Force-finalize: hitung ulang stats dari baris yang sudah ada di MongoDB & langsung pending_review (tanpa re-upload)"
                >
                  <Zap className="w-3 h-3" /> Force Finalize
                </button>
              )}
              {canDelete && ["awaiting_upload", "processing", "error", "publish_error", "pending_review"].includes(i.status) && (
                <button
                  onClick={(e) => remove(i, e)}
                  className="rm-btn-ghost text-rose-300 hover:bg-rose-500/10 flex items-center gap-1 text-[10px] px-2 py-1"
                  data-testid={`royalty-import-delete-${i.id}`}
                  title="Hapus import ini permanen (hanya untuk yang belum dipublish/dana diterima)"
                >
                  <Trash2 className="w-3 h-3" /> Hapus
                </button>
              )}
            </div>
          </Link>
        ))}
      </div>

      {open && (
        <div className="fixed inset-0 z-50 bg-black/40 grid place-items-center p-4" onClick={() => setOpen(false)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={submit} className="w-full max-w-md rm-glass-strong rounded-[24px] p-6 space-y-4">
            <h3 className="font-display font-extrabold text-xl tracking-tighter">Upload CSV Royalti</h3>
            <div>
              <label className="rm-label">Kurs EUR → IDR</label>
              <input type="number" min="1000" step="0.01" className="rm-input" value={form.rate_eur_idr} onChange={(e) => setForm({ ...form, rate_eur_idr: parseFloat(e.target.value) })} data-testid="admin-royalty-rate" required />
              <div className="text-[11px] text-zinc-500 mt-1">Kurs diinput manual per periode. Tidak bisa diubah setelah publish.</div>
            </div>
            <div>
              <label className="rm-label">File CSV Believe</label>
              <input type="file" accept=".csv,.gz,text/csv,application/gzip" className="rm-input" onChange={(e) => setForm({ ...form, file: e.target.files?.[0] || null })} data-testid="admin-royalty-file" disabled={busy} />
              <div className="text-[11px] text-zinc-500 mt-1">Upload langsung ke Cloudflare R2 — mendukung file <strong>hingga 5 GB</strong>. Kolom <strong>Bulan laporan</strong> wajib ada dan menjadi satu-satunya acuan periode; Bulan Penjualan tidak digunakan. Format desimal Eropa <code>0,000123</code> didukung. File .csv.gz juga oke.</div>
              {form.file && !busy && (
                <div className="text-[11px] text-emerald-300 mt-2">📁 {form.file.name} ({(form.file.size / 1024 / 1024).toFixed(1)} MB)</div>
              )}
            </div>
            <div>
              <label className="rm-label">Catatan (opsional)</label>
              <input className="rm-input" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} disabled={busy} />
            </div>
            {busy && (
              <div className="rounded-2xl bg-sky-500/10 border border-sky-500/20 p-4 space-y-2" data-testid="admin-royalty-upload-progress">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-sky-300 font-bold flex items-center gap-2">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    {uploadStage === "initiating" && "Meminta URL upload…"}
                    {uploadStage === "uploading" && `Upload ke R2 (${uploadPct}%)`}
                    {uploadStage === "finalizing" && "Memulai background processing…"}
                  </span>
                  {uploadStage === "uploading" && form.file && (
                    <span className="text-zinc-500">{((form.file.size * uploadPct / 100) / 1024 / 1024).toFixed(1)} / {(form.file.size / 1024 / 1024).toFixed(1)} MB</span>
                  )}
                </div>
                <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-sky-400 to-violet-400 transition-all"
                    style={{ width: `${uploadStage === "initiating" ? 5 : uploadStage === "uploading" ? uploadPct : 100}%` }}
                  />
                </div>
              </div>
            )}
            <div className="flex justify-end gap-2">
              <button type="button" className="rm-btn-ghost" onClick={() => setOpen(false)} disabled={busy}>Batal</button>
              <button className="rm-btn-primary" disabled={busy} data-testid="admin-royalty-submit">{busy ? "Mengupload…" : "Upload & Parse"}</button>
            </div>
          </form>
        </div>
      )}

      {resetOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 grid place-items-center p-4" onClick={() => setResetOpen(false)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={submitReset} className="w-full max-w-md rm-glass-strong rounded-[24px] p-6 space-y-4 border border-red-500/30">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-red-500/20 text-red-300 grid place-items-center">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <h3 className="font-display font-extrabold text-xl tracking-tighter text-red-200">Reset Data Demo</h3>
            </div>
            <div className="rounded-2xl bg-red-500/10 border border-red-500/20 p-4 text-sm text-red-200 space-y-2">
              <div className="font-bold">⚠️ Aksi ini TIDAK BISA DIBATALKAN.</div>
              <div>Akan menghapus seluruh:</div>
              <ul className="list-disc pl-5 text-xs space-y-1 text-red-200/80">
                <li>Semua import royalti (Believe CSV)</li>
                <li>Semua royalty lines</li>
                <li>Semua transaksi saldo (pending/available)</li>
                <li>Reset balance pending & available SEMUA label ke Rp 0</li>
                <li>Hapus file CSV yang sudah diupload</li>
              </ul>
              <div className="text-xs mt-2 text-red-200/70">Gunakan ini sebelum production deploy untuk membersihkan data dummy. Withdraw request, releases, dan data label lainnya TIDAK terpengaruh.</div>
            </div>
            <div>
              <label className="rm-label">Ketik <b>RESET</b> untuk konfirmasi</label>
              <input
                className="rm-input"
                value={resetConfirm}
                onChange={(e) => setResetConfirm(e.target.value)}
                placeholder="RESET"
                data-testid="admin-royalty-reset-confirm-input"
                autoFocus
              />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" className="rm-btn-ghost" onClick={() => { setResetOpen(false); setResetConfirm(""); }}>Batal</button>
              <button
                className="rm-btn-primary bg-gradient-to-r from-red-500 to-rose-600 hover:from-red-400 hover:to-rose-500"
                disabled={busy || resetConfirm !== "RESET"}
                data-testid="admin-royalty-reset-submit"
              >
                {busy ? "Menghapus…" : "Hapus Semua Data"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ s }) {
  const map = {
    processing: { bg: "bg-sky-500/15", color: "text-sky-300", label: "Processing", icon: Loader2, spin: true },
    pending_review: { bg: "bg-amber-500/15", color: "text-amber-300", label: "Pending Review", icon: FileSpreadsheet },
    publishing: { bg: "bg-violet-500/15", color: "text-violet-300", label: "Publishing", icon: Loader2, spin: true },
    publish_error: { bg: "bg-red-500/15", color: "text-red-300", label: "Publish Error", icon: XCircle },
    published: { bg: "bg-sky-500/15", color: "text-sky-300", label: "Published", icon: CheckCircle2 },
    receiving: { bg: "bg-cyan-500/15", color: "text-cyan-300", label: "Memindahkan Saldo", icon: Loader2, spin: true },
    receive_error: { bg: "bg-red-500/15", color: "text-red-300", label: "Penerimaan Gagal", icon: XCircle },
    dana_received: { bg: "bg-emerald-500/15", color: "text-emerald-300", label: "Dana Diterima", icon: Banknote },
    error: { bg: "bg-red-500/15", color: "text-red-300", label: "Error", icon: XCircle },
    deleting: { bg: "bg-rose-500/15", color: "text-rose-300", label: "Menghapus…", icon: Loader2, spin: true },
  }[s] || { bg: "bg-white/[0.06]", color: "text-zinc-300", label: s };
  const Icon = map.icon;
  return <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold ${map.bg} ${map.color}`} data-testid={`royalty-status-${s}`}>{Icon && <Icon className={`w-3 h-3 ${map.spin ? "animate-spin" : ""}`} />}{map.label}</span>;
}
