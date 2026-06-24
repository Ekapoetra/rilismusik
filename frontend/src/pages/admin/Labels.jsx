import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import StatusBadge from "@/components/shared/StatusBadge";

export default function AdminLabels() {
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");

  const load = async () => {
    const { data } = await api.get("/admin/labels", { params: { q: q || undefined, status: status || undefined } });
    setItems(data);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [status]);

  return (
    <div className="space-y-5">
      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Operations</div>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">Label Management</h1>
      </div>
      <div className="rm-card p-4 flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="rm-label">Cari Label</label>
          <input className="rm-input" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()} placeholder="Nama label…" data-testid="admin-labels-search" />
        </div>
        <div className="min-w-[180px]">
          <label className="rm-label">Status</label>
          <select className="rm-input" value={status} onChange={(e) => setStatus(e.target.value)} data-testid="admin-labels-status">
            <option value="">Semua</option>
            <option value="active">Active</option>
            <option value="suspended">Suspended</option>
            <option value="blacklisted">Blacklisted</option>
          </select>
        </div>
        <button className="rm-btn-ghost" onClick={load}>Filter</button>
      </div>

      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5">
          <div className="col-span-4">Label</div>
          <div className="col-span-3">Email</div>
          <div className="col-span-2">Tipe</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-1 text-right">Aksi</div>
        </div>
        {items.length === 0 ? <div className="p-8 text-center text-zinc-500 text-sm">Belum ada label.</div> : items.map((l) => (
          <div key={l.id} className="px-5 py-4 grid grid-cols-12 gap-3 items-center border-b border-white/5 last:border-0 hover:bg-white/[0.02]">
            <div className="col-span-12 md:col-span-4">
              <div className="font-semibold">{l.label_name}</div>
              <div className="text-xs text-zinc-500">{l.pic_name}</div>
            </div>
            <div className="col-span-6 md:col-span-3 text-sm truncate">{l.email}</div>
            <div className="col-span-6 md:col-span-2 text-sm capitalize">{l.payment_type?.replace(/_/g, " ") || "—"}</div>
            <div className="col-span-6 md:col-span-2">
              <span className={`px-2.5 py-1 rounded-full text-xs font-bold capitalize ${l.account_status === "active" ? "bg-emerald-500/15 text-emerald-300" : l.account_status === "suspended" ? "bg-amber-500/100/15 text-amber-300" : "bg-red-500/15 text-red-300"}`}>{l.account_status}</span>
            </div>
            <div className="col-span-6 md:col-span-1 text-right">
              <Link to={`/admin/labels/${l.id}`} className="text-sm font-semibold rm-gradient-text" data-testid={`admin-label-detail-${l.id}`}>Detail →</Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
