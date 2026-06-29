import React, { useState, useRef } from "react";
import { Upload, Download, FileText, Users, Music2, ListMusic, Wallet, AlertCircle, CheckCircle2, Clock, UserCheck, UserX, RotateCw, Loader2, AlertTriangle, Sparkles } from "lucide-react";
import { api } from "@/api/client";
import { useEffect } from "react";

const TABS = [
  { id: "labels", label: "Labels", icon: Users, endpoint: "labels", desc: "Import data label lama (5-6 ribu). user_id=null, status=legacy_unclaimed." },
  { id: "releases", label: "Releases", icon: Music2, endpoint: "releases", desc: "Import katalog rilisan lama (imported_legacy=true)." },
  { id: "tracks", label: "Tracks", icon: ListMusic, endpoint: "tracks", desc: "Import master tracks per release. Audio file URL optional." },
  { id: "withdraws", label: "Withdraws (old)", icon: Wallet, endpoint: "withdraws", desc: "Format lama: kolom amount_idr + request_date. Tidak trigger notifikasi atau mutasi saldo." },
  { id: "withdraws-fifo", label: "Withdraws (Period FIFO)", icon: Wallet, endpoint: "withdraws-legacy-period", desc: "Format CSV: nama_label + period_end. Commit jalan di background (Phase 26) untuk hindari 120s ingress timeout.", custom: true },
  { id: "backfill-period", label: "Backfill Bulan Laporan", icon: RotateCw, endpoint: "royalty/backfill-period-from-row", desc: "Perbaiki royalty_lines.period agar pakai nilai kolom Bulan Laporan dari CSV. Untuk imports lama (sebelum Phase 23.1) yang semua barisnya tertulis 1 bulan padahal CSV multi-bulan.", custom: true },
  { id: "materialize-artists", label: "Materialize Artists", icon: Sparkles, endpoint: "materialize-artists", desc: "Buat dokumen artist dari kolom artist_name di royalty_lines (CSV ingestion tidak otomatis bikin artist). Lalu backfill artist_id di lines + tracks supaya Artist Management menampilkan data.", custom: true },
  { id: "claims", label: "Claims", icon: UserCheck, endpoint: null, desc: "Resolve permintaan label claim akun lama. Link ke legacy label_id atau reject." },
];

export default function AdminMigrate() {
  const params = new URLSearchParams(window.location.search);
  const initialTab = params.get("tab") || "labels";
  const [tab, setTab] = useState(TABS.find(t => t.id === initialTab) ? initialTab : "labels");
  const cfg = TABS.find(t => t.id === tab);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Migrasi Data</h1>
        <p className="text-sm text-zinc-400 mt-1">Bulk import data lama (royalti, label, releases, tracks, withdraw). <b>Super Admin only.</b></p>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-white/5 pb-3">
        {TABS.map(t => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              data-testid={`admin-migrate-tab-${t.id}`}
              onClick={() => setTab(t.id)}
              className={`rm-pill flex items-center gap-2 px-4 py-2 text-sm ${tab === t.id ? "bg-white/10 border-white/20 text-white" : "text-zinc-400 hover:text-white"}`}
            >
              <Icon className="w-4 h-4" /> {t.label}
            </button>
          );
        })}
      </div>

      <div className="rm-card p-5">
        <div className="text-sm text-zinc-400 mb-4 flex items-start gap-2">
          <FileText className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span>{cfg.desc}</span>
        </div>

        {cfg.endpoint ? (
          cfg.custom ? (
            cfg.id === "backfill-period" ? <BackfillPeriodPanel /> :
            cfg.id === "materialize-artists" ? <MaterializeArtistsPanel /> :
            <WithdrawFifoPanel />
          ) : (
            <CsvImportPanel kind={cfg.endpoint} />
          )
        ) : (
          <ClaimsPanel />
        )}
      </div>
    </div>
  );
}

