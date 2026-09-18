import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import * as Icons from "lucide-react";
import { ClipboardList, AlertTriangle, Clock, ArrowRight, Settings2, History as HistoryIcon, X, ShieldCheck } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { toast } from "@/components/ui/sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";

const PRIORITY = { critical: "bg-red-500/15 text-red-300", high: "bg-orange-500/15 text-orange-300", normal: "bg-sky-500/15 text-sky-300", low: "bg-zinc-500/15 text-zinc-300" };
const iconFor = (name) => Icons[name] || Icons.Circle;

function WorkCard({ item, onOpen }) {
  const Ico = iconFor(item.icon);
  return (
    <button type="button" onClick={() => onOpen(item)} className={`group flex flex-col rounded-lg border p-5 text-left transition-all hover:-translate-y-0.5 ${item.overdue_count ? "border-red-400/30 bg-red-500/[0.04]" : "border-white/10 bg-white/[0.02] hover:bg-white/[0.05]"}`} data-testid={`work-card-${item.work_type}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2"><span className="grid h-9 w-9 place-items-center rounded-md bg-white/5"><Ico className="h-4 w-4 text-pink-300" /></span><span className={`rm-badge text-[10px] ${PRIORITY[item.priority] || PRIORITY.normal}`}>{item.priority}</span></div>
        <span className="font-display text-3xl font-extrabold tabular-nums" data-testid={`work-count-${item.work_type}`}>{item.open_count}</span>
      </div>
      <h3 className="mt-3 font-bold">{item.label_id}</h3>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-zinc-500">
        {item.overdue_count > 0 && <span className="inline-flex items-center gap-1 rounded bg-red-500/15 px-1.5 py-0.5 font-bold text-red-300" data-testid={`work-overdue-${item.work_type}`}><AlertTriangle className="h-3 w-3" />{item.overdue_count} lewat tempo</span>}
        {item.oldest_age_days > 0 && <span className="inline-flex items-center gap-1"><Clock className="h-3 w-3" />tertua {item.oldest_age_days} hari</span>}
        <span>SLA {item.sla_days}h</span>
      </div>
      {item.scope === "super_admin_only" && <div className="mt-3 inline-flex items-center gap-1 rounded bg-violet-500/15 px-2 py-0.5 text-[10px] font-bold text-violet-300">Khusus Super Admin</div>}
      <div className="mt-4 inline-flex items-center gap-1 text-sm font-bold text-pink-300 opacity-0 transition-opacity group-hover:opacity-100">Buka modul <ArrowRight className="h-4 w-4" /></div>
    </button>
  );
}

function ConfigDialog({ open, onClose, onSaved }) {
  const [data, setData] = useState(null);
  const load = useCallback(async () => { const { data } = await api.get("/admin/work/settings"); setData(data); }, []);
  useEffect(() => { if (open) load(); }, [open, load]);
  const saveSla = async (wt, days) => {
    try { await api.put("/admin/work/settings/sla", { work_type: wt.key, sla_days: Number(days) }); toast.success("SLA disimpan."); onSaved && onSaved(); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="ui-menu max-h-[90dvh] w-[calc(100%-2rem)] max-w-3xl overflow-y-auto rounded-lg" data-testid="work-config-dialog">
        <DialogHeader><DialogTitle>Konfigurasi SLA</DialogTitle><DialogDescription>Ambang SLA (hari) per jenis pekerjaan. Kepemilikan pekerjaan otomatis mengikuti izin role (atau khusus Super Admin) — atur izin di menu Role &amp; Permission.</DialogDescription></DialogHeader>
        {!data ? <p className="text-sm text-zinc-500">Memuat…</p> : (
          <div className="space-y-4">
            {data.work_types.map((wt) => (
              <div key={wt.key} className="rounded-md border border-white/10 p-3" data-testid={`work-config-${wt.key}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <strong className="text-sm">{wt.label_id}{wt.scope === "super_admin_only" && <span className="ml-2 rm-badge bg-violet-500/15 text-violet-300 text-[10px]">Khusus Super Admin</span>}</strong>
                  <label className="flex items-center gap-2 text-xs text-zinc-400">SLA (hari)<input type="number" min="0" max="90" defaultValue={wt.sla_days} className="rm-input w-20 py-1" onBlur={(e) => saveSla(wt, e.target.value)} data-testid={`work-sla-${wt.key}`} /></label>
                </div>
                <div className="mt-2 text-[11px] text-zinc-500" data-testid={`work-config-roles-${wt.key}`}>
                  {wt.scope === "super_admin_only" ? "Pekerjaan eksklusif Super Admin — tidak perlu izin role." : <>Izin: <span className="font-mono text-zinc-400">{wt.permission}</span> — otomatis muncul di Pekerjaan Saya role yang memiliki izin ini.</>}
                </div>
              </div>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function WorkQueue() {
  const { hasPermission } = useAuth();
  const navigate = useNavigate();
  const [scope, setScope] = useState("my");
  const [view, setView] = useState("queue");
  const [data, setData] = useState(null);
  const [history, setHistory] = useState([]);
  const [cfgOpen, setCfgOpen] = useState(false);
  const [err, setErr] = useState("");
  const canManage = hasPermission("work.manage");

  const load = useCallback(async () => {
    setErr("");
    try { const { data } = await api.get("/admin/work/queue", { params: { scope } }); setData(data); }
    catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
  }, [scope]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (view === "history") api.get("/admin/work/history").then((r) => setHistory(r.data.items || [])).catch(() => {}); }, [view]);

  const openItem = (item) => { navigate(item.link); };
  const isManager = data?.is_manager;

  return (
    <div className="space-y-6" data-testid="admin-work-page">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-white/10 pb-5">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Operasional</div>
          <h1 className="mt-1 flex items-center gap-2 font-display text-3xl font-extrabold"><ClipboardList className="h-6 w-6 text-pink-400" /> Pekerjaan</h1>
          <p className="mt-2 text-sm text-zinc-400">Monitor pekerjaan terbuka per tanggung jawab role. Pekerjaan diselesaikan otomatis dari event bisnis nyata di modul terkait.</p>
        </div>
        {canManage && <button type="button" onClick={() => setCfgOpen(true)} className="rm-btn-ghost inline-flex items-center gap-2 text-sm" data-testid="work-config-open"><Settings2 className="h-4 w-4" /> Konfigurasi</button>}
      </header>

      <div className="flex flex-wrap items-center gap-2">
        <button type="button" onClick={() => setView("queue")} className={`rounded-full px-4 py-1.5 text-sm font-bold ${view === "queue" ? "bg-white text-black" : "border border-white/10 text-zinc-400 hover:text-white"}`} data-testid="work-view-queue">Antrean</button>
        <button type="button" onClick={() => setView("history")} className={`inline-flex items-center gap-1 rounded-full px-4 py-1.5 text-sm font-bold ${view === "history" ? "bg-white text-black" : "border border-white/10 text-zinc-400 hover:text-white"}`} data-testid="work-view-history"><HistoryIcon className="h-3.5 w-3.5" />Riwayat</button>
        {view === "queue" && <div className="ml-auto flex gap-2">
          <button type="button" onClick={() => setScope("my")} className={`rounded-full px-4 py-1.5 text-sm font-bold ${scope === "my" ? "bg-pink-500 text-white" : "border border-white/10 text-zinc-400 hover:text-white"}`} data-testid="work-scope-my">Pekerjaan Saya</button>
          {isManager && <button type="button" onClick={() => setScope("team")} className={`rounded-full px-4 py-1.5 text-sm font-bold ${scope === "team" ? "bg-pink-500 text-white" : "border border-white/10 text-zinc-400 hover:text-white"}`} data-testid="work-scope-team">Team Monitor</button>}
        </div>}
      </div>

      {err && <div className="rounded-md bg-red-500/15 px-4 py-3 text-sm text-red-300" data-testid="work-error">{err}</div>}

      {view === "queue" && data && (
        <>
          {data.items.length === 0 ? (
            <div className="rounded-md border border-white/10 py-16 text-center text-sm text-zinc-500" data-testid="work-empty">Tidak ada pekerjaan untuk Anda saat ini.</div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="work-grid">
              {data.items.map((item) => <WorkCard key={item.work_type} item={item} onOpen={openItem} />)}
            </div>
          )}
        </>
      )}

      {view === "history" && (
        <div className="overflow-x-auto rounded-lg border border-white/10" data-testid="work-history-table">
          <table className="w-full text-sm">
            <thead className="bg-white/5 text-left text-xs uppercase text-zinc-500"><tr><th className="px-4 py-3">Work Type</th><th className="px-4 py-3">Referensi</th><th className="px-4 py-3">Diselesaikan Oleh</th><th className="px-4 py-3">Waktu</th></tr></thead>
            <tbody>
              {history.length === 0 ? <tr><td colSpan={4} className="px-4 py-10 text-center text-zinc-500">Belum ada riwayat penyelesaian.</td></tr> : history.map((h) => (
                <tr key={h.id} className="border-t border-white/5" data-testid={`work-history-row-${h.id}`}>
                  <td className="px-4 py-3">{h.work_type_label_id}</td>
                  <td className="px-4 py-3 text-zinc-400">{h.entity_ref || h.entity_id}{h.label_name ? ` · ${h.label_name}` : ""}</td>
                  <td className="px-4 py-3">{h.completed_by_name}{h.completed_by_super && <span className="ml-2 rm-badge bg-violet-500/15 text-violet-300 text-[10px]"><ShieldCheck className="mr-0.5 inline h-3 w-3" />Super Admin</span>}</td>
                  <td className="px-4 py-3 text-zinc-500">{(h.completed_at || "").replace("T", " ").slice(0, 16)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ConfigDialog open={cfgOpen} onClose={() => setCfgOpen(false)} onSaved={load} />
    </div>
  );
}
