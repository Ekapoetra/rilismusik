import React, { useEffect, useRef, useState } from "react";
import { ArrowDownToLine, Loader2, Upload, FileText, AlertTriangle, CheckCircle2, HelpCircle } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";

const Stat = ({ label, value, tone }) => (
  <div className={`rounded-lg border p-3 text-center ${tone}`} data-testid={`takedown-stat-${label}`}>
    <div className="text-2xl font-extrabold tabular-nums">{value}</div>
    <div className="mt-0.5 text-[11px] uppercase tracking-wider opacity-80">{label}</div>
  </div>
);

export default function TakedownImportModal({ open, onClose, onDone }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    if (!open) { setFile(null); setPreview(null); setError(""); setConfirm(false); setLoading(false); setProcessing(false); }
  }, [open]);

  const pick = (f) => { setFile(f); setPreview(null); setError(""); setConfirm(false); };

  const runPreview = async () => {
    if (!file) return;
    setLoading(true); setError(""); setPreview(null); setConfirm(false);
    const fd = new FormData(); fd.append("file", file);
    try {
      const { data } = await api.post("/admin/releases/takedown-import/preview", fd);
      setPreview(data);
    } catch (e) {
      setError(formatApiError(e.response?.data?.detail) || "Gagal membaca file.");
    } finally { setLoading(false); }
  };

  const runProcess = async () => {
    if (!file || !preview) return;
    setProcessing(true); setError("");
    const fd = new FormData(); fd.append("file", file);
    try {
      const { data } = await api.post("/admin/releases/takedown-import/process", fd);
      toast.success(`${data.updated} rilisan diturunkan (takedown).`);
      onDone?.();
      onClose?.();
    } catch (e) {
      setError(formatApiError(e.response?.data?.detail) || "Gagal memproses takedown.");
      setProcessing(false);
    }
  };

  const willCount = preview?.counts?.will_takedown || 0;

  return (
    <Dialog open={open} onOpenChange={(o) => !o && !processing && !loading && onClose?.()}>
      <DialogContent className="ui-menu max-h-[90dvh] w-[calc(100%-2rem)] max-w-3xl overflow-y-auto rounded-lg" data-testid="takedown-import-modal" closeTestId="takedown-import-close">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><ArrowDownToLine className="h-5 w-5 text-amber-400" /> Import Takedown Rilisan</DialogTitle>
          <DialogDescription>Unggah laporan katalog dari distributor (CSV). Rilisan yang UPC-nya cocok akan diubah statusnya menjadi <b>Diturunkan (takedown)</b>. Pratinjau dulu sebelum memproses.</DialogDescription>
        </DialogHeader>

        <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-white/20 bg-white/[0.02] px-4 py-8 text-center transition-colors hover:border-pink-400/50" data-testid="takedown-dropzone">
          <input ref={inputRef} type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => pick(e.target.files?.[0] || null)} data-testid="takedown-file-input" />
          {file ? (
            <div className="flex items-center gap-2 text-sm text-zinc-200"><FileText className="h-4 w-4 text-emerald-400" /> {file.name}</div>
          ) : (
            <><Upload className="h-6 w-6 text-zinc-500" /><span className="text-sm text-zinc-400">Klik untuk memilih file CSV</span></>
          )}
        </label>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="text-xs text-zinc-500">Pencocokan dilakukan berdasarkan <b>UPC</b>. Rilisan yang sudah takedown akan dilewati.</div>
          <button type="button" onClick={runPreview} disabled={!file || loading || processing} className="rm-btn-ghost inline-flex items-center gap-2 text-sm disabled:opacity-40" data-testid="takedown-preview-btn">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />} Pratinjau
          </button>
        </div>

        {error && <div role="alert" className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-300" data-testid="takedown-error">{error}</div>}

        {preview && (
          <div className="space-y-4" data-testid="takedown-preview">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label="Baris" value={preview.total_data_rows} tone="border-white/10 text-zinc-200" />
              <Stat label="Akan Takedown" value={preview.counts.will_takedown} tone="border-amber-400/40 bg-amber-400/[0.06] text-amber-200" />
              <Stat label="Sudah Takedown" value={preview.counts.already_taken_down} tone="border-white/10 text-zinc-400" />
              <Stat label="Tidak Ditemukan" value={preview.counts.not_found} tone="border-white/10 text-zinc-400" />
            </div>

            {preview.will_takedown.length > 0 && (
              <div className="rounded-lg border border-white/10">
                <div className="border-b border-white/10 px-3 py-2 text-xs font-bold uppercase tracking-wider text-amber-200">Akan diubah ke Takedown ({preview.counts.will_takedown})</div>
                <div className="max-h-56 overflow-y-auto divide-y divide-white/5" data-testid="takedown-will-list">
                  {preview.will_takedown.map((r) => (
                    <div key={r.release_id} className="flex items-center justify-between gap-3 px-3 py-2 text-sm" data-testid={`takedown-will-${r.release_id}`}>
                      <div className="min-w-0"><div className="truncate font-medium" translate="no">{r.release_title || "—"}</div><div className="truncate text-xs text-zinc-500" translate="no">{r.label_name || "—"} · UPC {r.upc}</div></div>
                      <span className="shrink-0 text-[11px] text-zinc-500">{r.current_status}</span>
                    </div>
                  ))}
                  {preview.counts.will_takedown > preview.will_takedown.length && <div className="px-3 py-2 text-center text-xs text-zinc-500">…dan {preview.counts.will_takedown - preview.will_takedown.length} lainnya</div>}
                </div>
              </div>
            )}

            {preview.not_found_upcs.length > 0 && (
              <details className="rounded-lg border border-white/10" data-testid="takedown-notfound">
                <summary className="cursor-pointer px-3 py-2 text-xs font-bold uppercase tracking-wider text-zinc-400 flex items-center gap-2"><HelpCircle className="h-3.5 w-3.5" /> UPC tidak ditemukan ({preview.counts.not_found})</summary>
                <div className="max-h-40 overflow-y-auto px-3 py-2 font-mono text-xs text-zinc-500">{preview.not_found_upcs.join(", ")}{preview.counts.not_found > preview.not_found_upcs.length ? " …" : ""}</div>
              </details>
            )}

            {willCount === 0 ? (
              <div className="flex items-center gap-2 rounded-md bg-white/[0.03] px-3 py-2 text-sm text-zinc-400" data-testid="takedown-nothing"><CheckCircle2 className="h-4 w-4 text-emerald-400" /> Tidak ada rilisan yang perlu diubah.</div>
            ) : !confirm ? (
              <button type="button" onClick={() => setConfirm(true)} disabled={processing} className="w-full rounded-md bg-amber-500 px-4 py-2.5 text-sm font-bold text-black transition-colors hover:bg-amber-400" data-testid="takedown-process-btn">Proses Takedown ({willCount} rilisan)</button>
            ) : (
              <div className="rounded-lg border border-amber-400/40 bg-amber-400/[0.06] p-3" data-testid="takedown-confirm">
                <div className="flex items-start gap-2 text-sm text-amber-100"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> Yakin menurunkan <b>{willCount}</b> rilisan menjadi status Takedown? Tindakan ini mengubah data.</div>
                <div className="mt-3 flex gap-2">
                  <button type="button" onClick={runProcess} disabled={processing} className="inline-flex items-center gap-2 rounded-md bg-amber-500 px-4 py-2 text-sm font-bold text-black hover:bg-amber-400 disabled:opacity-50" data-testid="takedown-confirm-btn">{processing ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowDownToLine className="h-4 w-4" />} Ya, proses sekarang</button>
                  <button type="button" onClick={() => setConfirm(false)} disabled={processing} className="rm-btn-ghost text-sm" data-testid="takedown-cancel-btn">Batal</button>
                </div>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
