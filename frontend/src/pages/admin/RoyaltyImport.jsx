import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { Upload, FileSpreadsheet, CheckCircle2, Banknote, AlertTriangle, Trash2, Loader2, RefreshCw, XCircle } from "lucide-react";

function fmtIDR(n) { return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0); }
function fmtEUR(n) { return new Intl.NumberFormat("en-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 2 }).format(n || 0); }

function todayPeriod() {
  const d = new Date();
  d.setMonth(d.getMonth() - 1);
  return d.toISOString().slice(0, 7);
}

export default function AdminRoyaltyImport() {
  const [imports, setImports] = useState([]);
  const [open, setOpen] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);
  const [resetConfirm, setResetConfirm] = useState("");
  const [form, setForm] = useState({ period: todayPeriod(), rate_eur_idr: 17500, file: null, note: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => { const { data } = await api.get("/royalty/admin/imports"); setImports(data); };
  useEffect(() => { load(); }, []);

  // Auto-poll every 4s while any import is still 'processing'
  const pollRef = useRef(null);
  useEffect(() => {
    const anyProcessing = imports.some((i) => i.status === "processing");
    if (anyProcessing && !pollRef.current) {
      pollRef.current = setInterval(load, 4000);
    } else if (!anyProcessing && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [imports]);

  const retry = async (id, e) => {
    e.preventDefault();
    e.stopPropagation();
    setErr(""); setMsg("");
    try {
      await api.post(`/royalty/admin/imports/${id}/retry`);
      setMsg("Retry dijadwalkan — proses akan jalan di background.");
      load();
    } catch (e2) { setErr(formatApiError(e2.response?.data?.detail)); }
  };

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setMsg("");
    if (!form.file) { setErr("File CSV wajib diupload"); return; }
    if (!form.period.match(/^\d{4}-\d{2}$/)) { setErr("Periode harus YYYY-MM"); return; }
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("period", form.period);
      fd.append("rate_eur_idr", form.rate_eur_idr);
      fd.append("note", form.note || "");
      fd.append("file", form.file);
      await api.post("/royalty/admin/imports", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setMsg("CSV diupload & diparse.");
      setOpen(false);
      setForm({ period: todayPeriod(), rate_eur_idr: 17500, file: null, note: "" });
      load();
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const submitReset = async (e) => {
    e.preventDefault();
    setErr(""); setMsg("");
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("confirm", resetConfirm);
      const { data } = await api.post("/royalty/admin/reset-demo-data", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setMsg(`Reset selesai — ${data.imports_deleted} import, ${data.lines_deleted} lines, ${data.transactions_deleted} transaksi dihapus. ${data.labels_reset} label balance di-reset.`);
      setResetOpen(false);
      setResetConfirm("");
      load();
    } catch (e2) { setErr(formatApiError(e2.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-5">
      <div className="flex justify-between items-center flex-wrap gap-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Finance</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter">Royalty Import</h1>
          <p className="text-sm text-zinc-400 mt-1">Upload CSV Believe (EUR) + set kurs IDR per periode.</p>
        </div>
        <div className="flex gap-2">
          <button
            className="rm-btn-ghost flex items-center gap-2 text-red-300 hover:text-red-200"
            onClick={() => setResetOpen(true)}
            data-testid="admin-royalty-reset-button"
            title="Hapus semua data royalti (dummy) sebelum production"
          >
            <Trash2 className="w-4 h-4" /> Reset Data Demo
          </button>
          <button className="rm-btn-primary flex items-center gap-2" onClick={() => setOpen(true)} data-testid="admin-royalty-upload-button">
            <Upload className="w-4 h-4" /> Upload CSV
          </button>
        </div>
      </div>

      {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm">{err}</div>}
      {msg && <div className="rounded-2xl bg-emerald-500/15 text-emerald-300 px-4 py-3 text-sm">{msg}</div>}

      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5">
          <div className="col-span-2">Periode</div>
          <div className="col-span-2">Kurs</div>
          <div className="col-span-2">Revenue EUR</div>
          <div className="col-span-2">Bagian Label IDR</div>
          <div className="col-span-2">Lines (matched/total)</div>
          <div className="col-span-2">Status</div>
        </div>
        {imports.length === 0 ? <div className="p-10 text-center text-zinc-500 text-sm">Belum ada import. Klik &quot;Upload CSV&quot; untuk mulai.</div> : imports.map((i) => (
          <Link key={i.id} to={`/admin/royalty/${i.id}`} className="px-5 py-4 grid grid-cols-12 gap-3 items-center border-b border-white/5 last:border-0 hover:bg-white/[0.02]">
            <div className="col-span-12 md:col-span-2 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/100/15 text-amber-300 grid place-items-center"><FileSpreadsheet className="w-4 h-4" /></div>
              <div>
                <div className="font-display font-bold">{i.period}</div>
                {i.is_multi_period && <div className="text-[10px] text-zinc-500">multi-period</div>}
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
            <div className="col-span-12 md:col-span-2 flex items-center gap-2">
              <StatusBadge s={i.status} />
              {(i.status === "processing" || i.status === "error") && (
                <button
                  onClick={(e) => retry(i.id, e)}
                  className="rm-btn-ghost flex items-center gap-1 text-[10px] px-2 py-1"
                  data-testid={`royalty-import-retry-${i.id}`}
                  title="Retry background processing"
                >
                  <RefreshCw className="w-3 h-3" /> Retry
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
              <label className="rm-label">Periode (YYYY-MM)</label>
              <input className="rm-input" value={form.period} onChange={(e) => setForm({ ...form, period: e.target.value })} placeholder="2026-05" data-testid="admin-royalty-period" required />
            </div>
            <div>
              <label className="rm-label">Kurs EUR → IDR</label>
              <input type="number" min="1000" step="0.01" className="rm-input" value={form.rate_eur_idr} onChange={(e) => setForm({ ...form, rate_eur_idr: parseFloat(e.target.value) })} data-testid="admin-royalty-rate" required />
              <div className="text-[11px] text-zinc-500 mt-1">Kurs diinput manual per periode. Tidak bisa diubah setelah publish.</div>
            </div>
            <div>
              <label className="rm-label">File CSV Believe</label>
              <input type="file" accept=".csv,text/csv" className="rm-input" onChange={(e) => setForm({ ...form, file: e.target.files?.[0] || null })} data-testid="admin-royalty-file" />
              <div className="text-[11px] text-zinc-500 mt-1">Auto-detect kolom Believe (Indonesian + English): ISRC, UPC, Judul track, Nama Artis, Platform, Negara, Kuantias, Pendapatan Bersih (EUR). Format desimal Eropa <code>0,000123</code> didukung.</div>
            </div>
            <div>
              <label className="rm-label">Catatan (opsional)</label>
              <input className="rm-input" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" className="rm-btn-ghost" onClick={() => setOpen(false)}>Batal</button>
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
    published: { bg: "bg-sky-500/15", color: "text-sky-300", label: "Published", icon: CheckCircle2 },
    dana_received: { bg: "bg-emerald-500/15", color: "text-emerald-300", label: "Dana Diterima", icon: Banknote },
    error: { bg: "bg-red-500/15", color: "text-red-300", label: "Error", icon: XCircle },
  }[s] || { bg: "bg-white/[0.06]", color: "text-zinc-300", label: s };
  const Icon = map.icon;
  return <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold ${map.bg} ${map.color}`} data-testid={`royalty-status-${s}`}>{Icon && <Icon className={`w-3 h-3 ${map.spin ? "animate-spin" : ""}`} />}{map.label}</span>;
}
