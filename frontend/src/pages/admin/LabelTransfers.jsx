import React, { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRightLeft, Check, X, RotateCcw, ExternalLink } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { toast } from "@/components/ui/sonner";
import { TRANSFER_STATUS, TransferPlanSummary } from "@/components/label/LabelTransferCard";

const TABS = [
  { key: "pending", label: "Menunggu" },
  { key: "failed", label: "Tertunda" },
  { key: "completed", label: "Selesai" },
  { key: "rejected", label: "Ditolak" },
  { key: "", label: "Semua" },
];
const MODES = [
  { key: "rename", label: "Ganti nama" },
  { key: "merge", label: "Gabung (akun sama)" },
  { key: "releases", label: "Pindah rilisan (akun sama)" },
  { key: "sale", label: "Penjualan ke akun lain" },
];

export default function AdminLabelTransfers() {
  const { hasPermission } = useAuth();
  const [params] = useSearchParams();
  const [tab, setTab] = useState("pending");
  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [formOpen, setFormOpen] = useState(Boolean(params.get("source")));
  const load = useCallback(async () => {
    setErr("");
    try { const { data } = await api.get("/admin/label-transfers", { params: tab ? { status: tab } : {} }); setRows(data || []); }
    catch (error) { setErr(formatApiError(error.response?.data?.detail)); }
  }, [tab]);
  useEffect(() => { load(); }, [load]);

  const act = async (row, action) => {
    let payload = { action };
    if (action === "approve") {
      if (!window.confirm(`Pastikan perpindahan ini SUDAH berhasil di Believe.\n\n${row.summary}\n\nSetujui dan terapkan sekarang?`)) return;
      payload = { action, believe_confirmed: true };
    } else {
      const note = window.prompt("Alasan penolakan (opsional):");
      if (note === null) return;
      payload = { action, note };
    }
    setBusy(true); setErr("");
    try {
      await api.post(`/admin/label-transfers/${row.id}/decision`, payload);
      toast.success(action === "approve" ? "Perpindahan diterapkan." : "Pengajuan ditolak.");
      await load();
    } catch (error) { setErr(formatApiError(error.response?.data?.detail)); await load(); }
    finally { setBusy(false); }
  };
  const resume = async (row) => {
    setBusy(true); setErr("");
    try { await api.post(`/admin/label-transfers/${row.id}/resume`); toast.success("Perpindahan dilanjutkan dan selesai."); await load(); }
    catch (error) { setErr(formatApiError(error.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-6" data-testid="admin-label-transfers">
      <header className="flex flex-wrap items-end justify-between gap-3 border-b border-white/10 pb-5">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Manajemen Label</div>
          <h1 className="mt-1 flex items-center gap-2 font-display text-3xl font-extrabold"><ArrowRightLeft className="h-6 w-6 text-pink-400" /> Pindah Label</h1>
          <p className="mt-2 max-w-2xl text-sm text-zinc-400">Ganti nama, gabung, atau pindahkan rilisan antar label mengikuti perpindahan di Believe. Saldo yang belum ditarik ikut pindah; nama lama tetap dikenali saat impor royalti.</p>
        </div>
        {hasPermission("labels.manage") && <button type="button" className="rm-btn-primary" onClick={() => setFormOpen((value) => !value)} data-testid="label-transfer-new">{formOpen ? "Tutup Form" : "+ Input Perpindahan"}</button>}
      </header>

      {formOpen && <TransferForm initialSource={params.get("source") ? { id: params.get("source"), label_name: params.get("name") || params.get("source") } : null} onDone={() => { setFormOpen(false); setTab("pending"); load(); }} />}

      <div className="flex flex-wrap gap-2">
        {TABS.map((item) => <button key={item.key} type="button" onClick={() => setTab(item.key)} className={`rounded-full px-4 py-1.5 text-sm font-bold ${tab === item.key ? "bg-white text-black" : "border border-white/10 text-zinc-400 hover:text-white"}`}>{item.label}</button>)}
      </div>
      {err && <div className="rounded-md bg-red-500/15 px-4 py-3 text-sm text-red-300" role="alert">{err}</div>}
      {rows.length === 0 ? <div className="rounded-md border border-white/10 py-16 text-center text-sm text-zinc-500">Tidak ada perpindahan.</div> : (
        <div className="space-y-3">
          {rows.map((row) => <TransferRow key={row.id} row={row} busy={busy} onAct={act} onResume={resume} />)}
        </div>
      )}
    </div>
  );
}

function TransferRow({ row, busy, onAct, onResume }) {
  const badge = TRANSFER_STATUS[row.status] || TRANSFER_STATUS.pending;
  const canResume = ["failed", "applying", "approved"].includes(row.status);
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.02] p-4" data-testid={`label-transfer-row-${row.id}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rm-badge bg-white/10 text-[10px] text-zinc-300">{MODES.find((item) => item.key === row.mode)?.label || row.mode}</span>
          <span className="font-mono text-xs text-zinc-500">{row.reference_id}</span>
          <span className={`rm-badge ${badge.cls}`}>{badge.label}</span>
        </div>
        <div className="flex gap-3 text-xs">
          <Link to={`/admin/labels/${row.source_label_id}`} className="inline-flex items-center gap-1 text-sky-300">{row.source_label_name} <ExternalLink className="h-3 w-3" /></Link>
          {row.target_label_id && <Link to={`/admin/labels/${row.target_label_id}`} className="inline-flex items-center gap-1 text-sky-300">{row.target_label_name} <ExternalLink className="h-3 w-3" /></Link>}
        </div>
      </div>
      <div className="mt-2 text-lg font-bold">{row.summary}</div>
      <div className="mt-1 text-sm text-zinc-400">Alasan: {row.reason || "—"}{row.reference ? ` · Rujukan: ${row.reference}` : ""}{row.effective_period ? ` · Berlaku laporan ${row.effective_period}` : ""}{row.mode === "sale" ? ` · Saldo sebelum efektif ${row.carry_balance ? "ikut pindah" : "tetap di penjual"}` : ""}</div>
      <div className="mt-1 text-[11px] text-zinc-500">Diajukan oleh {row.requested_by_name} ({row.requested_by_kind === "label" ? "pelanggan" : "admin"}) · {(row.requested_at || "").slice(0, 10)}{row.decided_by_name ? ` · Diputuskan oleh ${row.decided_by_name}` : ""}{row.decision_note ? ` · ${row.decision_note}` : ""}</div>
      {row.plan && <div className="mt-3"><TransferPlanSummary plan={row.plan} /></div>}
      {row.result && <div className="mt-2 text-[11px] text-zinc-500">Dipindah: {row.result.releases ?? 0} rilisan, {row.result.tracks ?? 0} lagu, {row.result.lines ?? 0} baris royalti, {row.result.artists ?? 0} artis.</div>}
      {row.error && <div className="mt-2 rounded-md bg-red-500/10 px-3 py-2 text-xs text-red-300">{row.error}</div>}
      <div className="mt-3 flex flex-wrap gap-2">
        {row.status === "pending" && row.can_decide && <>
          <button type="button" disabled={busy} onClick={() => onAct(row, "approve")} className="inline-flex items-center gap-1 rounded-md border border-emerald-400/30 px-4 py-2 text-xs font-bold text-emerald-300 hover:bg-emerald-500/10 disabled:opacity-50" data-testid={`label-transfer-approve-${row.id}`}><Check className="h-4 w-4" /> Setujui & Terapkan</button>
          <button type="button" disabled={busy} onClick={() => onAct(row, "reject")} className="inline-flex items-center gap-1 rounded-md border border-red-400/30 px-4 py-2 text-xs font-bold text-red-300 hover:bg-red-500/10 disabled:opacity-50"><X className="h-4 w-4" /> Tolak</button>
        </>}
        {row.status === "pending" && !row.can_decide && <span className="text-xs text-zinc-500">{row.mode === "sale" ? "Menunggu persetujuan Super Admin lain." : "Menunggu persetujuan admin lain."}</span>}
        {canResume && <button type="button" disabled={busy} onClick={() => onResume(row)} className="inline-flex items-center gap-1 rounded-md border border-sky-400/30 px-4 py-2 text-xs font-bold text-sky-300 hover:bg-sky-500/10 disabled:opacity-50"><RotateCcw className="h-4 w-4" /> Lanjutkan</button>}
      </div>
    </div>
  );
}

function LabelPicker({ label, value, onChange, testId }) {
  const [q, setQ] = useState("");
  const [options, setOptions] = useState([]);
  useEffect(() => {
    if (value) return undefined;
    const timer = setTimeout(() => {
      api.get("/admin/label-transfers/labels", { params: { q } }).then((r) => setOptions(r.data || [])).catch(() => setOptions([]));
    }, 250);
    return () => clearTimeout(timer);
  }, [q, value]);
  if (value) {
    return <div><label className="rm-label">{label}</label><div className="flex items-center justify-between rounded-lg border border-white/10 px-3 py-2 text-sm"><span className="font-semibold">{value.label_name}</span><button type="button" className="text-xs text-zinc-400 hover:text-white" onClick={() => onChange(null)}>Ganti</button></div></div>;
  }
  return (
    <div><label className="rm-label">{label}</label>
      <input className="rm-input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cari nama label…" data-testid={testId} />
      <div className="mt-1 max-h-40 overflow-y-auto rounded-lg border border-white/10">
        {options.map((item) => <button type="button" key={item.id} onClick={() => onChange(item)} className="flex w-full justify-between px-3 py-1.5 text-left text-sm hover:bg-white/5"><span>{item.label_name}</span><span className="text-xs text-zinc-500">{item.email || (item.user_id ? "" : "belum diklaim")}</span></button>)}
      </div>
    </div>
  );
}

function TransferForm({ initialSource, onDone }) {
  const [source, setSource] = useState(initialSource);
  const [target, setTarget] = useState(null);
  const [mode, setMode] = useState("rename");
  const [newName, setNewName] = useState("");
  const [releases, setReleases] = useState([]);
  const [selected, setSelected] = useState([]);
  const [effective, setEffective] = useState("");
  const [carry, setCarry] = useState(false);
  const [reference, setReference] = useState("");
  const [reason, setReason] = useState("");
  const [believe, setBelieve] = useState(false);
  const [applyNow, setApplyNow] = useState(false);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const pickRelease = mode === "releases" || mode === "sale";
  useEffect(() => {
    setReleases([]); setSelected([]);
    if (source && pickRelease) api.get(`/admin/label-transfers/labels/${source.id}/releases`).then((r) => setReleases(r.data || [])).catch(() => {});
  }, [source, pickRelease]);
  useEffect(() => { setPreview(null); }, [source, target, mode, newName, selected, effective, carry, reference, reason]);
  const body = () => ({
    mode, source_label_id: source?.id, target_label_id: mode === "rename" ? null : target?.id, new_name: mode === "rename" ? newName : null,
    release_ids: pickRelease ? selected : [], effective_period: effective || null, carry_balance: mode === "sale" ? carry : true,
    reference: reference || null, reason, believe_confirmed: believe, apply_now: applyNow,
  });
  const run = async (path, onOk) => {
    setBusy(true); setErr("");
    try { const { data } = await api.post(path, body()); onOk(data); }
    catch (error) { setErr(formatApiError(error.response?.data?.detail)); }
    finally { setBusy(false); }
  };
  const submit = (event) => {
    event.preventDefault();
    run("/admin/label-transfers", (data) => { toast.success(data.status === "completed" ? "Perpindahan diterapkan." : "Pengajuan dibuat, menunggu persetujuan."); onDone(); });
  };
  const toggle = (id) => setSelected((list) => (list.includes(id) ? list.filter((item) => item !== id) : [...list, id]));
  return (
    <form onSubmit={submit} className="rm-card space-y-4 p-5" data-testid="label-transfer-form">
      <div className="flex flex-wrap gap-2">
        {MODES.map((item) => <button type="button" key={item.key} onClick={() => setMode(item.key)} className={`rounded-full px-3 py-1.5 text-xs font-bold ${mode === item.key ? "bg-pink-500 text-white" : "border border-white/10 text-zinc-400"}`} data-testid={`label-transfer-form-mode-${item.key}`}>{item.label}</button>)}
      </div>
      {mode === "sale" && <div className="rounded-lg border border-amber-400/30 bg-amber-400/[0.06] px-3 py-2 text-xs text-amber-200">Penjualan memindahkan katalog ke akun lain. Wajib rujukan dokumen, dan hanya bisa diterapkan setelah disetujui Super Admin selain Anda. Kedua pemilik akun mendapat notifikasi.</div>}
      <div className="grid gap-4 md:grid-cols-2">
        <LabelPicker label="Label asal" value={source} onChange={setSource} testId="label-transfer-source-search" />
        {mode === "rename"
          ? <div><label className="rm-label">Nama baru</label><input className="rm-input" value={newName} onChange={(e) => setNewName(e.target.value)} required placeholder="Sesuai nama di Believe" /></div>
          : <LabelPicker label={mode === "sale" ? "Label pembeli" : "Label tujuan (akun yang sama)"} value={target} onChange={setTarget} testId="label-transfer-target-search" />}
      </div>
      {pickRelease && source && (
        <div><label className="rm-label">{mode === "sale" ? `Rilisan yang dijual (${selected.length || "semua"})` : `Rilisan yang dipindah (${selected.length})`}</label>
          <div className="max-h-56 space-y-1 overflow-y-auto rounded-lg border border-white/10 p-2">
            {releases.length === 0 ? <div className="text-xs text-zinc-500">Tidak ada rilisan.</div> : releases.map((item) => (
              <label key={item.id} className="flex cursor-pointer items-center gap-2 text-sm"><input type="checkbox" checked={selected.includes(item.id)} onChange={() => toggle(item.id)} /><span className="truncate">{item.release_title}</span><span className="text-xs text-zinc-500">{item.upc || ""} · {item.status}</span></label>
            ))}
          </div>
          {mode === "sale" && <p className="mt-1 text-[11px] text-zinc-500">Kosongkan pilihan untuk menjual semua rilisan label asal.</p>}
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-3">
        <div><label className="rm-label">Berlaku mulai laporan{mode === "sale" ? "" : " (opsional)"}</label><input type="month" className="rm-input" value={effective} onChange={(e) => setEffective(e.target.value)} required={mode === "sale"} /></div>
        <div><label className="rm-label">Rujukan{mode === "sale" ? " dokumen jual-beli" : " (tiket/Believe)"}</label><input className="rm-input" value={reference} onChange={(e) => setReference(e.target.value)} required={mode === "sale"} /></div>
        <div><label className="rm-label">Alasan</label><input className="rm-input" value={reason} onChange={(e) => setReason(e.target.value)} minLength={3} required /></div>
      </div>
      {mode === "sale" && <label className="flex items-center gap-2 text-sm text-zinc-300"><input type="checkbox" checked={carry} onChange={(e) => setCarry(e.target.checked)} /> Saldo penjual sebelum bulan efektif ikut pindah ke pembeli</label>}
      <label className="flex items-center gap-2 text-sm text-zinc-300"><input type="checkbox" checked={believe} onChange={(e) => setBelieve(e.target.checked)} data-testid="label-transfer-believe" /> Perpindahan di Believe sudah berhasil</label>
      {preview?.can_apply_directly && <label className="flex items-center gap-2 text-sm text-zinc-300"><input type="checkbox" checked={applyNow} onChange={(e) => setApplyNow(e.target.checked)} data-testid="label-transfer-apply-now" /> Terapkan langsung tanpa persetujuan</label>}
      {preview && <div className="space-y-2 rounded-lg border border-white/10 bg-white/[0.03] p-3"><div className="text-sm font-semibold">{preview.summary}</div><TransferPlanSummary plan={preview.plan} />{preview.plan?.credit_idr > 0 && <div className="text-[11px] text-zinc-500">Termasuk {`Rp ${Number(preview.plan.credit_idr).toLocaleString("id-ID")}`} dari periode yang sudah ditarik label tujuan, dikreditkan lewat jurnal penyesuaian.</div>}</div>}
      {err && <div className="rounded-lg bg-red-500/15 px-3 py-2 text-sm text-red-300" role="alert">{err}</div>}
      <div className="flex justify-end gap-2">
        <button type="button" className="rm-btn-ghost" disabled={busy || !source} onClick={() => run("/admin/label-transfers/preview", setPreview)} data-testid="label-transfer-form-preview">Pratinjau</button>
        <button className="rm-btn-primary" disabled={busy || !preview || (applyNow && !believe)} data-testid="label-transfer-form-submit">{applyNow ? "Terapkan Sekarang" : "Buat Pengajuan"}</button>
      </div>
    </form>
  );
}
