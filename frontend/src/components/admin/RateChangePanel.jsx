import React, { useCallback, useEffect, useState } from "react";
import { Percent, ShieldCheck, Clock, Check, X } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

const STATUS_BADGE = {
  pending: { label: "Menunggu Persetujuan", cls: "bg-amber-500/15 text-amber-300" },
  approved: { label: "Disetujui", cls: "bg-emerald-500/15 text-emerald-300" },
  rejected: { label: "Ditolak", cls: "bg-red-500/15 text-red-300" },
};

function RequestRow({ req, canApprove, onDecide, busy }) {
  const badge = STATUS_BADGE[req.status] || STATUS_BADGE.pending;
  return (
    <div className="rounded-md border border-white/10 bg-white/[0.02] p-3 text-sm" data-testid={`rate-request-${req.id}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-mono text-xs text-zinc-500">{req.reference_id}</span>
        <span className={`rm-badge ${badge.cls}`} data-testid={`rate-request-status-${req.id}`}>{badge.label}</span>
      </div>
      <div className="mt-1 font-semibold">{req.current_value}% → {req.proposed_value}%</div>
      <div className="mt-1 text-xs text-zinc-400">Alasan: {req.reason}</div>
      <div className="mt-1 text-[11px] text-zinc-500">Diajukan oleh {req.requested_by_name} · {(req.requested_at || "").slice(0, 10)}</div>
      {req.decided_by_name && <div className="text-[11px] text-zinc-500">Diputuskan oleh {req.decided_by_name} · {(req.decided_at || "").slice(0, 10)}{req.decision_note ? ` · ${req.decision_note}` : ""}</div>}
      {canApprove && req.status === "pending" && (
        <div className="mt-2 flex gap-2">
          <button type="button" className="inline-flex items-center gap-1 rounded-md border border-emerald-400/30 px-3 py-1.5 text-xs font-bold text-emerald-300 hover:bg-emerald-500/10 disabled:opacity-50" disabled={busy} onClick={() => onDecide(req, "approve")} data-testid={`rate-request-approve-${req.id}`}><Check className="h-3.5 w-3.5" /> Setujui</button>
          <button type="button" className="inline-flex items-center gap-1 rounded-md border border-red-400/30 px-3 py-1.5 text-xs font-bold text-red-300 hover:bg-red-500/10 disabled:opacity-50" disabled={busy} onClick={() => onDecide(req, "reject")} data-testid={`rate-request-reject-${req.id}`}><X className="h-3.5 w-3.5" /> Tolak</button>
        </div>
      )}
    </div>
  );
}

export function RateChangePanel({ labelId, label, perms, onChanged }) {
  const [requests, setRequests] = useState([]);
  const [value, setValue] = useState(String(label.royalty_percentage_default ?? 60));
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [recalc, setRecalc] = useState(null);
  const [err, setErr] = useState("");

  const canList = perms.view || perms.request || perms.approve;
  const load = useCallback(async () => {
    if (!canList) return;
    try { const { data } = await api.get(`/admin/rate-changes`, { params: { label_id: labelId } }); setRequests(data || []); }
    catch (e) { /* non-fatal */ }
  }, [labelId, canList]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { setValue(String(label.royalty_percentage_default ?? 60)); }, [label.royalty_percentage_default]);

  const pollRecalc = async (jobId) => {
    if (!jobId) return;
    for (let i = 0; i < 180; i += 1) {
      await wait(2000);
      const { data } = await api.get(`/admin/migrate/jobs/${jobId}`);
      setRecalc(data);
      if (data.status === "done" || data.status === "error") break;
    }
  };

  const submitDirect = async () => {
    setErr(""); setBusy(true);
    try {
      if (!reason.trim()) { setErr("Alasan wajib diisi."); return; }
      const { data } = await api.post(`/admin/labels/${labelId}/rate-change/direct`, { proposed_value: Number(value), reason });
      toast.success("Rate/fee diubah langsung.");
      setReason(""); onChanged && onChanged();
      pollRecalc(data.royalty_recalculation_job_id);
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const submitRequest = async () => {
    setErr(""); setBusy(true);
    try {
      if (!reason.trim()) { setErr("Alasan wajib diisi."); return; }
      await api.post(`/admin/labels/${labelId}/rate-change/request`, { proposed_value: Number(value), reason });
      toast.success("Permintaan perubahan rate/fee dikirim untuk persetujuan Super Admin.");
      setReason(""); await load();
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const decide = async (req, action) => {
    let note = "";
    if (action === "reject") { note = window.prompt("Alasan penolakan (opsional):") ?? ""; }
    setBusy(true); setErr("");
    try {
      const { data } = await api.post(`/admin/rate-changes/${req.id}/decision`, { action, note });
      toast.success(action === "approve" ? "Permintaan disetujui & diterapkan." : "Permintaan ditolak.");
      await load(); onChanged && onChanged();
      if (action === "approve") pollRecalc(data.royalty_recalculation_job_id);
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  if (!perms.direct && !perms.request && !canList) return null;

  return (
    <div className="rm-card p-5 space-y-4" data-testid="admin-rate-change-panel">
      <div className="flex items-center gap-2">
        <Percent className="h-4 w-4 text-pink-400" />
        <h3 className="font-display font-bold tracking-tight text-lg">Rate / Fee Royalti</h3>
        {perms.direct ? <span className="rm-badge bg-red-500/15 text-red-300 text-[10px]">Ubah Langsung</span> : perms.request ? <span className="rm-badge bg-amber-500/15 text-amber-300 text-[10px]">Perlu Persetujuan</span> : null}
      </div>
      <div className="text-sm text-zinc-400">Nilai aktif: <span className="font-bold text-zinc-100">{label.royalty_percentage_default}%</span></div>

      {(perms.direct || perms.request) && (
        <div className="space-y-3 border-t border-white/5 pt-3">
          <div><label className="rm-label">Bagian Royalti Label (%)</label><input className="rm-input" type="number" min="0" max="100" value={value} onChange={(e) => setValue(e.target.value)} data-testid="admin-rate-value-input" /></div>
          <div><label className="rm-label">Alasan Perubahan</label><input className="rm-input" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Misal: review tahunan" data-testid="admin-rate-reason-input" /></div>
          {perms.direct ? (
            <button className="rm-btn-primary text-sm inline-flex items-center gap-2" onClick={submitDirect} disabled={busy} data-testid="admin-rate-direct-save"><ShieldCheck className="h-4 w-4" />{busy ? "Memproses…" : "Ubah Langsung"}</button>
          ) : (
            <button className="rm-btn-primary text-sm inline-flex items-center gap-2" onClick={submitRequest} disabled={busy} data-testid="admin-rate-request-submit"><Clock className="h-4 w-4" />{busy ? "Mengirim…" : "Ajukan Perubahan"}</button>
          )}
          <p className="text-[11px] text-zinc-500">{perms.direct ? "Perubahan langsung diterapkan dan dihitung ulang. Setiap perubahan diaudit." : "Nilai live tidak berubah sampai Super Admin menyetujui permintaan."}</p>
        </div>
      )}

      {recalc && <div className="text-xs text-sky-300" data-testid="admin-rate-recalc-status">Hitung ulang: {recalc.status} • {(recalc.progress_lines_done || 0).toLocaleString("id-ID")}/{(recalc.progress_lines_total || 0).toLocaleString("id-ID")} baris</div>}
      {err && <div className="rounded-md bg-red-500/15 text-red-300 px-3 py-2 text-sm" data-testid="admin-rate-error">{err}</div>}

      {canList && (
        <div className="space-y-2 border-t border-white/5 pt-3" data-testid="admin-rate-request-list">
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Riwayat Permintaan</div>
          {requests.length === 0 ? <div className="text-sm text-zinc-500">Belum ada permintaan.</div> : requests.map((req) => <RequestRow key={req.id} req={req} canApprove={perms.approve} onDecide={decide} busy={busy} />)}
        </div>
      )}
    </div>
  );
}
