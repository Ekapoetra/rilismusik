import React, { useCallback, useEffect, useState } from "react";
import { ArrowRightLeft } from "lucide-react";
import { api, formatApiError } from "@/api/client";

const fmtIDR = (value) => `Rp ${Number(value || 0).toLocaleString("id-ID")}`;

export const TRANSFER_STATUS = {
  pending: { label: "Menunggu persetujuan", cls: "bg-amber-500/15 text-amber-300" },
  approved: { label: "Disetujui, sedang diproses", cls: "bg-sky-500/15 text-sky-300" },
  applying: { label: "Sedang diproses", cls: "bg-sky-500/15 text-sky-300" },
  failed: { label: "Tertunda — ditangani admin", cls: "bg-red-500/15 text-red-300" },
  completed: { label: "Selesai", cls: "bg-emerald-500/15 text-emerald-300" },
  rejected: { label: "Ditolak", cls: "bg-red-500/15 text-red-300" },
  cancelled: { label: "Dibatalkan", cls: "bg-white/10 text-zinc-400" },
};

const MODES = [
  { key: "rename", label: "Ganti nama label", hint: "Nama label diganti. Rilisan, saldo, dan rekening tetap di label ini." },
  { key: "merge", label: "Gabung ke label lain di akun ini", hint: "Semua rilisan dan saldo yang belum ditarik pindah ke label tujuan." },
  { key: "releases", label: "Pindahkan rilisan tertentu", hint: "Hanya rilisan yang dipilih (beserta royaltinya yang belum ditarik) yang pindah." },
];

export function TransferPlanSummary({ plan }) {
  if (!plan || plan.mode === "rename") return null;
  const moved = (plan.available_idr || 0) + (plan.adjustment_idr || 0);
  return (
    <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4" data-testid="label-transfer-plan">
      <div><div className="text-zinc-500">Rilisan</div><div className="font-semibold">{plan.release_count}</div></div>
      <div><div className="text-zinc-500">Saldo tersedia pindah</div><div className="font-semibold">{fmtIDR(moved)}</div></div>
      <div><div className="text-zinc-500">Saldo tertunda pindah</div><div className="font-semibold">{fmtIDR(plan.pending_idr)}</div></div>
      <div><div className="text-zinc-500">Baris royalti</div><div className="font-semibold">{(plan.line_count || 0).toLocaleString("id-ID")}</div></div>
    </div>
  );
}

