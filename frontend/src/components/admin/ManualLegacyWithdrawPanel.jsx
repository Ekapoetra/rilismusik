import React, { useEffect, useRef, useState } from "react";
import { AlertCircle, Calculator, CheckCircle2, Loader2, Search } from "lucide-react";
import { api, formatApiError } from "@/api/client";

const fmtIDR = (value) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(value || 0);
const today = new Date().toISOString().slice(0, 10);
const EMPTY = { label_id: "", period_from: "", period_to: "", request_date: today, paid_date: today, note: "" };

export const ManualLegacyWithdrawPanel = ({ onComplete }) => {
  const [labels, setLabels] = useState([]);
  const [initialLabels, setInitialLabels] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [labelQuery, setLabelQuery] = useState("");
  const [labelPickerOpen, setLabelPickerOpen] = useState(false);
  const [labelSearchLoading, setLabelSearchLoading] = useState(false);
  const [preview, setPreview] = useState(null);
  const [job, setJob] = useState(null);
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState("");
  const pollRef = useRef(null);

  useEffect(() => {
    api.get("/admin/labels").then(({ data }) => {
      const sorted = (data || []).sort((a, b) => (a.label_name || "").localeCompare(b.label_name || ""));
      setLabels(sorted); setInitialLabels(sorted);
    }).catch((err) => setError(formatApiError(err.response?.data?.detail)));
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  useEffect(() => {
    if (!labelPickerOpen || form.label_id) return undefined;
    const query = labelQuery.trim();
    if (query.length < 2) { setLabels(initialLabels); setLabelSearchLoading(false); return undefined; }
    setLabelSearchLoading(true);
    const timer = setTimeout(async () => {
      try {
        const { data } = await api.get("/admin/labels", { params: { q: query } });
        setLabels((data || []).sort((a, b) => (a.label_name || "").localeCompare(b.label_name || "")));
      } catch (err) { setError(formatApiError(err.response?.data?.detail)); }
      finally { setLabelSearchLoading(false); }
    }, 300);
    return () => clearTimeout(timer);
  }, [labelQuery, labelPickerOpen, form.label_id, initialLabels]);

  const ready = form.label_id && form.period_from && form.period_to && form.request_date && form.paid_date;
  const filteredLabels = labels.filter((label) => (label.label_name || "").toLowerCase().includes(labelQuery.toLowerCase())).slice(0, 12);
  useEffect(() => {
    setPreview(null); setError("");
    if (!ready || busy) return undefined;
    const timer = setTimeout(async () => {
      try { const { data } = await api.post("/withdraw/admin/legacy-manual/preview", form); setPreview(data); }
      catch (err) { setError(formatApiError(err.response?.data?.detail)); }
    }, 350);
    return () => clearTimeout(timer);
  }, [form, ready, busy]);

  const pollJob = (jobId) => {
    if (pollRef.current) clearInterval(pollRef.current);
    const check = async () => {
      try {
        const { data } = await api.get(`/admin/migrate/jobs/${jobId}`);
        setJob(data);
        if (["done", "error"].includes(data.status)) {
          clearInterval(pollRef.current); pollRef.current = null; setBusy(false);
          if (data.status === "error") setError(data.error_message || "Proses background gagal");
          else { setForm(EMPTY); setLabelQuery(""); setPreview(null); await onComplete?.(); }
        }
      } catch (err) { clearInterval(pollRef.current); pollRef.current = null; setBusy(false); setError(formatApiError(err.response?.data?.detail)); }
    };
    pollRef.current = setInterval(check, 2500); check();
  };

  const submit = async () => {
    setConfirming(false); setBusy(true); setError("");
    try { const { data } = await api.post("/withdraw/admin/legacy-manual", form); setJob(data); pollJob(data.job_id); }
    catch (err) { setBusy(false); setError(formatApiError(err.response?.data?.detail)); }
  };

  return <div className="space-y-5" data-testid="admin-manual-legacy-withdraw-panel">
    <div className="rounded-lg border border-amber-500/30 bg-amber-500/[0.06] px-4 py-3 text-xs leading-relaxed text-amber-100">
      Nominal dihitung otomatis dari royalti aktif pada rentang bulan laporan. Saat disimpan, baris tersebut menjadi <b>legacy withdrawn</b>, cutoff label diperbarui, dan saldo dihitung ulang. Riwayat hanya terlihat oleh admin.
    </div>
    {error && <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300" data-testid="admin-manual-legacy-withdraw-error"><AlertCircle className="mr-2 inline h-4 w-4" />{error}</div>}
    <div className="grid gap-4 md:grid-cols-2">
      <Field label="Nama Label" wide><div className="relative"><Search className="pointer-events-none absolute left-3 top-1/2 z-10 h-4 w-4 -translate-y-1/2 text-zinc-500" /><input className="rm-input pl-10 pr-10" value={labelQuery} onFocus={() => setLabelPickerOpen(true)} onBlur={() => setTimeout(() => setLabelPickerOpen(false), 150)} onChange={(event) => { setLabelQuery(event.target.value); setForm({ ...form, label_id: "" }); setLabelPickerOpen(true); }} placeholder="Cari semua nama label…" role="combobox" aria-expanded={labelPickerOpen} aria-controls="manual-legacy-label-options" autoComplete="off" data-testid="admin-manual-legacy-label-select" required />{labelSearchLoading && <Loader2 className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-zinc-400" data-testid="admin-manual-legacy-label-searching" />}{labelPickerOpen && <div id="manual-legacy-label-options" role="listbox" className="absolute z-30 mt-1 max-h-64 w-full overflow-y-auto rounded-lg border border-white/10 bg-[#111016] p-1 shadow-2xl" data-testid="admin-manual-legacy-label-options">{filteredLabels.length ? filteredLabels.map((label) => <button key={label.id} type="button" role="option" aria-selected={form.label_id === label.id} className="w-full rounded-md px-3 py-2 text-left text-sm text-zinc-200 transition-colors hover:bg-white/10 focus:bg-white/10 focus:outline-none" onMouseDown={(event) => event.preventDefault()} onClick={() => { setForm({ ...form, label_id: label.id }); setLabelQuery(label.label_name); setLabelPickerOpen(false); }} data-testid={`admin-manual-legacy-label-option-${label.id}`}>{label.label_name}</button>) : <div className="px-3 py-3 text-sm text-zinc-500" data-testid="admin-manual-legacy-label-empty">Label tidak ditemukan.</div>}</div>}</div></Field>
      <Field label="Bulan Awal"><input type="month" className="rm-input" value={form.period_from} onChange={(event) => setForm({ ...form, period_from: event.target.value })} data-testid="admin-manual-legacy-period-from" required /></Field>
      <Field label="Bulan Pencairan Terbaru"><input type="month" className="rm-input" value={form.period_to} onChange={(event) => setForm({ ...form, period_to: event.target.value })} data-testid="admin-manual-legacy-period-to" required /></Field>
      <Field label="Tanggal Pengajuan"><input type="date" className="rm-input" value={form.request_date} onChange={(event) => setForm({ ...form, request_date: event.target.value })} data-testid="admin-manual-legacy-request-date" required /></Field>
      <Field label="Tanggal Pencairan"><input type="date" className="rm-input" value={form.paid_date} onChange={(event) => setForm({ ...form, paid_date: event.target.value })} data-testid="admin-manual-legacy-paid-date" required /></Field>
      <Field label="Catatan Admin" wide><textarea className="rm-input min-h-[80px]" value={form.note} onChange={(event) => setForm({ ...form, note: event.target.value })} data-testid="admin-manual-legacy-note" /></Field>
    </div>

    {ready && !preview && !error && <div className="flex items-center gap-2 text-sm text-zinc-400" data-testid="admin-manual-legacy-calculating"><Loader2 className="h-4 w-4 animate-spin" /> Menghitung nominal…</div>}
    {preview && <div className="grid gap-3 sm:grid-cols-3" data-testid="admin-manual-legacy-preview">
      <Stat label="Nominal Otomatis" value={fmtIDR(preview.amount_idr)} accent="text-emerald-300" testId="admin-manual-legacy-amount" />
      <Stat label="Baris Royalti" value={Number(preview.lines_count || 0).toLocaleString("id-ID")} accent="text-sky-300" testId="admin-manual-legacy-lines" />
      <Stat label="Cutoff Baru" value={preview.new_last_withdrawn_period} accent="text-amber-300" testId="admin-manual-legacy-cutoff" />
    </div>}
    <div className="flex justify-end"><button type="button" className="rm-btn-primary flex items-center gap-2" disabled={!preview || busy} onClick={() => setConfirming(true)} data-testid="admin-manual-legacy-submit"><Calculator className="h-4 w-4" /> {busy ? "Memproses…" : "Simpan Riwayat Legacy"}</button></div>

    {job && busy && <div className="rounded-lg border border-sky-500/30 bg-sky-500/10 px-4 py-3 text-sm text-sky-200" data-testid="admin-manual-legacy-job"><Loader2 className="mr-2 inline h-4 w-4 animate-spin" /> {job.progress_phase || job.status} — proses tetap berjalan di background.</div>}
    {job?.status === "done" && <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200" data-testid="admin-manual-legacy-complete"><CheckCircle2 className="mr-2 inline h-4 w-4" /> Riwayat tersimpan. {job.result?.royalty_lines_flipped?.toLocaleString("id-ID")} baris dipindahkan ke legacy withdrawn.</div>}

    {confirming && <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4" onClick={() => setConfirming(false)}><div className="rm-glass-strong w-full max-w-md rounded-[24px] border border-amber-500/30 p-6 space-y-4" onClick={(event) => event.stopPropagation()} data-testid="admin-manual-legacy-confirm-modal"><h3 className="font-display text-xl font-extrabold">Konfirmasi Riwayat Legacy</h3><p className="text-sm text-zinc-300">Tandai <b>{preview.lines_count.toLocaleString("id-ID")}</b> baris periode <b>{preview.period_from}–{preview.period_to}</b> sebagai legacy withdrawn senilai <b>{fmtIDR(preview.amount_idr)}</b>? Data ini tidak akan tampil pada akun label.</p><div className="flex justify-end gap-2"><button type="button" className="rm-btn-ghost" onClick={() => setConfirming(false)} data-testid="admin-manual-legacy-confirm-cancel">Batal</button><button type="button" className="rm-btn-primary" onClick={submit} data-testid="admin-manual-legacy-confirm-submit">Ya, Simpan</button></div></div></div>}
  </div>;
};

const Field = ({ label, wide, children }) => <div className={wide ? "md:col-span-2" : ""}><label className="rm-label">{label}</label>{children}</div>;
const Stat = ({ label, value, accent, testId }) => <div className="rounded-lg border border-white/10 bg-white/[0.025] p-4" data-testid={testId}><div className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">{label}</div><div className={`mt-1 font-display text-xl font-extrabold ${accent}`}>{value}</div></div>;