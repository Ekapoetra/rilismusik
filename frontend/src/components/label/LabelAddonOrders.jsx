import React, { useEffect, useState } from "react";
import { api } from "@/api/client";
import { Sparkles, ExternalLink } from "lucide-react";

const STATUS_STYLE = {
  pending: "bg-zinc-500/15 text-zinc-300",
  in_progress: "bg-amber-500/15 text-amber-300",
  delivered: "bg-sky-500/15 text-sky-300",
  completed: "bg-emerald-500/15 text-emerald-300",
  cancelled: "bg-red-500/15 text-red-300",
};

export function LabelAddonOrders({ releaseId = null, title = "Layanan Tambahan", showRelease = false, hideWhenEmpty = true }) {
  const [orders, setOrders] = useState(null);
  const [labels, setLabels] = useState({});

  useEffect(() => {
    const params = releaseId ? { params: { release_id: releaseId } } : {};
    api.get("/label/addon-orders", params)
      .then((r) => { setOrders(r.data.items || []); setLabels(r.data.labels || {}); })
      .catch(() => setOrders([]));
  }, [releaseId]);

  if (orders === null) return null;
  if (orders.length === 0 && hideWhenEmpty) return null;

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
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
