import React, { useEffect, useState } from "react";
import { api } from "@/api/client";
import { Layers, ChevronDown, ChevronRight } from "lucide-react";

const fmtIDR = (n) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
const PILL = { requested: "bg-amber-500/15 text-amber-300", processing: "bg-sky-500/15 text-sky-300", paid: "bg-emerald-500/15 text-emerald-300", rejected: "bg-red-500/15 text-red-300" };

// Admin view of Multi Label withdrawal batches: one parent row per batch with child breakdown.
export default function MultiLabelBatchPanel() {
  const [batches, setBatches] = useState([]);
  const [open, setOpen] = useState({});
  useEffect(() => { api.get("/withdraw/admin/batches").then((r) => setBatches(r.data || [])).catch(() => {}); }, []);
  if (!batches.length) return null;
  return (
    <section className="rm-glass rounded-2xl p-5" data-testid="admin-ml-batch-panel">
      <div className="mb-3 flex items-center gap-2"><Layers className="h-4 w-4 text-[#C79BFF]" /><h3 className="font-display text-lg font-bold">Pencairan Multi Label (Batch)</h3></div>
      <div className="space-y-2">
        {batches.map((b) => (
          <div key={b.id} className="rounded-xl border border-white/10" data-testid={`ml-batch-${b.id}`}>
            <button onClick={() => setOpen((o) => ({ ...o, [b.id]: !o[b.id] }))} className="flex w-full items-center justify-between px-4 py-3 text-left">
              <div className="flex items-center gap-3">
                {open[b.id] ? <ChevronDown className="h-4 w-4 text-zinc-500" /> : <ChevronRight className="h-4 w-4 text-zinc-500" />}
                <div>
                  <div className="text-sm font-semibold">{b.primary_email || b.user_id}</div>
                  <div className="text-xs text-zinc-500">{b.label_count} label • cutoff {b.period_to || "—"}</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-display text-base font-extrabold tabular-nums rm-gradient-text">{fmtIDR(b.amount_total_idr)}</span>
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${PILL[b.status] || "bg-white/10 text-zinc-300"}`}>{b.status}</span>
              </div>
            </button>
            {open[b.id] && (
              <div className="border-t border-white/5 px-4 py-2">
                {(b.children || []).map((c) => (
                  <div key={c.id} className="flex items-center justify-between py-1.5 text-sm" data-testid={`ml-batch-child-${c.id}`}>
                    <span className="text-zinc-300">{c.label_name || c.label_id}</span>
                    <span className="flex items-center gap-3"><span className="tabular-nums text-zinc-400">{fmtIDR(c.amount_idr)}</span><span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${PILL[c.status] || "bg-white/10 text-zinc-300"}`}>{c.status}</span></span>
                  </div>
                ))}
                <p className="mt-1 text-[11px] text-zinc-500">Setiap child diproses di daftar penarikan di bawah. Batch = satu rekening tujuan.</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
