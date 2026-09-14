import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, Check, X, ExternalLink } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { toast } from "@/components/ui/sonner";

const TABS = [
  { key: "pending", label: "Menunggu" },
  { key: "approved", label: "Disetujui" },
  { key: "rejected", label: "Ditolak" },
  { key: "", label: "Semua" },
];
const BADGE = {
  pending: "bg-amber-500/15 text-amber-300",
  approved: "bg-emerald-500/15 text-emerald-300",
  rejected: "bg-red-500/15 text-red-300",
};
const TYPE_LABEL = { rate: "Rate/Fee", package: "Paket", blacklist: "Blacklist" };

export default function RateChangeQueue() {
  const { hasPermission } = useAuth();
  const [tab, setTab] = useState("pending");
  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const approvePerm = { rate: "labels.rate.approve", package: "labels.package.approve", blacklist: "labels.blacklist.approve" };

  const load = useCallback(async () => {
    setErr("");
    const params = tab ? { status: tab } : {};
    const rateReq = api.get("/admin/rate-changes", { params }).then((r) => (r.data || []).map((x) => ({
      ...x, _kind: "rate", _type: "rate", _summary: `${x.current_value}% → ${x.proposed_value}%`,
    }))).catch(() => []);
    const sensReq = api.get("/admin/sensitive-requests", { params }).then((r) => (r.data || []).map((x) => ({
      ...x, _kind: "sensitive", _type: x.action_type, _summary: x.summary,
    }))).catch(() => []);
    try {
      const [a, b] = await Promise.all([rateReq, sensReq]);
      const merged = [...a, ...b].sort((x, y) => (y.requested_at || "").localeCompare(x.requested_at || ""));
      setRows(merged);
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
  }, [tab]);
  useEffect(() => { load(); }, [load]);

  const decide = async (req, action) => {
    let note = "";
    if (action === "reject") note = window.prompt("Alasan penolakan (opsional):") ?? "";
    setBusy(true); setErr("");
    try {
      const url = req._kind === "rate" ? `/admin/rate-changes/${req.id}/decision` : `/admin/sensitive-requests/${req.id}/decision`;
      await api.post(url, { action, note });
      toast.success(action === "approve" ? "Permintaan disetujui & diterapkan." : "Permintaan ditolak.");
      await load();
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-6" data-testid="admin-rate-change-queue">
      <header className="border-b border-white/10 pb-5">
        <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Aksi Sensitif</div>
        <h1 className="mt-1 flex items-center gap-2 font-display text-3xl font-extrabold"><ShieldCheck className="h-6 w-6 text-pink-400" /> Persetujuan Aksi Sensitif</h1>
        <p className="mt-2 text-sm text-zinc-400">Perubahan rate/fee, paket, dan blacklist tidak berlaku sampai Super Admin menyetujui permintaan.</p>
      </header>

      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => <button key={t.key} type="button" onClick={() => setTab(t.key)} className={`rounded-full px-4 py-1.5 text-sm font-bold transition-colors ${tab === t.key ? "bg-white text-black" : "border border-white/10 text-zinc-400 hover:text-white"}`} data-testid={`rate-queue-tab-${t.key || "all"}`}>{t.label}</button>)}
      </div>

      {err && <div className="rounded-md bg-red-500/15 text-red-300 px-4 py-3 text-sm" data-testid="rate-queue-error">{err}</div>}

      {rows.length === 0 ? (
        <div className="rounded-md border border-white/10 py-16 text-center text-sm text-zinc-500" data-testid="rate-queue-empty">Tidak ada permintaan.</div>
      ) : (
        <div className="space-y-3">
          {rows.map((req) => {
            const canApprove = hasPermission(approvePerm[req._type]);
            return (
              <div key={`${req._kind}-${req.id}`} className="rounded-lg border border-white/10 bg-white/[0.02] p-4" data-testid={`rate-queue-row-${req.id}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="rm-badge bg-white/10 text-zinc-300 text-[10px]">{TYPE_LABEL[req._type] || req._type}</span>
                    <span className="font-mono text-xs text-zinc-500">{req.reference_id}</span>
                    <span className={`rm-badge ${BADGE[req.status] || BADGE.pending}`}>{req.status}</span>
                  </div>
                  <Link to={`/admin/labels/${req.label_id}`} className="inline-flex items-center gap-1 text-xs text-sky-300 hover:text-sky-200" data-testid={`rate-queue-label-link-${req.id}`}>{req.label_name} <ExternalLink className="h-3 w-3" /></Link>
                </div>
                <div className="mt-2 text-lg font-bold">{req._summary}</div>
                <div className="mt-1 text-sm text-zinc-400">Alasan: {req.reason || "—"}</div>
                <div className="mt-1 text-[11px] text-zinc-500">Diajukan oleh {req.requested_by_name} · {(req.requested_at || "").slice(0, 10)}{req.decided_by_name ? ` · Diputuskan oleh ${req.decided_by_name}` : ""}</div>
                {canApprove && req.status === "pending" && (
                  <div className="mt-3 flex gap-2">
                    <button type="button" disabled={busy} onClick={() => decide(req, "approve")} className="inline-flex items-center gap-1 rounded-md border border-emerald-400/30 px-4 py-2 text-xs font-bold text-emerald-300 hover:bg-emerald-500/10 disabled:opacity-50" data-testid={`rate-queue-approve-${req.id}`}><Check className="h-4 w-4" /> Setujui & Terapkan</button>
                    <button type="button" disabled={busy} onClick={() => decide(req, "reject")} className="inline-flex items-center gap-1 rounded-md border border-red-400/30 px-4 py-2 text-xs font-bold text-red-300 hover:bg-red-500/10 disabled:opacity-50" data-testid={`rate-queue-reject-${req.id}`}><X className="h-4 w-4" /> Tolak</button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
