import React, { useState, useEffect, useRef } from "react";
import { Upload, AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { api } from "@/api/client";

const fmtIDR = (n) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);

function Stat({ label, value, color }) {
  return (
    <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-3">
      <div className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold">{label}</div>
      <div className={`text-xl font-bold mt-1 ${color}`}>{value ?? 0}</div>
    </div>
  );
}

export default function WithdrawImportPanel() {
  const [file, setFile] = useState(null);
  const [dryRun, setDryRun] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");
  const [showUnmatched, setShowUnmatched] = useState(true);
  const [job, setJob] = useState(null);
  const pollRef = useRef(null);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const pollJob = (jobId) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await api.get(`/admin/migrate/jobs/${jobId}`);
        setJob(data);
        if (data.status === "done" || data.status === "error") {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setLoading(false);
        }
      } catch (e) { /* keep polling */ }
    }, 3000);
  };

  const submit = async () => {
    if (!file) { setErr("Pilih CSV dulu"); return; }
    setErr(""); setResult(null); setJob(null); setLoading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("dry_run", dryRun ? "true" : "false");
      fd.append("create_history_docs", "true");
      fd.append("flip_royalty_lines", "true");
      fd.append("adjust_balances", "true");
      const { data } = await api.post("/admin/migrate/withdraws-legacy-period", fd, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 115000,
      });
      setResult(data);
      if (!dryRun && data.job_id) {
        pollJob(data.job_id);
      } else {
        setLoading(false);
      }
    } catch (e) {
      setErr(e.response?.data?.detail || e.message || "Upload gagal");
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4" data-testid="admin-withdraw-import-panel">
      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 text-amber-200 text-xs px-4 py-3 leading-relaxed">
        <b>Sinkronisasi riwayat penarikan lama.</b> Upload CSV dengan kolom <code>nama_label</code> + <code>period_end</code> (YYYY-MM).
        Sistem otomatis: (1) mencocokkan berdasarkan <b>nama label</b>, (2) set bulan laporan terakhir yang sudah ditarik = MAX(<code>period_end</code>),
        (3) royalti sampai bulan itu ditandai <b>sudah diambil</b> (saldo menyesuaikan), (4) nominal dari CSV tersimpan apa adanya sebagai riwayat penarikan (status: Paid).
        Penarikan berikutnya oleh label otomatis mulai dari bulan SETELAHNYA. Jalankan <b>Preview dulu</b>, cek hasil, baru Commit.
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          type="file"
          accept=".csv"
          onChange={(e) => { setFile(e.target.files?.[0] || null); setResult(null); setErr(""); }}
          className="text-xs text-zinc-300 file:rm-btn-secondary file:mr-3 file:px-3 file:py-1.5 file:border-0 file:cursor-pointer"
          data-testid="admin-withdraw-import-file"
        />
        <label className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 cursor-pointer hover:bg-white/10 text-xs">
          <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} className="accent-[#FF1F8E]" data-testid="admin-withdraw-import-dryrun" />
          <span>Preview dulu (dry-run, data belum diubah)</span>
        </label>
        <button
          onClick={submit}
          disabled={!file || loading}
          className="rm-btn-primary text-xs flex items-center gap-2"
          data-testid="admin-withdraw-import-submit"
        >
          <Upload className="w-3.5 h-3.5" />
          {loading ? "Memproses…" : dryRun ? "Preview Dry-run" : "COMMIT (data akan diubah)"}
        </button>
      </div>

      {err && (
        <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm flex items-start gap-2">
          <AlertCircle className="w-4 h-4 mt-0.5" /> <span>{String(err)}</span>
        </div>
      )}

      {result && (
        <div className="space-y-4">
          {result.dry_run ? (
            <div className="rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-200 text-xs px-3 py-2 flex items-center gap-2" data-testid="admin-withdraw-import-dryrun-banner">
              <AlertCircle className="w-3.5 h-3.5" /> Mode <b>dry-run</b> — data BELUM diubah. Review report di bawah, lalu uncheck Preview + klik COMMIT.
            </div>
          ) : result.commit?.queued ? (
            <div className="rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-200 text-xs px-3 py-2 space-y-1.5" data-testid="admin-withdraw-import-job-status">
              <div className="flex items-center gap-2 font-semibold">
                {job?.status === "done" ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-300" /> : <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                {job?.status === "done" ? "COMMIT SELESAI" : "COMMIT BERJALAN DI BACKGROUND"}
              </div>
              {job && (
                <>
                  <div className="flex justify-between gap-2 pt-1">
                    <span>Status</span>
                    <span className={`font-semibold ${job.status === "done" ? "text-emerald-300" : job.status === "error" ? "text-red-300" : "text-amber-300"}`}>
                      {job.status === "processing" ? "Memproses…" : job.status === "done" ? "SELESAI" : job.status === "error" ? "GAGAL" : job.status}
                    </span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span>Labels diproses</span>
                    <span className="font-mono">{job.progress_labels_done || 0} / {job.progress_labels_total || 0}</span>
                  </div>
                  {job.error_message && (
                    <div className="text-red-300 mt-1 font-mono break-all">{job.error_message}</div>
                  )}
                  {job.status === "done" && job.result && (
                    <div className="grid grid-cols-2 gap-1 pt-2 mt-1 border-t border-indigo-500/20">
                      <div>Labels updated: <b className="font-mono">{job.result.labels_period_updated}</b></div>
                      <div>Lines flipped: <b className="font-mono">{(job.result.royalty_lines_flipped || 0).toLocaleString("id-ID")}</b></div>
                      <div>Riwayat tersimpan: <b className="font-mono">{job.result.history_docs_inserted}</b></div>
                      <div>Saldo pending −: <b className="font-mono">{fmtIDR(job.result.balance_pending_subtracted)}</b></div>
                    </div>
                  )}
                </>
              )}
            </div>
          ) : null}

          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <Stat label="Total CSV Rows" value={result.total_csv_rows} color="text-zinc-200" />
            <Stat label="Label Cocok" value={result.matched_labels} color="text-emerald-300" />
            <Stat label="Label Tidak Cocok" value={result.unmatched_label_count} color="text-amber-300" />
            <Stat label="Baris Royalti → Withdrawn" value={(result.totals_preview?.royalty_lines_to_flip || 0).toLocaleString("id-ID")} color="text-indigo-300" />
            <Stat label="Riwayat Disimpan" value={result.totals_preview?.history_docs_to_insert} color="text-rose-300" />
          </div>

          {result.unmatched_label_count > 0 && (
            <div className="rm-card p-4">
              <button onClick={() => setShowUnmatched((s) => !s)} className="w-full flex items-center justify-between text-xs font-bold uppercase tracking-widest text-zinc-500">
                <span>Nama Label Tidak Ditemukan — cek ejaan / belum ada di sistem</span>
                <span className="text-amber-300">{result.unmatched_label_count} {showUnmatched ? "▾" : "▸"}</span>
              </button>
              {showUnmatched && (
                <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-1 text-xs max-h-72 overflow-y-auto">
                  {(result.unmatched_label_names || []).map((u) => (
                    <div key={u.name} className="flex justify-between px-2 py-1 rounded bg-white/[0.02]">
                      <span className="truncate text-zinc-300">{u.name}</span>
                      <span className="text-zinc-500 font-mono">{u.row_count}×</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="rm-card p-4">
            <div className="text-xs uppercase font-bold text-zinc-500 tracking-widest mb-3">Ringkasan Per Label ({(result.label_summaries || []).length})</div>
            <div className="overflow-x-auto rounded-2xl border border-white/5 max-h-96 overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="bg-white/[0.03] text-zinc-400 sticky top-0">
                  <tr>
                    <th className="px-3 py-2 text-left">Label</th>
                    <th className="px-3 py-2 text-left">Bulan Terakhir Ditarik (Lama → Baru)</th>
                    <th className="px-3 py-2 text-right">Riwayat</th>
                    <th className="px-3 py-2 text-right">Baris Flip</th>
                  </tr>
                </thead>
                <tbody>
                  {(result.label_summaries || []).map((s) => (
                    <tr key={s.label_id} className="border-t border-white/5">
                      <td className="px-3 py-2 text-zinc-200">{s.label_name}</td>
                      <td className="px-3 py-2 text-xs"><span className="text-zinc-500">{s.old_last_withdrawn_period || "—"}</span> <span className="text-zinc-600 mx-1">→</span> <span className={s.period_will_advance ? "text-emerald-300" : "text-zinc-500"}>{s.new_last_withdrawn_period}</span></td>
                      <td className="px-3 py-2 text-right text-zinc-400">{s.csv_row_count}</td>
                      <td className="px-3 py-2 text-right text-indigo-300">{(s.royalty_lines_to_flip || 0).toLocaleString("id-ID")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
