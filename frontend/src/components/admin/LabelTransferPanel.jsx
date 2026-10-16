import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRightLeft } from "lucide-react";
import { api } from "@/api/client";
import { TRANSFER_STATUS } from "@/components/label/LabelTransferCard";

// Transfers touching one label, with a shortcut to input a new one.
export function LabelTransferPanel({ label, canManage }) {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    api.get("/admin/label-transfers", { params: { label_id: label.id } }).then((r) => setRows(r.data || [])).catch(() => {});
  }, [label.id]);
  const createLink = `/admin/label-transfers?source=${encodeURIComponent(label.id)}&name=${encodeURIComponent(label.label_name || "")}`;
  return (
    <section className="rm-card p-5 space-y-3" data-testid="admin-label-transfer-panel">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 font-display text-lg font-bold tracking-tight"><ArrowRightLeft className="h-4 w-4 text-pink-400" /> Pindah / Ganti Nama Label</h3>
        {canManage && !label.merged_into_label_id && <Link to={createLink} className="rm-btn-ghost text-xs" data-testid="admin-label-transfer-create">Input Perpindahan</Link>}
      </div>
      {rows.length === 0 ? <div className="text-sm text-zinc-500">Belum ada perpindahan untuk label ini.</div> : rows.map((row) => {
        const badge = TRANSFER_STATUS[row.status] || TRANSFER_STATUS.pending;
        return (
          <Link key={row.id} to="/admin/label-transfers" className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm hover:bg-white/[0.03]">
            <span className="min-w-0"><span className="font-semibold">{row.summary}</span><span className="block text-[11px] text-zinc-500">{row.reference_id} · {(row.requested_at || "").slice(0, 10)}</span></span>
            <span className={`rm-badge ${badge.cls}`}>{badge.label}</span>
          </Link>
        );
      })}
    </section>
  );
}
