import React, { useCallback, useEffect, useState } from "react";
import { History, Plus, Minus, Pencil, Trash2, RefreshCw } from "lucide-react";
import { api } from "@/api/client";

const ACTION_META = {
  create_admin_role: { label: "Role dibuat", cls: "bg-emerald-500/15 text-emerald-300", Icon: Plus },
  update_admin_role: { label: "Izin diubah", cls: "bg-sky-500/15 text-sky-300", Icon: Pencil },
  delete_admin_role: { label: "Role dihapus", cls: "bg-red-500/15 text-red-300", Icon: Trash2 },
};

const fmt = (iso) => { try { return new Date(iso).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" }); } catch { return iso; } };

export const RoleAuditPanel = () => {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    setLoading(true);
    try { const { data } = await api.get("/admin/access/role-audit", { params: { limit: 100 } }); setEntries(data.entries || []); }
    catch { /* non-fatal */ }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <section className="border-t border-white/10 pt-6" data-testid="admin-role-audit-panel">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-zinc-500"><History className="h-4 w-4" /> Riwayat Perubahan Izin</div>
        <button type="button" onClick={load} className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white" data-testid="admin-role-audit-refresh"><RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} /> Muat ulang</button>
      </div>
      {loading ? <p className="text-sm text-zinc-600">Memuat…</p> : entries.length === 0 ? (
        <p className="text-sm text-zinc-600" data-testid="admin-role-audit-empty">Belum ada perubahan izin yang tercatat.</p>
      ) : (
        <ol className="space-y-3">
          {entries.map((e) => { const meta = ACTION_META[e.action] || ACTION_META.update_admin_role; return (
            <li key={e.id} className="rounded-md border border-white/10 bg-white/[0.02] p-3" data-testid="admin-role-audit-entry">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-bold ${meta.cls}`}><meta.Icon className="h-3 w-3" />{meta.label}</span>
                  <strong className="text-sm text-zinc-200" translate="no">{e.role_name}</strong>
                </div>
                <div className="text-[11px] text-zinc-500">oleh <span className="text-zinc-300">{e.actor_name}</span> · {fmt(e.at)}</div>
              </div>
              {e.name_changed && <div className="mt-2 text-xs text-zinc-400">Nama: <span className="line-through text-zinc-600">{e.name_from || "—"}</span> → <span className="text-zinc-200">{e.name_to || "—"}</span></div>}
              {e.active_changed && <div className="mt-2 text-xs text-zinc-400">Status: <span className={e.active_to ? "text-emerald-300" : "text-red-300"}>{e.active_to ? "Aktif" : "Nonaktif"}</span></div>}
              {(e.added.length > 0 || e.removed.length > 0) && (
                <div className="mt-2 flex flex-wrap gap-1.5" data-testid="admin-role-audit-diff">
                  {e.added.map((p) => <span key={`a-${p.key}`} className="inline-flex items-center gap-1 rounded bg-emerald-500/10 px-2 py-0.5 text-[11px] text-emerald-300" title={p.key}><Plus className="h-3 w-3" />{p.label}</span>)}
                  {e.removed.map((p) => <span key={`r-${p.key}`} className="inline-flex items-center gap-1 rounded bg-red-500/10 px-2 py-0.5 text-[11px] text-red-300" title={p.key}><Minus className="h-3 w-3" />{p.label}</span>)}
                </div>
              )}
            </li>
          ); })}
        </ol>
      )}
    </section>
  );
};
