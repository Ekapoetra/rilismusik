import React, { useCallback, useEffect, useState } from "react";
import { Activity, Send } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

const STATUS_CLS = {
  PRESENT: "bg-emerald-500/15 text-emerald-300", LATE: "bg-amber-500/15 text-amber-300",
  ABSENT: "bg-red-500/15 text-red-300", LEAVE: "bg-sky-500/15 text-sky-300",
  HOLIDAY: "bg-zinc-500/15 text-zinc-400", NOT_RECORDED: "bg-white/5 text-zinc-500",
};

export default function WorkspaceStatus() {
  const { t } = useAppPreferences();
  const [me, setMe] = useState(null); const [team, setTeam] = useState(null);
  const [leaveForm, setLeaveForm] = useState({ type: "annual", start_date: "", end_date: "", reason: "" });
  const load = useCallback(async () => {
    try { const { data } = await api.get("/admin/status/me"); setMe(data); } catch { setMe({ is_staff: false }); }
    try { const { data } = await api.get("/admin/status/team"); setTeam(data); } catch { setTeam(null); }
  }, []);
  useEffect(() => { load(); }, [load]);
  const submitLeave = async () => { if (!leaveForm.start_date || !leaveForm.end_date || leaveForm.reason.trim().length < 3) { toast.error(t("Lengkapi form cuti")); return; } try { await api.post("/admin/leave", leaveForm); toast.success(t("Permohonan cuti terkirim")); setLeaveForm({ type: "annual", start_date: "", end_date: "", reason: "" }); } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); } };

  return (
    <div className="space-y-5" data-testid="workspace-status-page">
      <div className="border-b border-white/10 pb-4"><div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Workspace</div><h1 className="flex items-center gap-2 font-display text-3xl font-extrabold"><Activity className="h-6 w-6 text-pink-400" /> {t("Status")}</h1></div>

      {me?.is_staff && (
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rm-card p-5" data-testid="status-me">
            <div className="text-sm font-bold">{t("Status Saya Hari Ini")}</div>
            <div className="mt-3"><span className={`rounded-full px-3 py-1.5 text-sm font-bold ${STATUS_CLS[me.today?.status]}`} data-testid="status-me-today">{t(me.today?.status)}</span></div>
            <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">{Object.entries(me.summary_30d || {}).map(([k, v]) => <div key={k} className="rounded-md bg-white/[0.03] py-2"><div className="text-lg font-bold">{v}</div><div className="text-zinc-500">{t(k)}</div></div>)}</div>
          </div>
          <div className="rm-card space-y-2 p-5" data-testid="status-leave-form">
            <div className="text-sm font-bold">{t("Ajukan Cuti / Izin")}</div>
            <div className="grid grid-cols-2 gap-2">
              <label className="block"><span className="rm-label">{t("Jenis")}</span><select className="rm-input" value={leaveForm.type} onChange={(e) => setLeaveForm({ ...leaveForm, type: e.target.value })} data-testid="leave-type"><option value="annual">{t("annual")}</option><option value="sick">{t("sick")}</option><option value="permit">{t("permit")}</option></select></label>
              <div />
              <label className="block"><span className="rm-label">{t("Mulai")}</span><input type="date" className="rm-input" value={leaveForm.start_date} onChange={(e) => setLeaveForm({ ...leaveForm, start_date: e.target.value })} data-testid="leave-start" /></label>
              <label className="block"><span className="rm-label">{t("Selesai")}</span><input type="date" className="rm-input" value={leaveForm.end_date} onChange={(e) => setLeaveForm({ ...leaveForm, end_date: e.target.value })} data-testid="leave-end" /></label>
            </div>
            <label className="block"><span className="rm-label">{t("Alasan")}</span><textarea className="rm-input min-h-[60px]" value={leaveForm.reason} onChange={(e) => setLeaveForm({ ...leaveForm, reason: e.target.value })} data-testid="leave-reason" /></label>
            <button onClick={submitLeave} className="rm-btn-primary inline-flex items-center gap-2 text-sm" data-testid="leave-submit"><Send className="h-4 w-4" /> {t("Kirim Permohonan")}</button>
          </div>
        </div>
      )}

      {team?.rows && (
        <div className="rm-card overflow-hidden" data-testid="status-team">
          <div className="border-b border-white/5 px-5 py-3 text-sm font-bold">{t("Status Tim Hari Ini")} · {team.date}</div>
          {team.rows.map((r) => (
            <div key={r.user_id} className="flex items-center justify-between border-b border-white/5 px-5 py-2.5 text-sm last:border-0" data-testid={`team-status-${r.user_id}`}>
              <span className="truncate font-medium" translate="no">{r.name}</span>
              <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${STATUS_CLS[r.status]}`}>{t(r.status)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
