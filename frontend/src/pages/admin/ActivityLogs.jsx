import React, { useEffect, useState } from "react";
import { api } from "@/api/client";

export default function AdminActivityLogs() {
  const [items, setItems] = useState([]);
  useEffect(() => { api.get("/admin/activity-logs?limit=300").then((r) => setItems(r.data)); }, []);
  return (
    <div className="space-y-5">
      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Audit</div>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">Activity Logs</h1>
      </div>
      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5">
          <div className="col-span-3">Waktu</div>
          <div className="col-span-2">Module</div>
          <div className="col-span-3">Aksi</div>
          <div className="col-span-2">Referensi</div>
          <div className="col-span-2">User</div>
        </div>
        {items.length === 0 ? <div className="p-8 text-center text-zinc-500 text-sm">Belum ada log.</div> : items.map((l) => (
          <div key={l.id} className="px-5 py-3 grid grid-cols-12 gap-2 items-center border-b border-white/5 last:border-0 text-sm">
            <div className="col-span-12 md:col-span-3 text-zinc-500">{l.created_at?.slice(0, 19).replace("T", " ")}</div>
            <div className="col-span-6 md:col-span-2 capitalize">{l.module}</div>
            <div className="col-span-6 md:col-span-3 font-semibold">{l.action}</div>
            <div className="col-span-6 md:col-span-2 text-zinc-500 truncate">{l.reference_id || "—"}</div>
            <div className="col-span-6 md:col-span-2 text-zinc-500 truncate">{l.user_id?.slice(0, 8)}…</div>
          </div>
        ))}
      </div>
    </div>
  );
}
