import React, { useCallback, useEffect, useState } from "react";
import { UsersRound, X, Save, Power, Wallet } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

const STATUS_BADGE = { active: "bg-emerald-500/15 text-emerald-300", inactive: "bg-zinc-500/15 text-zinc-400" };
function fmtIDR(n) { return n == null ? "—" : new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n); }

function StaffDetail({ userId, onClose, onChanged }) {
  const { t } = useAppPreferences();
  const [d, setD] = useState(null);
  const [salary, setSalary] = useState(""); const [join, setJoin] = useState(""); const [busy, setBusy] = useState(false);
  const load = useCallback(async () => { const { data } = await api.get(`/admin/staff/${userId}`); setD(data); setSalary(data.salary_idr || ""); setJoin(data.join_date || ""); }, [userId]);
  useEffect(() => { load(); }, [load]);
  const toggle = async () => { setBusy(true); try { await api.post(`/admin/staff/${userId}/employment`, { status: d.employment_status === "active" ? "inactive" : "active" }); toast.success(t("Status kerja diperbarui")); await load(); onChanged?.(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); } finally { setBusy(false); } };
  const saveSalary = async () => { setBusy(true); try { await api.post(`/admin/staff/${userId}/salary`, { salary_idr: Number(salary) || 0, join_date: join || null }); toast.success(t("Gaji pokok tersimpan")); await load(); onChanged?.(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); } finally { setBusy(false); } };
  if (!d) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/50" onClick={onClose} data-testid="staff-detail-overlay">
      <div className="h-full w-full max-w-lg overflow-y-auto bg-[#14111E] p-6" onClick={(e) => e.stopPropagation()} data-testid="staff-detail-panel">
        <div className="mb-4 flex items-start justify-between">
          <div><h2 className="font-display text-2xl font-extrabold" translate="no">{d.name}</h2><div className="text-sm text-zinc-400">{d.email} · {d.role_name}</div></div>
          <button onClick={onClose} className="rm-btn-ghost" data-testid="staff-detail-close"><X className="h-4 w-4" /></button>
        </div>
        <div className="mb-4 flex items-center gap-3">
          <span className={`rounded-full px-3 py-1 text-xs font-bold ${STATUS_BADGE[d.employment_status]}`} data-testid="staff-detail-employment">{d.employment_status === "active" ? t("Aktif") : t("Nonaktif")}</span>
          <button onClick={toggle} disabled={busy} className="rm-btn-ghost inline-flex items-center gap-2 text-sm" data-testid="staff-employment-toggle"><Power className="h-4 w-4" /> {d.employment_status === "active" ? t("Nonaktifkan") : t("Aktifkan")}</button>
        </div>
        <div className="rm-card space-y-3 p-4">
          <div className="flex items-center gap-2 text-sm font-bold"><Wallet className="h-4 w-4 text-pink-400" /> {t("Gaji Pokok")}</div>
          <div className="grid grid-cols-2 gap-3">
            <label className="block"><span className="rm-label">{t("Gaji Pokok (IDR)")}</span><input className="rm-input" type="number" value={salary} onChange={(e) => setSalary(e.target.value)} data-testid="staff-salary-input" /></label>
            <label className="block"><span className="rm-label">{t("Tanggal Bergabung")}</span><input className="rm-input" type="date" value={join} onChange={(e) => setJoin(e.target.value)} data-testid="staff-join-input" /></label>
          </div>
          <button onClick={saveSalary} disabled={busy} className="rm-btn-primary inline-flex items-center gap-2 text-sm" data-testid="staff-salary-save"><Save className="h-4 w-4" /> {t("Simpan")}</button>
          <div className="text-xs text-zinc-500">{t("Saat ini")}: <b className="text-zinc-200">{fmtIDR(d.salary_idr)}</b></div>
          {d.salary_history?.length > 0 && <div className="mt-2 border-t border-white/10 pt-2 text-xs text-zinc-500 space-y-1">{d.salary_history.map((h) => <div key={h.id}>{h.effective_date}: {fmtIDR(h.previous_idr)} → <b>{fmtIDR(h.new_idr)}</b></div>)}</div>}
        </div>
        <div className="rm-card mt-4 p-4">
          <div className="mb-2 text-sm font-bold">{t("Ringkasan Absensi (30 hari)")}</div>
          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            {Object.entries(d.attendance_summary_30d || {}).map(([k, v]) => <div key={k} className="rounded-md bg-white/[0.03] py-2" data-testid={`staff-sum-${k}`}><div className="text-lg font-bold">{v}</div><div className="text-zinc-500">{t(k)}</div></div>)}
          </div>
          <a href="/admin/attendance" className="mt-3 inline-block text-xs font-bold text-pink-300">{t("Lihat Absensi lengkap")} →</a>
        </div>
        <a href="/admin/admin-users" className="mt-4 inline-block text-xs text-zinc-400 hover:text-white" data-testid="staff-change-role-link">{t("Ubah role via Pengguna Admin")} →</a>
      </div>
    </div>
  );
}

export default function StaffManagement() {
  const { t } = useAppPreferences();
  const [rows, setRows] = useState([]); const [sel, setSel] = useState(null); const [showInactive, setShowInactive] = useState(true);
  const load = useCallback(async () => { const { data } = await api.get(`/admin/staff?include_inactive=${showInactive}`); setRows(data.staff || []); }, [showInactive]);
  useEffect(() => { load(); }, [load]);
  return (
    <div className="space-y-5" data-testid="staff-management-page">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div><div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Staff Management</div><h1 className="flex items-center gap-2 font-display text-3xl font-extrabold"><UsersRound className="h-6 w-6 text-pink-400" /> {t("Manajemen Staf")}</h1></div>
        <label className="flex items-center gap-2 text-sm text-zinc-400"><input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} className="accent-[#FF1F8E]" data-testid="staff-show-inactive" /> {t("Tampilkan nonaktif")}</label>
      </div>
      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid md:grid-cols-[2fr_1.2fr_1fr_1fr] gap-3 border-b border-white/5 bg-white/[0.03] px-5 py-3 text-[11px] font-bold uppercase tracking-widest text-zinc-500"><div>{t("Nama")}</div><div>Role</div><div>{t("Status Kerja")}</div><div className="text-right">{t("Gaji Pokok")}</div></div>
        {rows.length === 0 ? <div className="p-8 text-center text-sm text-zinc-500">{t("Belum ada staf")}</div> : rows.map((s) => (
          <button key={s.user_id} onClick={() => setSel(s.user_id)} className="grid w-full grid-cols-2 md:grid-cols-[2fr_1.2fr_1fr_1fr] items-center gap-3 border-b border-white/5 px-5 py-3 text-left text-sm last:border-0 hover:bg-white/[0.02]" data-testid={`staff-row-${s.user_id}`}>
            <div className="min-w-0"><div className="truncate font-semibold" translate="no">{s.name}</div><div className="truncate text-xs text-zinc-500">{s.email}</div></div>
            <div className="text-zinc-300">{s.role_name}</div>
            <div><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${STATUS_BADGE[s.employment_status]}`}>{s.employment_status === "active" ? t("Aktif") : t("Nonaktif")}</span></div>
            <div className="text-right font-mono">{fmtIDR(s.salary_idr)}</div>
          </button>
        ))}
      </div>
      {sel && <StaffDetail userId={sel} onClose={() => setSel(null)} onChanged={load} />}
    </div>
  );
}
