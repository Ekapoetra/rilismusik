import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { Sparkles, ExternalLink, CheckCircle2, RotateCcw, LifeBuoy } from "lucide-react";

const STATUS_STYLE = {
  pending: "bg-zinc-500/15 text-zinc-300",
  in_progress: "bg-amber-500/15 text-amber-300",
  delivered: "bg-sky-500/15 text-sky-300",
  completed: "bg-emerald-500/15 text-emerald-300",
  cancelled: "bg-red-500/15 text-red-300",
  revision: "bg-orange-500/15 text-orange-300",
  refunded: "bg-violet-500/15 text-violet-300",
};

const TERMINAL_STATUSES = ["completed", "cancelled", "refunded"];

export function LabelAddonOrders({ releaseId = null, title = "Layanan Tambahan", showRelease = false, hideWhenEmpty = true }) {
  const [orders, setOrders] = useState(null);
  const [labels, setLabels] = useState({});
  const [busy, setBusy] = useState("");
  const [revising, setRevising] = useState(null);
  const [revisionNote, setRevisionNote] = useState("");

  const load = useCallback(() => {
    const params = releaseId ? { params: { release_id: releaseId } } : {};
    api.get("/label/addon-orders", params)
      .then((r) => { setOrders(r.data.items || []); setLabels(r.data.labels || {}); })
      .catch(() => setOrders([]));
  }, [releaseId]);

  useEffect(() => { load(); }, [load]);

  if (orders === null) return null;
  if (orders.length === 0 && hideWhenEmpty) return null;

  const accept = async (order) => {
    setBusy(order.id);
    try {
      await api.post(`/label/addon-orders/${order.id}/accept`);
      toast.success("Hasil diterima — order selesai");
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail) || "Gagal"); }
    finally { setBusy(""); }
  };

  const submitRevision = async () => {
    if ((revisionNote || "").trim().length < 3) { toast.error("Tuliskan bagian yang perlu direvisi"); return; }
    setBusy(revising.id);
    try {
      await api.post(`/label/addon-orders/${revising.id}/revision`, { note: revisionNote.trim() });
      toast.success("Permintaan revisi dikirim ke admin");
      setRevising(null); setRevisionNote("");
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail) || "Gagal"); }
    finally { setBusy(""); }
  };

  return (
    <section className="rm-card p-5" data-testid="label-addon-orders">
      <div className="mb-4 flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-[#FF7FC0]" />
        <h3 className="font-display text-lg font-bold tracking-tight">{title}</h3>
      </div>
      {orders.length === 0 ? (
        <div className="text-sm text-zinc-500" data-testid="label-addon-orders-empty">Belum ada layanan tambahan.</div>
      ) : (
        <div className="space-y-3">
          {orders.map((o) => (
            <div key={o.id} className="rounded-lg border border-white/10 bg-white/[0.02] p-4" data-testid={`label-addon-order-${o.id}`}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold">{o.product_name}</div>
                  {showRelease && o.release_title && <div className="truncate text-xs text-zinc-500">Rilisan: {o.release_title}</div>}
                  {o.product_description && <div className="mt-0.5 text-xs text-zinc-500">{o.product_description}</div>}
                </div>
                <span className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-bold ${STATUS_STYLE[o.status] || STATUS_STYLE.pending}`} data-testid={`label-addon-order-status-${o.id}`}>
                  {o.status_label || labels[o.status] || o.status}
                </span>
              </div>
              {(o.delivery_url || o.delivery_note) && (
                <div className="mt-3 rounded-md border border-emerald-400/20 bg-emerald-400/[0.05] p-3">
                  <div className="text-[11px] font-bold uppercase tracking-widest text-emerald-300">Hasil</div>
                  {o.delivery_note && <p className="mt-1 text-xs text-zinc-300">{o.delivery_note}</p>}
                  {o.delivery_url && (
                    <a href={o.delivery_url} target="_blank" rel="noopener noreferrer" className="mt-1 inline-flex items-center gap-1.5 text-xs font-semibold rm-gradient-text" data-testid={`label-addon-order-link-${o.id}`}>
                      Buka / Unduh hasil <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  )}
                </div>
              )}
              {o.status === "revision" && o.revision_note && (
                <div className="mt-3 rounded-md border border-orange-400/20 bg-orange-400/[0.05] p-3" data-testid={`label-addon-revision-info-${o.id}`}>
                  <div className="text-[11px] font-bold uppercase tracking-widest text-orange-300">Revisi diminta</div>
                  <p className="mt-1 text-xs text-zinc-300">{o.revision_note}</p>
                </div>
              )}
              {o.status === "delivered" && o.revision_decision === "decline" && o.revision_decision_note && (
                <p className="mt-2 text-[11px] text-zinc-500" data-testid={`label-addon-revision-declined-${o.id}`}>Revisi ditolak: {o.revision_decision_note}</p>
              )}
              {o.status === "refunded" && (
                <div className="mt-3 rounded-md border border-violet-400/20 bg-violet-400/[0.05] p-3" data-testid={`label-addon-refund-info-${o.id}`}>
                  <div className="text-[11px] font-bold uppercase tracking-widest text-violet-300">
                    {o.benefit_restored ? "Benefit dikembalikan" : "Direfund"}
                  </div>
                  {o.refund_note && <p className="mt-1 text-xs text-zinc-300">{o.refund_note}</p>}
                </div>
              )}
              {o.status === "delivered" && (
                <div className="mt-3 flex flex-wrap gap-2">
                  <button onClick={() => accept(o)} disabled={busy === o.id} className="rm-btn-primary inline-flex items-center gap-1.5 py-1.5 text-xs" data-testid={`label-addon-accept-${o.id}`}>
                    <CheckCircle2 className="h-3.5 w-3.5" /> {busy === o.id ? "…" : "Terima Hasil"}
                  </button>
                  <button onClick={() => { setRevising(o); setRevisionNote(""); }} disabled={busy === o.id} className="rm-btn-ghost inline-flex items-center gap-1.5 py-1.5 text-xs" data-testid={`label-addon-revise-${o.id}`}>
                    <RotateCcw className="h-3.5 w-3.5" /> Minta Revisi
                  </button>
                </div>
              )}
              {!TERMINAL_STATUSES.includes(o.status) && (
                <p className="mt-3 text-[11px] text-zinc-500">
                  Ada masalah dengan pesanan ini?{" "}
                  <Link to="/label/support" className="inline-flex items-center gap-1 font-semibold rm-gradient-text" data-testid={`label-addon-ticket-${o.id}`}>
                    <LifeBuoy className="h-3 w-3" /> Ajukan tiket bantuan
                  </Link>
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {revising && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4" data-testid="label-addon-revision-modal" onClick={() => setRevising(null)}>
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-zinc-950 p-6" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-display text-lg font-bold">Minta Revisi — {revising.product_name}</h3>
            <p className="mt-1 text-xs text-zinc-500">Jelaskan bagian hasil yang perlu diperbaiki. Admin akan meninjau permintaan Anda.</p>
            <textarea value={revisionNote} onChange={(e) => setRevisionNote(e.target.value)} className="rm-input mt-4 min-h-[100px]"
              placeholder="Contoh: warna visualizer tidak sesuai arahan…" data-testid="label-addon-revision-note" />
            <div className="mt-5 flex justify-end gap-2">
              <button onClick={() => setRevising(null)} className="rm-btn-ghost">Batal</button>
              <button onClick={submitRevision} disabled={busy === revising.id} className="rm-btn-primary" data-testid="label-addon-revision-submit">
                {busy === revising.id ? "Mengirim…" : "Kirim Permintaan"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
