import React, { useCallback, useEffect, useState } from "react";
import { SlidersHorizontal, Save, Trash2, Plus } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

const DAYS = [["1", "Sen"], ["2", "Sel"], ["3", "Rab"], ["4", "Kam"], ["5", "Jum"], ["6", "Sab"], ["7", "Min"]];

export default function StaffConfiguration() {
  const { t } = useAppPreferences();
  const [cfg, setCfg] = useState(null);
  const [hDate, setHDate] = useState(""); const [hName, setHName] = useState("");
  const load = useCallback(async () => { const { data } = await api.get("/admin/staff/config"); setCfg(data); }, []);
  useEffect(() => { load(); }, [load]);
  if (!cfg) return <div className="text-zinc-500">{t("Memuat…")}</div>;
  const sched = cfg.schedule; const rules = cfg.rules;
  const setSched = (k, v) => setCfg((c) => ({ ...c, schedule: { ...c.schedule, [k]: v } }));
  const setRule = (k, v) => setCfg((c) => ({ ...c, rules: { ...c.rules, [k]: v } }));
  const toggleDay = (d) => setSched("working_days", sched.working_days.includes(Number(d)) ? sched.working_days.filter((x) => x !== Number(d)) : [...sched.working_days, Number(d)].sort());
  const save = async (section, value) => { try { await api.put("/admin/staff/config", { section, value }); toast.success(t("Konfigurasi tersimpan")); await load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); } };
  const addHoliday = async () => { if (!hDate || !hName) return; try { await api.post("/admin/staff/config/holidays", { date: hDate, name: hName }); setHDate(""); setHName(""); await load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); } };
  const delHoliday = async (d) => { try { await api.delete(`/admin/staff/config/holidays/${d}`); await load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); } };

  return (
    <div className="max-w-3xl space-y-5" data-testid="staff-config-page">
      <div className="border-b border-white/10 pb-4"><div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Staff Management</div><h1 className="flex items-center gap-2 font-display text-3xl font-extrabold"><SlidersHorizontal className="h-6 w-6 text-pink-400" /> {t("Konfigurasi Absensi")}</h1></div>

      <section className="rm-card space-y-3 p-5" data-testid="config-schedule">
        <div className="text-sm font-bold">{t("Jadwal Kerja")}</div>
        <div className="flex flex-wrap gap-2">{DAYS.map(([d, lbl]) => <button key={d} onClick={() => toggleDay(d)} className={`rounded-full px-3 py-1.5 text-xs font-bold ${sched.working_days.includes(Number(d)) ? "bg-pink-500 text-white" : "bg-white/5 text-zinc-400"}`} data-testid={`config-day-${d}`}>{t(lbl)}</button>)}</div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[["start", "Mulai"], ["end", "Selesai"], ["break_start", "Istirahat Mulai"], ["break_end", "Istirahat Selesai"]].map(([k, lbl]) => <label key={k} className="block"><span className="rm-label">{t(lbl)}</span><input type="time" className="rm-input" value={sched[k] || ""} onChange={(e) => setSched(k, e.target.value)} data-testid={`config-${k}`} /></label>)}
        </div>
        <button onClick={() => save("schedule", sched)} className="rm-btn-primary inline-flex items-center gap-2 text-sm" data-testid="config-schedule-save"><Save className="h-4 w-4" /> {t("Simpan Jadwal")}</button>
      </section>

      <section className="rm-card space-y-3 p-5" data-testid="config-rules">
        <div className="text-sm font-bold">{t("Aturan Absensi")}</div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <label className="block"><span className="rm-label">{t("Toleransi Terlambat (menit)")}</span><input type="number" className="rm-input" value={rules.grace_minutes} onChange={(e) => setRule("grace_minutes", Number(e.target.value))} data-testid="config-grace" /></label>
          <label className="block"><span className="rm-label">{t("Cutoff Harian")}</span><input type="time" className="rm-input" value={rules.cutoff} onChange={(e) => setRule("cutoff", e.target.value)} data-testid="config-cutoff" /></label>
          <label className="block"><span className="rm-label">{t("Awal Jendela Bukti")}</span><input type="time" className="rm-input" value={rules.evidence_start} onChange={(e) => setRule("evidence_start", e.target.value)} data-testid="config-evidence-start" /></label>
        </div>
        <p className="text-xs text-zinc-500">{t("Perubahan tidak menghitung ulang absensi historis yang sudah final.")}</p>
        <button onClick={() => save("rules", rules)} className="rm-btn-primary inline-flex items-center gap-2 text-sm" data-testid="config-rules-save"><Save className="h-4 w-4" /> {t("Simpan Aturan")}</button>
      </section>

      <section className="rm-card space-y-3 p-5" data-testid="config-holidays">
        <div className="text-sm font-bold">{t("Kalender Libur")}</div>
        <div className="flex flex-wrap items-end gap-2">
          <label className="block"><span className="rm-label">{t("Tanggal")}</span><input type="date" className="rm-input" value={hDate} onChange={(e) => setHDate(e.target.value)} data-testid="holiday-date" /></label>
          <label className="block flex-1"><span className="rm-label">{t("Nama Libur")}</span><input className="rm-input" value={hName} onChange={(e) => setHName(e.target.value)} data-testid="holiday-name" /></label>
          <button onClick={addHoliday} className="rm-btn-ghost inline-flex items-center gap-1 text-sm" data-testid="holiday-add"><Plus className="h-4 w-4" /> {t("Tambah")}</button>
        </div>
        <div className="divide-y divide-white/5">{(cfg.holidays || []).map((h) => <div key={h.date} className="flex items-center justify-between py-2 text-sm" data-testid={`holiday-${h.date}`}><span>{h.date} · {h.name}</span><button onClick={() => delHoliday(h.date)} className="text-red-400"><Trash2 className="h-4 w-4" /></button></div>)}</div>
      </section>

      <section className="rm-card space-y-3 p-5" data-testid="config-leave">
        <div className="text-sm font-bold">{t("Pengaturan Cuti")}</div>
        <label className="block"><span className="rm-label">{t("Jenis cuti (pisahkan dengan koma)")}</span><input className="rm-input" defaultValue={(cfg.leave_settings?.types || []).join(", ")} onBlur={(e) => save("leave_settings", { types: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })} data-testid="config-leave-types" /></label>
      </section>
    </div>
  );
}
