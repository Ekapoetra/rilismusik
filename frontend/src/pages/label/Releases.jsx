import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import StatusBadge from "@/components/shared/StatusBadge";
import { Disc3, Search, Filter } from "lucide-react";

const STATUSES = ["draft", "submitted", "awaiting_payment", "paid", "under_review", "need_revision", "approved", "delivered", "live", "rejected"];

export default function LabelReleases() {
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    load();
    // eslint-disable-next-line
  }, [status]);

  const load = async () => {
    const { data } = await api.get("/releases/", { params: { status: status || undefined, q: q || undefined } });
    setItems(data);
  };

  return (
    <div className="space-y-5 max-w-6xl">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-slate-500 font-bold">Rilisan</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter">Daftar Rilisan</h1>
        </div>
        <Link to="/label/releases/upload" className="rm-btn-primary" data-testid="label-releases-upload-button">+ Submit Rilisan</Link>
      </div>

      {/* Filters */}
      <div className="rm-card p-4 flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="rm-label">Cari Judul</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input className="rm-input pl-10" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()} placeholder="Cari rilisan…" data-testid="label-releases-search" />
          </div>
        </div>
        <div className="min-w-[180px]">
          <label className="rm-label">Status</label>
          <select className="rm-input" value={status} onChange={(e) => setStatus(e.target.value)} data-testid="label-releases-status-filter">
            <option value="">Semua</option>
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <button className="rm-btn-ghost flex items-center gap-2" onClick={load} data-testid="label-releases-apply-filter"><Filter className="w-4 h-4" /> Filter</button>
      </div>

      {/* Table */}
      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-slate-500 bg-slate-50/60 border-b border-slate-100">
          <div className="col-span-5">Judul / Artist</div>
          <div className="col-span-2">Tipe</div>
          <div className="col-span-2">Tanggal Rilis</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-1 text-right">Aksi</div>
        </div>
        {items.length === 0 ? (
          <div className="p-10 text-center text-slate-500 text-sm">Belum ada rilisan.</div>
        ) : items.map((r) => (
          <div key={r.id} className="px-5 py-4 border-b border-slate-50 last:border-0 grid grid-cols-12 gap-3 items-center hover:bg-slate-50/40">
            <div className="col-span-12 md:col-span-5 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-400 to-pink-500 grid place-items-center text-white"><Disc3 className="w-4 h-4" /></div>
              <div className="min-w-0">
                <div className="font-semibold truncate">{r.release_title}</div>
                <div className="text-xs text-slate-500 truncate">{r.artist_name}</div>
              </div>
            </div>
            <div className="col-span-6 md:col-span-2 text-sm capitalize">{r.release_type}</div>
            <div className="col-span-6 md:col-span-2 text-sm">{r.release_date}</div>
            <div className="col-span-6 md:col-span-2"><StatusBadge status={r.status} /></div>
            <div className="col-span-6 md:col-span-1 text-right"><Link to={`/label/releases/${r.id}`} className="text-sm font-semibold text-[#FF3B30]" data-testid={`label-release-detail-${r.id}`}>Detail →</Link></div>
          </div>
        ))}
      </div>
    </div>
  );
}
