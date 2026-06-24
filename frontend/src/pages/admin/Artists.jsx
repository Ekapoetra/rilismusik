import React, { useEffect, useState } from "react";
import { api } from "@/api/client";

export default function AdminArtists() {
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const load = async () => {
    const { data } = await api.get("/admin/artists", { params: { q: q || undefined } });
    setItems(data);
  };
  useEffect(() => { load(); }, []);
  return (
    <div className="space-y-5">
      <div>
        <div className="text-xs uppercase tracking-widest text-slate-500 font-bold">Operations</div>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">Artist Management</h1>
      </div>
      <div className="rm-card p-4 flex gap-3 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="rm-label">Cari Artist</label>
          <input className="rm-input" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()} />
        </div>
        <button className="rm-btn-ghost" onClick={load}>Filter</button>
      </div>
      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-slate-500 bg-slate-50/60 border-b border-slate-100">
          <div className="col-span-4">Artist</div>
          <div className="col-span-3">Email</div>
          <div className="col-span-3">Label</div>
          <div className="col-span-2">Status</div>
        </div>
        {items.length === 0 ? <div className="p-8 text-center text-slate-500 text-sm">Belum ada artist.</div> : items.map((a) => (
          <div key={a.id} className="px-5 py-4 grid grid-cols-12 gap-3 items-center border-b border-slate-50 last:border-0">
            <div className="col-span-12 md:col-span-4 font-semibold">{a.artist_name}</div>
            <div className="col-span-6 md:col-span-3 text-sm truncate">{a.email}</div>
            <div className="col-span-6 md:col-span-3 text-sm truncate">{a.label_name || "—"}</div>
            <div className="col-span-12 md:col-span-2 text-xs capitalize">{a.status}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
