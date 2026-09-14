import React, { useCallback, useEffect, useMemo, useState } from "react";
import { api, formatApiError } from "@/api/client";
import { Search, Filter, X } from "lucide-react";

const CATEGORIES = [
  { key: "", label: "Semua" },
  { key: "work", label: "Work" },
  { key: "finance", label: "Finansial" },
  { key: "system", label: "Sistem" },
];
const CAT_META = {
  work: { label: "Work", cls: "bg-pink-500/15 text-pink-300" },
  finance: { label: "Finansial", cls: "bg-emerald-500/15 text-emerald-300" },
  system: { label: "Sistem", cls: "bg-indigo-500/15 text-indigo-300" },
};
const humanize = (s) => (s || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export default function AdminActivityLogs() {
  const [items, setItems] = useState([]);
  const [actors, setActors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [category, setCategory] = useState("");
  const [actor, setActor] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [q, setQ] = useState("");
  const [qInput, setQInput] = useState("");

  const load = useCallback(() => {
    setLoading(true); setError("");
    api.get("/admin/activity-logs", { params: { limit: 300, category: category || undefined, actor: actor || undefined, start: start || undefined, end: end || undefined, q: q || undefined } })
      .then((r) => setItems(r.data))
      .catch((e) => setError(formatApiError(e.response?.data?.detail)))
      .finally(() => setLoading(false));
  }, [category, actor, start, end, q]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { api.get("/admin/activity-logs/actors").then((r) => setActors(r.data || [])).catch(() => {}); }, []);

  const hasFilter = category || actor || start || end || q;
  const clear = () => { setCategory(""); setActor(""); setStart(""); setEnd(""); setQ(""); setQInput(""); };
  const counts = useMemo(() => items.length, [items]);

  return (
    <div className="min-w-0 space-y-5" data-testid="admin-activity-logs-page">
      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Audit</div>
        <h1 className="font-display text-4xl font-extrabold">Pusat Aktivitas</h1>
        <p className="mt-1 text-sm text-zinc-400">Rekam jejak siapa melakukan apa. Saring berdasarkan kategori, aktor, atau tanggal.</p>
      </div>

      {/* Filters */}
      <div className="rm-card p-4 space-y-3" data-testid="admin-activity-filters">
        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-md border border-white/10 bg-white/[0.03] p-1" data-testid="admin-activity-category-tabs">
            {CATEGORIES.map((c) => (
              <button key={c.key || "all"} type="button" onClick={() => setCategory(c.key)} className={`rounded px-3.5 py-1.5 text-sm font-bold transition-colors ${category === c.key ? "bg-white text-black" : "text-zinc-500 hover:text-white"}`} data-testid={`admin-activity-cat-${c.key || "all"}`}>{c.label}</button>
            ))}
          </div>
          <div className="relative ml-auto min-w-[180px] flex-1 sm:max-w-xs">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
            <input value={qInput} onChange={(e) => setQInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && setQ(qInput)} placeholder="Cari aksi / referensi…" className="rm-input pl-9" data-testid="admin-activity-search" />
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-xs text-zinc-400">Aktor
            <select value={actor} onChange={(e) => setActor(e.target.value)} className="rm-input ml-1 inline-block w-44 py-1.5" data-testid="admin-activity-actor-filter">
              <option value="">Semua aktor</option>
              {actors.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </label>
          <label className="text-xs text-zinc-400">Dari
            <input type="date" value={start} onChange={(e) => setStart(e.target.value)} className="rm-input ml-1 inline-block w-40 py-1.5" data-testid="admin-activity-start" />
          </label>
          <label className="text-xs text-zinc-400">Sampai
            <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} className="rm-input ml-1 inline-block w-40 py-1.5" data-testid="admin-activity-end" />
          </label>
          {hasFilter && <button type="button" onClick={clear} className="rm-btn-ghost inline-flex items-center gap-1.5 text-xs" data-testid="admin-activity-clear"><X className="h-3.5 w-3.5" /> Reset</button>}
          <span className="ml-auto inline-flex items-center gap-1.5 text-xs text-zinc-500" data-testid="admin-activity-count"><Filter className="h-3.5 w-3.5" /> {counts} entri</span>
        </div>
      </div>

      {error && <div className="rounded-md border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-200" role="alert" data-testid="admin-activity-logs-error">{error}</div>}

      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5">
          <div className="col-span-3">Waktu</div>
          <div className="col-span-2">Kategori</div>
          <div className="col-span-3">Aksi</div>
          <div className="col-span-2">Referensi</div>
          <div className="col-span-2">Pengguna</div>
        </div>
        {loading ? (
          <div className="p-8 text-center text-sm text-zinc-500" data-testid="admin-activity-logs-loading">Memuat log aktivitas…</div>
        ) : items.length === 0 ? (
          <div className="p-8 text-center text-sm text-zinc-500" data-testid="admin-activity-logs-empty">Tidak ada log yang cocok dengan filter.</div>
        ) : items.map((log) => {
          const meta = CAT_META[log.category] || CAT_META.system;
          return (
            <div key={log.id} className="grid min-w-0 grid-cols-12 items-center gap-2 border-b border-white/5 px-5 py-3 text-sm last:border-0" data-testid={`admin-activity-log-row-${log.id}`}>
              <div className="col-span-12 text-zinc-500 md:col-span-3" data-testid={`admin-activity-log-time-${log.id}`}>{log.created_at?.slice(0, 19).replace("T", " ")}</div>
              <div className="col-span-6 md:col-span-2" data-testid={`admin-activity-log-category-${log.id}`}>
                <span className={`inline-block rounded px-2 py-0.5 text-[11px] font-bold ${meta.cls}`}>{meta.label}</span>
                <span className="ml-1 text-[11px] capitalize text-zinc-600">{humanize(log.module)}</span>
              </div>
              <div className="col-span-6 break-words font-semibold md:col-span-3" data-testid={`admin-activity-log-action-${log.id}`}>{humanize(log.action)}</div>
              <div className="col-span-6 truncate text-zinc-500 md:col-span-2" title={log.reference_id || ""} data-testid={`admin-activity-log-reference-${log.id}`}>{log.reference_id || "—"}</div>
              <div className="col-span-6 min-w-0 break-words font-semibold text-zinc-300 md:col-span-2" title={log.user_name || log.user_id || "Sistem"} data-testid={`admin-activity-log-user-${log.id}`}>
                {log.user_name || log.user_id || "Sistem"}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
