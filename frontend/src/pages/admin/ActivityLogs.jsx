import React, { useEffect, useState } from "react";
import { api, formatApiError } from "@/api/client";

export default function AdminActivityLogs() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/admin/activity-logs?limit=300")
      .then((response) => setItems(response.data))
      .catch((requestError) => setError(formatApiError(requestError.response?.data?.detail)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-w-0 space-y-5" data-testid="admin-activity-logs-page">
      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Audit</div>
        <h1 className="font-display text-4xl font-extrabold">Log Aktivitas</h1>
      </div>
      {error && <div className="rounded-md border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-200" role="alert" data-testid="admin-activity-logs-error">{error}</div>}
      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5">
          <div className="col-span-3">Waktu</div>
          <div className="col-span-2">Modul</div>
          <div className="col-span-3">Aksi</div>
          <div className="col-span-2">Referensi</div>
          <div className="col-span-2">Pengguna</div>
        </div>
        {loading ? (
          <div className="p-8 text-center text-sm text-zinc-500" data-testid="admin-activity-logs-loading">Memuat log aktivitas…</div>
        ) : items.length === 0 ? (
          <div className="p-8 text-center text-sm text-zinc-500" data-testid="admin-activity-logs-empty">Belum ada log.</div>
        ) : items.map((log) => (
          <div key={log.id} className="grid min-w-0 grid-cols-12 items-center gap-2 border-b border-white/5 px-5 py-3 text-sm last:border-0" data-testid={`admin-activity-log-row-${log.id}`}>
            <div className="col-span-12 text-zinc-500 md:col-span-3" data-testid={`admin-activity-log-time-${log.id}`}>{log.created_at?.slice(0, 19).replace("T", " ")}</div>
            <div className="col-span-6 capitalize md:col-span-2" data-testid={`admin-activity-log-module-${log.id}`}>{log.module}</div>
            <div className="col-span-6 break-words font-semibold md:col-span-3" data-testid={`admin-activity-log-action-${log.id}`}>{log.action}</div>
            <div className="col-span-6 truncate text-zinc-500 md:col-span-2" title={log.reference_id || ""} data-testid={`admin-activity-log-reference-${log.id}`}>{log.reference_id || "—"}</div>
            <div className="col-span-6 min-w-0 break-words font-semibold text-zinc-300 md:col-span-2" title={log.user_name || log.user_id || "Sistem"} data-testid={`admin-activity-log-user-${log.id}`}>
              {log.user_name || log.user_id || "Sistem"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
