import React, { useCallback, useEffect, useState } from "react";
import { ShieldAlert, Check, X } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";

const STATUS = {
  pending: { label: "Menunggu Persetujuan", cls: "bg-amber-500/15 text-amber-300" },
  approved: { label: "Disetujui", cls: "bg-emerald-500/15 text-emerald-300" },
  rejected: { label: "Ditolak", cls: "bg-red-500/15 text-red-300" },
};
const TYPE_LABEL = { blacklist: "Blacklist", package: "Paket" };

// Shows blacklist + package sensitive requests for one label, with approve/reject for approvers.
export function SensitiveRequestsPanel({ labelId, canView, canApprove, onChanged, refreshKey }) {
  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    if (!canView) return;
    try { const { data } = await api.get("/admin/sensitive-requests", { params: { label_id: labelId } }); setRows(data || []); }
    catch (e) { /* non-fatal */ }
  }, [labelId, canView]);
  useEffect(() => { load(); }, [load, refreshKey]);

  const decide = async (req, action) => {
    let note = "";
    if (action === "reject") note = window.prompt("Alasan penolakan (opsional):") ?? "";
    setBusy(true);
    try {
      await api.post(`/admin/sensitive-requests/${req.id}/decision`, { action, note });
      toast.success(action === "approve" ? "Permintaan disetujui & diterapkan." : "Permintaan ditolak.");
      await load(); onChanged && onChanged();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  if (!canView) return null;
  return (
    <div className="rm-card p-5 space-y-3" data-testid="admin-sensitive-requests-panel">
      <div className="flex items-center gap-2"><ShieldAlert className="h-4 w-4 text-amber-400" /><h3 className="font-display font-bold tracking-tight text-lg">Permintaan Aksi Sensitif</h3></div>
      {rows.length === 0 ? <div className="text-sm text-zinc-500">Belum ada permintaan.</div> : rows.map((req) => {
        const badge = STATUS[req.status] || STATUS.pending;
        return (
          <div key={req.id} className="rounded-md border border-white/10 bg-white/[0.02] p-3 text-sm" data-testid={`sensitive-request-${req.id}`}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="flex items-center gap-2"><span className="rm-badge bg-white/10 text-zinc-300 text-[10px]">{TYPE_LABEL[req.action_type] || req.action_type}</span><span className="font-mono text-xs text-zinc-500">{req.reference_id}</span></span>
              <span className={`rm-badge ${badge.cls}`} data-testid={`sensitive-request-status-${req.id}`}>{badge.label}</span>
            </div>
            <div className="mt-1 font-semibold">{req.summary}</div>
            {req.reason && <div className="mt-1 text-xs text-zinc-400">Alasan: {req.reason}</div>}
            <div className="mt-1 text-[11px] text-zinc-500">Diajukan oleh {req.requested_by_name} · {(req.requested_at || "").slice(0, 10)}{req.decided_by_name ? ` · Diputuskan oleh ${req.decided_by_name}` : ""}</div>
            {canApprove && req.status === "pending" && (
              <div className="mt-2 flex gap-2">
                <button type="button" disabled={busy} onClick={() => decide(req, "approve")} className="inline-flex items-center gap-1 rounded-md border border-emerald-400/30 px-3 py-1.5 text-xs font-bold text-emerald-300 hover:bg-emerald-500/10 disabled:opacity-50" data-testid={`sensitive-request-approve-${req.id}`}><Check className="h-3.5 w-3.5" /> Setujui</button>
                <button type="button" disabled={busy} onClick={() => decide(req, "reject")} className="inline-flex items-center gap-1 rounded-md border border-red-400/30 px-3 py-1.5 text-xs font-bold text-red-300 hover:bg-red-500/10 disabled:opacity-50" data-testid={`sensitive-request-reject-${req.id}`}><X className="h-3.5 w-3.5" /> Tolak</button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