function CsvImportPanel({ kind }) {
  const [file, setFile] = useState(null);
  const [dryRun, setDryRun] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");
  const inputRef = useRef(null);

  const downloadTemplate = async () => {
    const res = await api.get(`/admin/migrate/template/${kind}`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const a = document.createElement("a");
    a.href = url; a.download = `template_${kind}.csv`; a.click();
    window.URL.revokeObjectURL(url);
  };

  const downloadReport = () => {
    if (!result?.report) return;
    const headers = Object.keys(result.report[0]);
    const csv = [
      headers.join(","),
      ...result.report.map(r => headers.map(h => JSON.stringify(r[h] ?? "")).join(","))
    ].join("\n");
    const url = window.URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url; a.download = `migrate_${kind}_report.csv`; a.click();
    window.URL.revokeObjectURL(url);
  };

  const submit = async () => {
    if (!file) {
      setErr("Pilih file CSV terlebih dahulu");
      return;
    }
    setErr(""); setResult(null); setLoading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("dry_run", dryRun ? "true" : "false");
      const { data } = await api.post(`/admin/migrate/${kind}`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      setResult(data);
    } catch (e) {
      setErr(e.response?.data?.detail || "Upload gagal");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={downloadTemplate}
          className="rm-btn-secondary text-xs flex items-center gap-2"
          data-testid={`admin-migrate-${kind}-template`}
        >
          <Download className="w-3.5 h-3.5" /> Download Template
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          onChange={(e) => { setFile(e.target.files?.[0] || null); setResult(null); setErr(""); }}
          className="text-xs text-zinc-300 file:rm-btn-secondary file:mr-3 file:px-3 file:py-1.5 file:border-0 file:cursor-pointer"
          data-testid={`admin-migrate-${kind}-file`}
        />
        <label className="text-xs text-zinc-400 flex items-center gap-2 cursor-pointer ml-auto">
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(e) => setDryRun(e.target.checked)}
            className="accent-[#FF1F8E]"
            data-testid={`admin-migrate-${kind}-dryrun`}
          />
          Dry-run (preview saja)
        </label>
        <button
          onClick={submit}
          disabled={!file || loading}
          className="rm-btn-primary text-xs flex items-center gap-2"
          data-testid={`admin-migrate-${kind}-submit`}
        >
          <Upload className="w-3.5 h-3.5" />
          {loading ? "Memproses…" : dryRun ? "Preview Dry-run" : "Import Sekarang"}
        </button>
      </div>

      {err && (
        <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm flex items-start gap-2">
          <AlertCircle className="w-4 h-4 mt-0.5" /> <span>{String(err)}</span>
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Stat label="Total Baris" value={result.total_rows} color="text-zinc-200" />
            <Stat label="Inserted" value={result.inserted} color="text-emerald-300" />
            <Stat label="Skipped" value={result.skipped ?? 0} color="text-amber-300" />
            <Stat label="Errors" value={result.errors} color="text-red-300" />
          </div>
          {result.dry_run && (
            <div className="rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-200 text-xs px-3 py-2 flex items-center gap-2">
              <AlertCircle className="w-3.5 h-3.5" /> Ini adalah <b>dry-run</b> — data BELUM disimpan. Untik commit, uncheck dry-run lalu submit lagi.
            </div>
          )}
          <div className="flex justify-between items-center">
            <div className="text-xs text-zinc-500">Menampilkan {Math.min(result.report.length, 20)} dari {result.report.length} baris report.</div>
            <button onClick={downloadReport} className="rm-btn-secondary text-xs flex items-center gap-2">
              <Download className="w-3.5 h-3.5" /> Download Report CSV
            </button>
          </div>
          <div className="overflow-x-auto rounded-2xl border border-white/5">
            <table className="w-full text-xs">
              <thead className="bg-white/[0.03] text-zinc-400">
                <tr>
                  <th className="px-3 py-2 text-left">Row</th>
                  <th className="px-3 py-2 text-left">Status</th>
                  <th className="px-3 py-2 text-left">Detail</th>
                  <th className="px-3 py-2 text-left">Reason</th>
                </tr>
              </thead>
              <tbody>
                {result.report.slice(0, 20).map((r, i) => (
                  <tr key={i} className="border-t border-white/5">
                    <td className="px-3 py-2 text-zinc-500">{r.row}</td>
                    <td className="px-3 py-2">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        r.status === "OK" ? "bg-emerald-500/15 text-emerald-300" :
                        r.status === "SKIPPED" ? "bg-amber-500/15 text-amber-300" :
                        "bg-red-500/15 text-red-300"
                      }`}>
                        {r.status === "OK" ? <CheckCircle2 className="inline w-3 h-3 mr-0.5" /> :
                          r.status === "SKIPPED" ? <Clock className="inline w-3 h-3 mr-0.5" /> :
                          <AlertCircle className="inline w-3 h-3 mr-0.5" />}
                        {r.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-zinc-200">{r.label_name || r.release_title || r.track_title}</td>
                    <td className="px-3 py-2 text-zinc-500">{r.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, color }) {
  return (
    <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-3">
      <div className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold">{label}</div>
      <div className={`text-xl font-bold mt-1 ${color}`}>{value ?? 0}</div>
    </div>
  );
}

function ClaimsPanel() {
  const [claims, setClaims] = useState([]);
  const [search, setSearch] = useState("");
  const [unclaimed, setUnclaimed] = useState([]);
  const [activeClaim, setActiveClaim] = useState(null);
  const [loading, setLoading] = useState(false);

  const reload = async () => {
    const { data } = await api.get("/admin/migrate/claims");
    setClaims(data);
  };
  useEffect(() => { reload(); }, []);

  const openLink = async (claim) => {
    setActiveClaim(claim);
    const { data } = await api.get(`/admin/migrate/labels/unclaimed?q=${encodeURIComponent(claim.claim_legacy_name || "")}`);
    setUnclaimed(data);
    setSearch(claim.claim_legacy_name || "");
  };
  const searchAgain = async () => {
    const { data } = await api.get(`/admin/migrate/labels/unclaimed?q=${encodeURIComponent(search)}`);
    setUnclaimed(data);
  };
  const doLink = async (legacy) => {
    setLoading(true);
    try {
      await api.post(`/admin/migrate/claims/${activeClaim.id}/link/${legacy.id}`);
      setActiveClaim(null); setUnclaimed([]); await reload();
    } catch (e) {
      alert(e.response?.data?.detail || "Link gagal");
    } finally { setLoading(false); }
  };
  const doReject = async (claim) => {
    const reason = window.prompt("Alasan reject?", "Data tidak cocok");
    if (reason === null) return;
    const fd = new FormData(); fd.append("reason", reason);
    await api.post(`/admin/migrate/claims/${claim.id}/reject`, fd, { headers: { "Content-Type": "multipart/form-data" } });
    await reload();
  };

  return (
    <div className="space-y-5">
      <div className="text-xs text-zinc-400">
        Total pending claims: <b className="text-zinc-200">{claims.length}</b>
      </div>

      {claims.length === 0 ? (
        <div className="text-center text-zinc-500 py-10 text-sm">
          <UserCheck className="w-8 h-8 mx-auto mb-2 opacity-50" />
          Belum ada permintaan claim akun lama.
        </div>
      ) : (
        <div className="space-y-3">
          {claims.map((c) => (
            <div key={c.id} className="rounded-2xl border border-white/5 bg-white/[0.02] p-4 flex flex-wrap items-start justify-between gap-3" data-testid={`admin-claim-${c.id}`}>
              <div className="text-sm space-y-1">
                <div className="font-semibold">{c.name} <span className="text-zinc-500 text-xs">· {c.email}</span></div>
                <div className="text-xs text-zinc-400">
                  Klaim sebagai: <b className="text-zinc-200">{c.claim_legacy_name}</b>
                </div>
                <div className="text-xs text-zinc-500">
                  Nama baru: {c.claim_label_name_new} · WA: {c.claim_whatsapp}
                </div>
                <div className="text-[10px] text-zinc-600">Diajukan: {c.claim_requested_at?.slice(0, 16)?.replace("T", " ")}</div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => openLink(c)}
                  className="rm-btn-primary text-xs flex items-center gap-2"
                  data-testid={`admin-claim-link-${c.id}`}
                >
                  <UserCheck className="w-3.5 h-3.5" /> Link
                </button>
                <button
                  onClick={() => doReject(c)}
                  className="rm-btn-secondary text-xs flex items-center gap-2 text-red-300"
                  data-testid={`admin-claim-reject-${c.id}`}
                >
                  <UserX className="w-3.5 h-3.5" /> Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeClaim && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="rm-card max-w-2xl w-full p-6 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <div>
                <div className="text-lg font-bold">Link ke Legacy Label</div>
                <div className="text-xs text-zinc-400 mt-1">
                  Klaimer: <b>{activeClaim.email}</b> mengaku punya label <b className="text-zinc-200">{activeClaim.claim_legacy_name}</b>
                </div>
              </div>
              <button onClick={() => { setActiveClaim(null); setUnclaimed([]); }} className="text-zinc-400 hover:text-white text-xl">×</button>
            </div>
            <div className="flex gap-2 mb-3">
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="rm-input flex-1"
                placeholder="Cari nama label lama…"
              />
              <button onClick={searchAgain} className="rm-btn-secondary text-xs px-4">Cari</button>
            </div>
            <div className="space-y-2">
              {unclaimed.length === 0 && (
                <div className="text-center text-zinc-500 text-sm py-6">Tidak ditemukan legacy label unclaimed.</div>
              )}
              {unclaimed.map((lab) => (
                <div key={lab.id} className="rounded-xl border border-white/5 bg-white/[0.02] p-3 flex items-center justify-between gap-3">
                  <div className="text-sm">
                    <div className="font-semibold">{lab.label_name}</div>
                    <div className="text-xs text-zinc-500">{lab.city || "—"} · PIC: {lab.pic_name || "—"} · {lab.subscription_tier || "no sub"}</div>
                  </div>
                  <button
                    onClick={() => doLink(lab)}
                    disabled={loading}
                    className="rm-btn-primary text-xs"
                    data-testid={`admin-claim-link-confirm-${lab.id}`}
                  >
                    Link
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


function WithdrawFifoPanel() {
  const [file, setFile] = useState(null);
  const [dryRun, setDryRun] = useState(true);
  const [createHistory, setCreateHistory] = useState(true);
  const [flipLines, setFlipLines] = useState(true);
  const [adjustBalances, setAdjustBalances] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");
  const [showUnmatched, setShowUnmatched] = useState(true);
  // Phase 26: commit now spawns a background job. We poll until done.
  const [job, setJob] = useState(null);
  const pollRef = useRef(null);

  // Cleanup polling on unmount
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
      fd.append("create_history_docs", createHistory ? "true" : "false");
      fd.append("flip_royalty_lines", flipLines ? "true" : "false");
      fd.append("adjust_balances", adjustBalances ? "true" : "false");
      const { data } = await api.post("/admin/migrate/withdraws-legacy-period", fd, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 110000,  // close to ingress 120s — preview/dry-run still sync
      });
      setResult(data);
      // If commit produced a background job, start polling.
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

  const fmtIDR = (n) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 text-amber-200 text-xs px-4 py-3">
        <b>Format CSV yang diharapkan:</b> kolom <code>nama_label</code> + <code>period_end</code> (YYYY-MM) wajib. Optional: <code>period_start, trx_id, amount, exchange_rate, request_date, payment_date, status</code>.
        Tool ini akan: (1) set <code>last_withdrawn_period = MAX(period_end)</code> per label, (2) flip royalty_lines historical → status withdrawn, (3) decrement balance, (4) insert riwayat withdraw_requests dengan <code>legacy_import=true</code>.
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          type="file"
          accept=".csv"
          onChange={(e) => { setFile(e.target.files?.[0] || null); setResult(null); setErr(""); }}
          className="text-xs text-zinc-300 file:rm-btn-secondary file:mr-3 file:px-3 file:py-1.5 file:border-0 file:cursor-pointer"
          data-testid="admin-migrate-withdraws-fifo-file"
        />
        <button
          onClick={submit}
          disabled={!file || loading}
          className="rm-btn-primary text-xs flex items-center gap-2"
          data-testid="admin-migrate-withdraws-fifo-submit"
        >
          <Upload className="w-3.5 h-3.5" />
          {loading ? "Memproses…" : dryRun ? "Preview Dry-run" : "COMMIT (data akan diubah)"}
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
        <label className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 cursor-pointer hover:bg-white/10">
          <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} className="accent-[#FF1F8E]" data-testid="admin-migrate-withdraws-fifo-dryrun" />
          <span>Dry-run (preview saja)</span>
        </label>
        <label className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 cursor-pointer hover:bg-white/10">
          <input type="checkbox" checked={createHistory} onChange={(e) => setCreateHistory(e.target.checked)} className="accent-[#FF1F8E]" />
          <span>Insert riwayat withdraw_requests</span>
        </label>
        <label className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 cursor-pointer hover:bg-white/10">
          <input type="checkbox" checked={flipLines} onChange={(e) => setFlipLines(e.target.checked)} className="accent-[#FF1F8E]" />
          <span>Flip royalty_lines → withdrawn</span>
        </label>
        <label className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 cursor-pointer hover:bg-white/10">
          <input type="checkbox" checked={adjustBalances} onChange={(e) => setAdjustBalances(e.target.checked)} className="accent-[#FF1F8E]" />
          <span>Adjust balance saldo</span>
        </label>
      </div>

      {err && (
        <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm flex items-start gap-2">
          <AlertCircle className="w-4 h-4 mt-0.5" /> <span>{String(err)}</span>
        </div>
      )}

      {result && (
        <div className="space-y-4">
          {result.dry_run ? (
            <div className="rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-200 text-xs px-3 py-2 flex items-center gap-2">
              <AlertCircle className="w-3.5 h-3.5" /> Mode <b>dry-run</b> — data BELUM diubah. Review report di bawah, lalu uncheck Dry-run + klik Commit.
            </div>
          ) : result.commit?.queued ? (
            <div className="rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-200 text-xs px-3 py-2 space-y-1.5">
              <div className="flex items-center gap-2 font-semibold">
                <Loader2 className="w-3.5 h-3.5 animate-spin" /> COMMIT DIJADWALKAN DI BACKGROUND
              </div>
              <div className="font-mono text-[11px] text-indigo-300/70">Job ID: {result.job_id}</div>
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
                  {job.progress_lines_flipped !== undefined && (
                    <div className="flex justify-between gap-2">
                      <span>Lines flipped</span>
                      <span className="font-mono">{(job.progress_lines_flipped || 0).toLocaleString("id-ID")}</span>
                    </div>
                  )}
                  {job.progress_history_inserted !== undefined && (
                    <div className="flex justify-between gap-2">
                      <span>History docs inserted</span>
                      <span className="font-mono">{(job.progress_history_inserted || 0).toLocaleString("id-ID")}</span>
                    </div>
                  )}
                  {job.error_message && (
                    <div className="text-red-300 mt-1 font-mono break-all">{job.error_message}</div>
                  )}
                  {job.status === "done" && job.result && (
                    <div className="grid grid-cols-2 gap-1 pt-2 mt-1 border-t border-indigo-500/20">
                      <div>Labels updated: <b className="font-mono">{job.result.labels_period_updated}</b></div>
                      <div>Lines flipped: <b className="font-mono">{(job.result.royalty_lines_flipped || 0).toLocaleString("id-ID")}</b></div>
                      <div>History inserted: <b className="font-mono">{job.result.history_docs_inserted}</b></div>
                      <div>Balance pending −: <b className="font-mono">{fmtIDR(job.result.balance_pending_subtracted)}</b></div>
                    </div>
                  )}
                </>
              )}
            </div>
          ) : (
            <div className="rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-200 text-xs px-3 py-2 flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5" /> <b>COMMITTED.</b> {JSON.stringify(result.commit)}
            </div>
          )}

          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <Stat label="Total CSV Rows" value={result.total_csv_rows} color="text-zinc-200" />
            <Stat label="Matched Labels" value={result.matched_labels} color="text-emerald-300" />
            <Stat label="Unmatched Labels" value={result.unmatched_label_count} color="text-amber-300" />
            <Stat label="Lines akan di-flip" value={result.totals_preview.royalty_lines_to_flip.toLocaleString("id-ID")} color="text-indigo-300" />
            <Stat label="History docs insert" value={result.totals_preview.history_docs_to_insert} color="text-rose-300" />
          </div>

          <div className="grid md:grid-cols-2 gap-3">
            <div className="rm-card p-4">
              <div className="text-xs uppercase font-bold text-zinc-500 tracking-widest mb-2">Balance Adjustment Preview</div>
              <div className="text-sm space-y-1.5">
                <div className="flex justify-between"><span className="text-zinc-500">Pending → withdrawn</span><span className="text-amber-300 font-mono">{fmtIDR(result.totals_preview.balance_pending_to_subtract)}</span></div>
                <div className="flex justify-between"><span className="text-zinc-500">Available → withdrawn</span><span className="text-emerald-300 font-mono">{fmtIDR(result.totals_preview.balance_available_to_subtract)}</span></div>
              </div>
            </div>
            <div className="rm-card p-4">
              <div className="text-xs uppercase font-bold text-zinc-500 tracking-widest mb-2">Period Update Preview</div>
              <div className="text-sm">
                <div><b className="text-emerald-300">{result.totals_preview.labels_period_will_advance}</b> label akan diadvance <code>last_withdrawn_period</code></div>
                <div className="text-xs text-zinc-500 mt-1">Yang tidak diadvance = MAX(period_end) di CSV lebih lama atau sama dengan nilai saat ini (idempotent).</div>
              </div>
            </div>
          </div>

          {result.unmatched_label_count > 0 && (
            <div className="rm-card p-4">
              <button onClick={() => setShowUnmatched((s) => !s)} className="w-full flex items-center justify-between text-xs font-bold uppercase tracking-widest text-zinc-500">
                <span>Unmatched Labels — perlu di-fix manual</span>
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
            <div className="text-xs uppercase font-bold text-zinc-500 tracking-widest mb-3">Per-Label Summary ({(result.label_summaries || []).length})</div>
            <div className="overflow-x-auto rounded-2xl border border-white/5">
              <table className="w-full text-xs">
                <thead className="bg-white/[0.03] text-zinc-400">
                  <tr>
                    <th className="px-3 py-2 text-left">Label</th>
                    <th className="px-3 py-2 text-left">Old → New Period</th>
                    <th className="px-3 py-2 text-right">CSV Rows</th>
                    <th className="px-3 py-2 text-right">Lines Flip</th>
                    <th className="px-3 py-2 text-right">Available − IDR</th>
                  </tr>
                </thead>
                <tbody>
                  {(result.label_summaries || []).map((s) => (
                    <tr key={s.label_id} className="border-t border-white/5">
                      <td className="px-3 py-2 text-zinc-200">{s.label_name}</td>
                      <td className="px-3 py-2 text-xs"><span className="text-zinc-500">{s.old_last_withdrawn_period || "—"}</span> <span className="text-zinc-600 mx-1">→</span> <span className={s.period_will_advance ? "text-emerald-300" : "text-zinc-500"}>{s.new_last_withdrawn_period}</span></td>
                      <td className="px-3 py-2 text-right text-zinc-400">{s.csv_row_count}</td>
                      <td className="px-3 py-2 text-right text-indigo-300">{s.royalty_lines_to_flip.toLocaleString("id-ID")}</td>
                      <td className="px-3 py-2 text-right text-emerald-300 font-mono">{fmtIDR(s.available_to_subtract_idr)}</td>
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



function BackfillPeriodPanel() {
  const [importId, setImportId] = useState("");
  const [dryRun, setDryRun] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");
  const [imports, setImports] = useState([]);

  // Load imports list once for the dropdown
  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/royalty/admin/imports");
        setImports(Array.isArray(data) ? data : []);
      } catch (e) { /* swallow */ }
    })();
  }, []);

  const run = async () => {
    setLoading(true); setErr(""); setResult(null);
    try {
      const fd = new FormData();
      fd.append("dry_run", dryRun ? "true" : "false");
      if (importId) fd.append("import_id", importId);
      const { data } = await api.post(
        "/admin/migrate/royalty/backfill-period-from-row",
        fd,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      setResult(data);
    } catch (e) {
      setErr(e.response?.data?.detail || e.message || "Backfill gagal");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 text-amber-200 text-xs flex gap-2">
        <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
        <div className="space-y-1.5">
          <p>
            Tool ini mem-flip <code className="bg-black/30 px-1 rounded">royalty_lines.period = row_period</code> untuk semua baris di mana
            <code className="bg-black/30 px-1 rounded mx-1">row_period</code> (nilai kolom <b>Bulan Laporan</b> di CSV) berbeda dari <code className="bg-black/30 px-1 rounded">period</code> yang tersimpan.
          </p>
          <p>
            <b>Kapan dipakai?</b> Jika upload sebelum Phase 23.1 menyebabkan semua baris yearly CSV ter-tag 1 bulan padahal kolom <b>Bulan Laporan</b> menunjukkan 12 bulan berbeda. Setelah commit, Artist/Release/Label/Analytics akan tampil dengan grouping bulan yang benar.
          </p>
          <p className="text-amber-300/80">
            <b>Aman dijalankan berulang</b> — hanya baris dengan <code className="bg-black/30 px-1 rounded">row_period ≠ period</code> yang tersentuh.
          </p>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-zinc-400 mb-1 block">Scope (opsional)</label>
          <select
            value={importId}
            onChange={(e) => setImportId(e.target.value)}
            className="rm-input w-full text-sm"
            data-testid="admin-migrate-backfill-period-import"
          >
            <option value="">— Semua import (full database backfill) —</option>
            {imports.map((i) => (
              <option key={i.id} value={i.id}>
                {(i.period || i.period_start || "?")} · {i.filename || i.id.slice(0,8)} · {i.status} · {(i.total_lines || 0).toLocaleString("id-ID")} baris
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-end gap-3">
          <label className="flex items-center gap-2 text-sm text-zinc-300">
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
              data-testid="admin-migrate-backfill-period-dryrun"
              className="rm-checkbox"
            />
            <span>Dry-run (preview saja, tidak commit)</span>
          </label>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={run}
          disabled={loading}
          data-testid="admin-migrate-backfill-period-submit"
          className="rm-btn flex items-center gap-2 disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCw className="w-4 h-4" />}
          {dryRun ? "Preview Backfill (Dry Run)" : "COMMIT Backfill"}
        </button>
        {!dryRun && (
          <span className="text-xs text-rose-300 flex items-center gap-1">
            <AlertCircle className="w-3 h-3" /> Akan menulis ke royalty_lines + recompute imports
          </span>
        )}
      </div>

      {err && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-200 text-sm">
          {typeof err === "string" ? err : JSON.stringify(err)}
        </div>
      )}

      {result && (
        <div className="space-y-3">
          <div className={`rounded-lg p-3 text-sm border ${result.dry_run ? "bg-amber-500/10 border-amber-500/30 text-amber-200" : "bg-emerald-500/10 border-emerald-500/30 text-emerald-200"}`}>
            <div className="flex items-center gap-2 font-semibold">
              {result.dry_run ? <Clock className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
              {result.dry_run ? "PREVIEW (Dry Run)" : "BACKFILL COMMITTED"}
            </div>
            <div className="mt-2 grid sm:grid-cols-3 gap-3 text-xs">
              <BfStat label="Baris Akan Difix" value={result.total_rows_to_fix?.toLocaleString("id-ID") || 0} />
              <BfStat label="Imports Terdampak" value={result.imports_affected || 0} />
              {result.commit ? (
                <BfStat label="Baris Updated" value={result.commit.rows_updated?.toLocaleString("id-ID") || 0} />
              ) : (
                <BfStat label="Mode" value={importId ? "Single import" : "Full DB"} />
              )}
            </div>
          </div>

          {result.summary && result.summary.length > 0 && (
            <div className="rm-card-inner p-4 space-y-3">
              <div className="text-sm font-semibold text-white flex items-center justify-between">
                <span>Per-Import Preview</span>
                <span className="text-xs text-zinc-500">({result.summary.length} ditampilkan)</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs border-collapse">
                  <thead className="bg-white/[0.04] text-zinc-400">
                    <tr>
                      <th className="text-left px-3 py-2">File</th>
                      <th className="text-left px-3 py-2">Status</th>
                      <th className="text-right px-3 py-2">Total Baris</th>
                      <th className="text-right px-3 py-2">Akan Difix</th>
                      <th className="text-left px-3 py-2">Periode Sekarang</th>
                      <th className="text-left px-3 py-2">→ Periode Baru</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.summary.map((s, idx) => (
                      <tr key={idx} className="border-t border-white/5">
                        <td className="px-3 py-2 text-zinc-300 max-w-xs truncate" title={s.filename}>{s.filename || s.import_id.slice(0,8)}</td>
                        <td className="px-3 py-2 text-zinc-400">{s.status}</td>
                        <td className="px-3 py-2 text-right text-zinc-400">{(s.total_lines || 0).toLocaleString("id-ID")}</td>
                        <td className="px-3 py-2 text-right text-amber-300 font-semibold">{s.rows_to_fix.toLocaleString("id-ID")}</td>
                        <td className="px-3 py-2 text-rose-200 font-mono text-[10px]">{(s.old_periods_in_lines || []).join(", ")}</td>
                        <td className="px-3 py-2 text-emerald-200 font-mono text-[10px]">{(s.new_periods_will_be || []).join(", ")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {result.commit && result.recomputed_imports && (
            <div className="rm-card-inner p-4 space-y-3">
              <div className="text-sm font-semibold text-white">Imports Recomputed</div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs border-collapse">
                  <thead className="bg-white/[0.04] text-zinc-400">
                    <tr>
                      <th className="text-left px-3 py-2">File</th>
                      <th className="text-left px-3 py-2">Periode Baru</th>
                      <th className="text-left px-3 py-2">Range</th>
                      <th className="text-right px-3 py-2">Bulan</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.recomputed_imports.map((r, idx) => (
                      <tr key={idx} className="border-t border-white/5">
                        <td className="px-3 py-2 text-zinc-300 max-w-xs truncate">{r.filename || r.import_id?.slice(0,8)}</td>
                        <td className="px-3 py-2 text-emerald-200 font-mono">{r.display_period}</td>
                        <td className="px-3 py-2 text-zinc-400">{r.new_period_start} → {r.new_period_end}</td>
                        <td className="px-3 py-2 text-right text-zinc-300">{r.new_period_breakdown ? Object.keys(r.new_period_breakdown).length : 0}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function BfStat({ label, value }) {
  return (
    <div className="bg-black/30 rounded p-2">
      <div className="text-[10px] uppercase tracking-wider text-zinc-500">{label}</div>
      <div className="text-base font-mono text-white">{value}</div>
    </div>
  );
}


function MaterializeArtistsPanel() {
  const [dryRun, setDryRun] = useState(true);
  const [limit, setLimit] = useState(0);  // 0 = no limit
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");

  const run = async () => {
    setLoading(true); setErr(""); setResult(null);
    try {
      const fd = new FormData();
      fd.append("dry_run", dryRun ? "true" : "false");
      if (limit > 0) fd.append("limit_combos", String(limit));
      const { data } = await api.post(
        "/admin/migrate/materialize-artists",
        fd,
        { headers: { "Content-Type": "multipart/form-data" }, timeout: 180000 },
      );
      setResult(data);
    } catch (e) {
      setErr(e.response?.data?.detail || e.message || "Materialize gagal");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 text-amber-200 text-xs flex gap-2">
        <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
        <div className="space-y-1.5">
          <p>
            <b>Kenapa tool ini ada?</b> Ingestion CSV royalti otomatis membuat <code className="bg-black/30 px-1 rounded">labels</code>, <code className="bg-black/30 px-1 rounded">releases</code>, dan <code className="bg-black/30 px-1 rounded">tracks</code>, tapi <b>TIDAK</b> membuat dokumen artist. Akibatnya halaman Artist Management kosong walau royalty_lines sudah ada.
          </p>
          <p>
            Tool ini scan kolom <code className="bg-black/30 px-1 rounded">artist_name</code> di <code className="bg-black/30 px-1 rounded">royalty_lines</code>, buat satu dokumen artist per (label_id, nama artist), lalu backfill <code className="bg-black/30 px-1 rounded">artist_id</code> di lines + tracks. Setelah commit, refresh Artist Management — semua artist langsung muncul beserta total revenue per bulan.
          </p>
          <p className="text-amber-300/80">
            <b>Aman dijalankan berulang</b> — hanya artist baru (label_id + nama yang belum ada) yang dibuat.
          </p>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-zinc-400 mb-1 block">Limit Combos (opsional)</label>
          <input
            type="number"
            value={limit}
            onChange={(e) => setLimit(Math.max(0, parseInt(e.target.value) || 0))}
            placeholder="0 = semua"
            className="rm-input w-full text-sm"
            data-testid="admin-migrate-materialize-artists-limit"
          />
          <p className="text-[10px] text-zinc-500 mt-1">Berguna untuk uji dengan sample kecil (mis. 100) sebelum full commit.</p>
        </div>
        <div className="flex items-end gap-3">
          <label className="flex items-center gap-2 text-sm text-zinc-300">
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
              data-testid="admin-migrate-materialize-artists-dryrun"
              className="rm-checkbox"
            />
            <span>Dry-run (preview saja, tidak commit)</span>
          </label>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={run}
          disabled={loading}
          data-testid="admin-migrate-materialize-artists-submit"
          className="rm-btn flex items-center gap-2 disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {dryRun ? "Preview Materialize (Dry Run)" : "COMMIT Materialize Artists"}
        </button>
        {!dryRun && (
          <span className="text-xs text-rose-300 flex items-center gap-1">
            <AlertCircle className="w-3 h-3" /> Akan insert ke artists + update royalty_lines + tracks
          </span>
        )}
      </div>

      {err && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-200 text-sm">
          {typeof err === "string" ? err : JSON.stringify(err)}
        </div>
      )}

      {result && (
        <div className="space-y-3">
          <div className={`rounded-lg p-3 text-sm border ${result.dry_run ? "bg-amber-500/10 border-amber-500/30 text-amber-200" : "bg-emerald-500/10 border-emerald-500/30 text-emerald-200"}`}>
            <div className="flex items-center gap-2 font-semibold">
              {result.dry_run ? <Clock className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
              {result.dry_run ? "PREVIEW (Dry Run)" : "ARTISTS MATERIALIZED"}
            </div>
            <div className="mt-2 grid sm:grid-cols-4 gap-3 text-xs">
              <BfStat label="Combos di Lines" value={result.combos_in_lines?.toLocaleString("id-ID") || 0} />
              <BfStat label="Sudah Ada" value={result.artists_already_existed?.toLocaleString("id-ID") || 0} />
              <BfStat label="Akan Dibuat" value={result.artists_to_create?.toLocaleString("id-ID") || 0} />
              {result.commit ? (
                <BfStat label="Lines Updated" value={result.commit.lines_updated?.toLocaleString("id-ID") || 0} />
              ) : (
                <BfStat label="Mode" value={limit > 0 ? `Limit ${limit}` : "Full"} />
              )}
            </div>
            {result.commit && (
              <div className="mt-2 text-xs text-emerald-300">
                {result.commit.artists_created.toLocaleString("id-ID")} artist created · {result.commit.lines_updated.toLocaleString("id-ID")} lines updated · {result.commit.tracks_updated.toLocaleString("id-ID")} tracks updated. Cache analytics akan auto-rebuild.
              </div>
            )}
          </div>

          {result.top_preview && result.top_preview.length > 0 && (
            <div className="rm-card-inner p-4 space-y-3">
              <div className="text-sm font-semibold text-white flex items-center justify-between">
                <span>Top {result.top_preview.length} (by revenue) yang akan dibuat</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs border-collapse">
                  <thead className="bg-white/[0.04] text-zinc-400">
                    <tr>
                      <th className="text-left px-3 py-2">Nama Artist</th>
                      <th className="text-left px-3 py-2">Label ID</th>
                      <th className="text-right px-3 py-2">Lines</th>
                      <th className="text-right px-3 py-2">Revenue EUR</th>
                      <th className="text-right px-3 py-2">Label IDR</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.top_preview.map((a, idx) => (
                      <tr key={idx} className="border-t border-white/5">
                        <td className="px-3 py-2 text-zinc-300 max-w-xs truncate" title={a.artist_name}>{a.artist_name}</td>
                        <td className="px-3 py-2 text-zinc-500 font-mono text-[10px] max-w-[160px] truncate">{a.label_id}</td>
                        <td className="px-3 py-2 text-right text-zinc-400">{a.lines.toLocaleString("id-ID")}</td>
                        <td className="px-3 py-2 text-right text-zinc-400">€{a.revenue_eur.toLocaleString("id-ID")}</td>
                        <td className="px-3 py-2 text-right text-emerald-300 font-mono">Rp {a.label_idr.toLocaleString("id-ID")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

