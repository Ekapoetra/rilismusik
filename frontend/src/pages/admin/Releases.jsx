import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import StatusBadge, { STATUS_LABELS } from "@/components/shared/StatusBadge";

const REVIEWABLE = ["paid", "under_review", "need_revision", "approved", "delivered", "live"];

export default function AdminReleases() {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("under_review");
  const [q, setQ] = useState("");

  const load = async () => {
    const { data } = await api.get("/admin/releases", { params: { status: status || undefined, q: q || undefined } });
    setItems(data);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [status]);

  return (
    <div className="space-y-5">
      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Release Operations</div>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">Release Management</h1>
      </div>

      <div className="rm-card p-4 flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="rm-label">Cari Judul</label>
          <input className="rm-input" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()} data-testid="admin-releases-search" />
        </div>
        <div className="min-w-[200px]">
          <label className="rm-label">Status</label>
          <select className="rm-input" value={status} onChange={(e) => setStatus(e.target.value)} data-testid="admin-releases-status">
            <option value="">Semua</option>
            {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <button className="rm-btn-ghost" onClick={load}>Filter</button>
      </div>

      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5">
          <div className="col-span-4">Rilisan</div>
          <div className="col-span-3">Label</div>
          <div className="col-span-2">Release Date</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-1 text-right">Aksi</div>
        </div>
        {items.length === 0 ? <div className="p-8 text-center text-zinc-500 text-sm">Tidak ada rilisan.</div> : items.map((r) => (
          <div key={r.id} className="px-5 py-4 grid grid-cols-12 gap-3 items-center border-b border-white/5 last:border-0 hover:bg-white/[0.02]">
            <div className="col-span-12 md:col-span-4">
              <div className="font-semibold">{r.release_title}</div>
              <div className="text-xs text-zinc-500">{r.artist_name} • {r.release_type}</div>
            </div>
            <div className="col-span-6 md:col-span-3 text-sm">{r.label_name || "—"}</div>
            <div className="col-span-6 md:col-span-2 text-sm">{r.release_date}</div>
            <div className="col-span-6 md:col-span-2"><StatusBadge status={r.status} /></div>
            <div className="col-span-6 md:col-span-1 text-right"><Link to={`/admin/releases/${r.id}`} className="text-sm font-semibold rm-gradient-text" data-testid={`admin-release-detail-${r.id}`}>Review →</Link></div>
          </div>
        ))}
      </div>
    </div>
  );
}
