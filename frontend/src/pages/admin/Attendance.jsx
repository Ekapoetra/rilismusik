import React, { useCallback, useEffect, useState } from "react";
import { CalendarCheck, Check, X, Pencil } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

const STATUS_CLS = {
  PRESENT: "bg-emerald-500/15 text-emerald-300", LATE: "bg-amber-500/15 text-amber-300",
  ABSENT: "bg-red-500/15 text-red-300", LEAVE: "bg-sky-500/15 text-sky-300",
  HOLIDAY: "bg-zinc-500/15 text-zinc-400", NOT_RECORDED: "bg-white/5 text-zinc-500",
};
const ALL_STATUS = ["PRESENT", "LATE", "ABSENT", "LEAVE", "HOLIDAY", "NOT_RECORDED"];
const todayWIB = () => new Date(Date.now() + 7 * 3600 * 1000).toISOString().slice(0, 10);

function CorrectModal({ row, date, onClose, onDone }) {
  const { t } = useAppPreferences();
  const [status, setStatus] = useState(row.status); const [reason, setReason] = useState(""); const [busy, setBusy] = useState(false);
  const save = async () => { if (reason.trim().length < 3) { toast.error(t("Alasan wajib diisi")); return; } setBusy(true); try { await api.post(`/admin/attendance/${row.user_id}/correct`, { date, final_status: status, reason }); toast.success(t("Absensi dikoreksi")); onDone?.(); onClose(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); setBusy(false); } };
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4" onClick={onClose} data-testid="attendance-correct-modal">
      <div className="w-full max-w-md rounded-lg bg-[#14111E] p-5" onClick={(e) => e.stopPropagation()}>
        <h3 className="mb-1 font-display text-lg font-bold">{t("Koreksi Absensi")}</h3>
        <div className="mb-3 text-sm text-zinc-400" translate="no">{row.name} · {date}</div>
        <label className="block"><span className="rm-label">{t("Status akhir")}</span>
          <select className="rm-input" value={status} onChange={(e) => setStatus(e.target.value)} data-testid="correct-status-select">{ALL_STATUS.map((s) => <option key={s} value={s}>{t(s)}</option>)}</select></label>
        <label className="mt-3 block"><span className="rm-label">{t("Alasan (wajib)")}</span><textarea className="rm-input min-h-[80px]" value={reason} onChange={(e) => setReason(e.target.value)} data-testid="correct-reason-input" /></label>
        <div className="mt-4 flex gap-2"><button onClick={save} disabled={busy} className="rm-btn-primary text-sm" data-testid="correct-save-btn">{t("Simpan Koreksi")}</button><button onClick={onClose} className="rm-btn-ghost text-sm">{t("Batal")}</button></div>
      </div>
    </div>
  );
}

export default function Attendance() {
  const { t } = useAppPreferences();
  const [tab, setTab] = useState("attendance");
  const [date, setDate] = useState(todayWIB());
  const [rows, setRows] = useState([]); const [correct, setCorrect] = useState(null);
  const [leave, setLeave] = useState({ items: [], can_approve: false });
  const loadAtt = useCallback(async () => { try { const { data } = await api.get(`/admin/attendance?date=${date}`); setRows(data.rows || []); } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); } }, [date]);
  const loadLeave = useCallback(async () => { const { data } = await api.get("/admin/leave"); setLeave(data); }, []);
  useEffect(() => { if (tab === "attendance") loadAtt(); else loadLeave(); }, [tab, loadAtt, loadLeave]);
  const act = async (id, action) => { try { await api.post(`/admin/leave/${id}/action`, { action }); toast.success(t(action === "approve" ? "Cuti disetujui" : "Cuti ditolak")); await loadLeave(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); } };

  return (
    <div className="space-y-5" data-testid="attendance-page">
      <div className="border-b border-white/10 pb-4"><div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Staff Management</div><h1 className="flex items-center gap-2 font-display text-3xl font-extrabold"><CalendarCheck className="h-6 w-6 text-pink-400" /> {t("Absensi")}</h1></div>
      <div className="flex gap-2">
        <button onClick={() => setTab("attendance")} className={`rounded-full px-4 py-2 text-sm font-bold ${tab === "attendance" ? "bg-pink-500 text-white" : "bg-white/5 text-zinc-400"}`} data-testid="tab-attendance">{t("Absensi Harian")}</button>
        <button onClick={() => setTab("leave")} className={`rounded-full px-4 py-2 text-sm font-bold ${tab === "leave" ? "bg-pink-500 text-white" : "bg-white/5 text-zinc-400"}`} data-testid="tab-leave">{t("Permohonan Cuti")}</button>
      </div>

      {tab === "attendance" ? (
        <>
          <input type="date" className="rm-input w-auto" value={date} onChange={(e) => setDate(e.target.value)} data-testid="attendance-date" />
          <div className="rm-card overflow-hidden">
            {rows.length === 0 ? <div className="p-8 text-center text-sm text-zinc-500">{t("Tidak ada data")}</div> : rows.map((r) => (
              <div key={r.user_id} className="flex items-center justify-between gap-3 border-b border-white/5 px-5 py-3 last:border-0" data-testid={`attendance-row-${r.user_id}`}>
                <div className="min-w-0"><div className="truncate font-semibold" translate="no">{r.name}</div>{r.corrected && <span className="text-[10px] text-amber-300">{t("Dikoreksi dari")} {t(r.original_status)}</span>}</div>
                <div className="flex items-center gap-3">
                  <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${STATUS_CLS[r.status]}`} data-testid={`attendance-status-${r.user_id}`}>{t(r.status)}</span>
                  <button onClick={() => setCorrect(r)} className="text-zinc-500 hover:text-white" data-testid={`attendance-correct-${r.user_id}`}><Pencil className="h-4 w-4" /></button>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="rm-card overflow-hidden">
          {leave.items.length === 0 ? <div className="p-8 text-center text-sm text-zinc-500">{t("Belum ada permohonan cuti")}</div> : leave.items.map((l) => (
            <div key={l.id} className="flex items-center justify-between gap-3 border-b border-white/5 px-5 py-3 last:border-0" data-testid={`leave-row-${l.id}`}>
              <div className="min-w-0"><div className="truncate font-semibold" translate="no">{l.staff_name}</div><div className="text-xs text-zinc-500">{t(l.type)} · {l.start_date} → {l.end_date} · {l.reason}</div></div>
              <div className="flex items-center gap-2">
                <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${l.status === "approved" ? "bg-emerald-500/15 text-emerald-300" : l.status === "rejected" ? "bg-red-500/15 text-red-300" : "bg-amber-500/15 text-amber-300"}`}>{t(l.status)}</span>
                {l.status === "pending" && leave.can_approve && <><button onClick={() => act(l.id, "approve")} className="text-emerald-400" data-testid={`leave-approve-${l.id}`}><Check className="h-4 w-4" /></button><button onClick={() => act(l.id, "reject")} className="text-red-400" data-testid={`leave-reject-${l.id}`}><X className="h-4 w-4" /></button></>}
              </div>
            </div>
          ))}
        </div>
      )}
      {correct && <CorrectModal row={correct} date={date} onClose={() => setCorrect(null)} onDone={loadAtt} />}
    </div>
  );
}