export function LabelTransferCard({ label }) {
  const [items, setItems] = useState([]);
  const [labels, setLabels] = useState([]);
  const [open, setOpen] = useState(false);
  const load = useCallback(async () => {
    try {
      const [list, options] = await Promise.all([api.get("/label/transfers"), api.get("/label/transfers/options")]);
      setItems(list.data || []); setLabels(options.data?.labels || []);
    } catch { /* non-fatal on the dashboard */ }
  }, []);
  useEffect(() => { load(); }, [load]);
  const current = labels.find((item) => item.id === label?.id);
  const cancel = async (item) => {
    if (!window.confirm("Batalkan pengajuan ini?")) return;
    try { await api.post(`/label/transfers/${item.id}/cancel`); await load(); } catch (error) { window.alert(formatApiError(error.response?.data?.detail)); }
  };
  if (!label) return null;
  return (
    <section className="rm-card p-5 space-y-3" data-testid="label-transfer-card">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-2 font-display text-lg font-bold tracking-tight"><ArrowRightLeft className="h-4 w-4 text-pink-400" /> Pindah / Ganti Nama Label</h3>
          <p className="mt-1 text-sm text-zinc-400">Sudah memindahkan atau mengganti nama label di distributor? Ajukan di sini agar data Rilis Musik ikut menyatu.</p>
          {current?.former_names?.length > 0 && <p className="mt-1 text-xs text-zinc-500">Nama sebelumnya: {current.former_names.join(", ")}</p>}
        </div>
        {!current?.merged_into_label_name && <button type="button" className="rm-btn-ghost text-sm" onClick={() => setOpen(true)} data-testid="label-transfer-open">Ajukan</button>}
      </div>
      {current?.merged_into_label_name && <div className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-zinc-300">Label ini sudah digabung ke <b>{current.merged_into_label_name}</b>.</div>}
      {items.slice(0, 5).map((item) => {
        const badge = TRANSFER_STATUS[item.status] || TRANSFER_STATUS.pending;
        return (
          <div key={item.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm" data-testid={`label-transfer-${item.id}`}>
            <div className="min-w-0"><div className="font-semibold">{item.summary}</div><div className="text-[11px] text-zinc-500">{item.reference_id} · {(item.requested_at || "").slice(0, 10)}{item.decision_note ? ` · ${item.decision_note}` : ""}</div></div>
            <div className="flex items-center gap-2"><span className={`rm-badge ${badge.cls}`}>{badge.label}</span>{item.status === "pending" && item.requested_by_kind === "label" && <button type="button" className="text-xs text-zinc-400 hover:text-white" onClick={() => cancel(item)}>Batalkan</button>}</div>
          </div>
        );
      })}
      {open && <LabelTransferModal label={label} labels={labels} close={() => setOpen(false)} done={() => { setOpen(false); load(); }} />}
    </section>
  );
}

function LabelTransferModal({ label, labels, close, done }) {
  const targets = labels.filter((item) => item.id !== label.id && !item.merged_into_label_name);
  const [mode, setMode] = useState("rename");
  const [newName, setNewName] = useState("");
  const [targetId, setTargetId] = useState(targets[0]?.id || "");
  const [releases, setReleases] = useState([]);
  const [selected, setSelected] = useState([]);
  const [reason, setReason] = useState("");
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => {
    if (mode !== "releases" || releases.length) return;
    api.get("/label/transfers/releases", { params: { label_id: label.id } }).then((r) => setReleases(r.data || [])).catch(() => {});
  }, [mode, label.id, releases.length]);
  useEffect(() => { setPreview(null); }, [mode, newName, targetId, selected, reason]);
  const body = () => ({ mode, source_label_id: label.id, new_name: mode === "rename" ? newName : null, target_label_id: mode === "rename" ? null : targetId, release_ids: mode === "releases" ? selected : [], reason });
  const run = async (path, onOk) => {
    setBusy(true); setErr("");
    try { const { data } = await api.post(path, body()); onOk(data); }
    catch (error) { setErr(formatApiError(error.response?.data?.detail)); }
    finally { setBusy(false); }
  };
  const toggle = (id) => setSelected((list) => (list.includes(id) ? list.filter((item) => item !== id) : [...list, id]));
  const needsTarget = mode !== "rename";
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={close}>
      <form onClick={(e) => e.stopPropagation()} onSubmit={(e) => { e.preventDefault(); run("/label/transfers", done); }} className="max-h-[90vh] w-full max-w-lg space-y-4 overflow-y-auto rounded-[24px] border border-white/10 rm-glass-strong p-6" data-testid="label-transfer-modal">
        <h3 className="font-display text-xl font-extrabold">Ajukan Pindah / Ganti Nama Label</h3>
        <p className="text-sm text-zinc-400">Label asal: <b>{label.label_name}</b>. Pengajuan diperiksa admin setelah perpindahan di distributor berhasil.</p>
        <div className="space-y-2">
          {MODES.map((item) => {
            const disabled = item.key !== "rename" && targets.length === 0;
            return (
              <label key={item.key} className={`flex gap-3 rounded-lg border p-3 text-sm ${mode === item.key ? "border-pink-400/50 bg-pink-500/5" : "border-white/10"} ${disabled ? "opacity-50" : "cursor-pointer"}`}>
                <input type="radio" name="mode" checked={mode === item.key} disabled={disabled} onChange={() => setMode(item.key)} data-testid={`label-transfer-mode-${item.key}`} />
                <span><span className="font-semibold">{item.label}</span><span className="block text-xs text-zinc-400">{disabled ? "Butuh label lain di akun ini (paket Multi Label)." : item.hint}</span></span>
              </label>
            );
          })}
        </div>
        {mode === "rename" && <div><label className="rm-label">Nama label baru</label><input className="rm-input" value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Sesuai nama di distributor" required data-testid="label-transfer-new-name" /></div>}
        {needsTarget && <div><label className="rm-label">Label tujuan</label><select className="rm-input" value={targetId} onChange={(e) => setTargetId(e.target.value)} data-testid="label-transfer-target">{targets.map((item) => <option key={item.id} value={item.id}>{item.label_name}</option>)}</select></div>}
        {mode === "releases" && (
          <div><label className="rm-label">Rilisan yang dipindah ({selected.length})</label>
            <div className="max-h-48 space-y-1 overflow-y-auto rounded-lg border border-white/10 p-2">
              {releases.length === 0 ? <div className="text-xs text-zinc-500">Memuat rilisan…</div> : releases.map((item) => (
                <label key={item.id} className="flex cursor-pointer items-center gap-2 text-sm"><input type="checkbox" checked={selected.includes(item.id)} onChange={() => toggle(item.id)} /><span className="truncate">{item.release_title}</span><span className="text-xs text-zinc-500">{item.upc || ""}</span></label>
              ))}
            </div>
          </div>
        )}
        <div><label className="rm-label">Alasan</label><input className="rm-input" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Contoh: label sudah dipindah di Believe" minLength={3} required data-testid="label-transfer-reason" /></div>
        {preview && <div className="space-y-2 rounded-lg border border-white/10 bg-white/[0.03] p-3"><div className="text-sm font-semibold">{preview.summary}</div><TransferPlanSummary plan={preview.plan} /></div>}
        {err && <div className="rounded-lg bg-red-500/15 px-3 py-2 text-sm text-red-300" role="alert">{err}</div>}
        <div className="flex justify-end gap-2">
          <button type="button" className="rm-btn-ghost" onClick={close}>Batal</button>
          <button type="button" className="rm-btn-ghost" disabled={busy} onClick={() => run("/label/transfers/preview", setPreview)} data-testid="label-transfer-preview">Pratinjau</button>
          <button className="rm-btn-primary" disabled={busy || !preview} data-testid="label-transfer-submit">Ajukan</button>
        </div>
      </form>
    </div>
  );
}
