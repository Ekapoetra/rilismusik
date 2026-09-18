import React, { useCallback, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { Receipt, UsersRound, Coins, Percent, PlusCircle, Download, Trash2 } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { useAuth } from "@/api/AuthContext";
import { downloadPayslip } from "@/api/payslip";

const fmtIDR = (n) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
const roleLabel = (r) => (r || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
const STATUS_PILL = { draft: "bg-zinc-500/20 text-zinc-300", review: "bg-amber-500/15 text-amber-300", approved: "bg-sky-500/15 text-sky-300", paid: "bg-emerald-500/15 text-emerald-300", finalized: "bg-violet-500/20 text-violet-300" };
const TABS = [
  ["payroll", "Payroll", Receipt, "compensation.payroll.view"],
  ["staff", "Staf", UsersRound, "compensation.view_team"],
  ["bonus", "Bonus", Coins, "compensation.bonus.transactions.view"],
  ["rules", "Aturan Bonus", Percent, "compensation.bonus.rules.manage"],
  ["adjustments", "Penyesuaian", PlusCircle, "compensation.adjustment.create"],
];
const PATH_TAB = { "/admin/compensation/payroll": "payroll", "/admin/compensation/staff": "staff", "/admin/compensation/bonus": "bonus", "/admin/compensation/bonus-rules": "rules", "/admin/compensation/adjustments": "adjustments" };

export default function CompensationAdmin() {
  const { hasPermission } = useAuth();
  const loc = useLocation();
  const [tab, setTab] = useState(PATH_TAB[loc.pathname] || "payroll");
  useEffect(() => { setTab(PATH_TAB[loc.pathname] || "payroll"); }, [loc.pathname]);
  const visible = TABS.filter(([, , , p]) => hasPermission(p));
  return (
    <div className="space-y-6" data-testid="compensation-admin-page">
      <header><h1 className="font-display text-2xl font-extrabold">Kompensasi & Payroll</h1><p className="text-sm text-zinc-400">Gaji, tunjangan, bonus penjualan, penyesuaian, dan payroll bulanan.</p></header>
      <div className="flex flex-wrap gap-2">
        {visible.map(([k, label, Icon]) => (
          <button key={k} onClick={() => setTab(k)} className={`inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-semibold ${tab === k ? "bg-white/10 text-white" : "text-zinc-400"}`} data-testid={`compadmin-tab-${k}`}><Icon className="h-4 w-4" />{label}</button>
        ))}
      </div>
      {tab === "payroll" && <PayrollTab />}
      {tab === "staff" && <StaffTab />}
      {tab === "bonus" && <BonusPreviewTab />}
      {tab === "rules" && <SchemesTab />}
      {tab === "adjustments" && <AdjustmentsTab />}
    </div>
  );
}

function PayrollTab() {
  const [periods, setPeriods] = useState([]);
  const [open, setOpen] = useState(null);
  const [pk, setPk] = useState("");
  const load = useCallback(() => api.get("/compensation/payroll/periods").then((r) => setPeriods(r.data.periods || [])).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  const openPeriod = (id) => api.get(`/compensation/payroll/periods/${id}`).then((r) => setOpen(r.data)).catch(() => {});
  const create = async () => { try { await api.post("/compensation/payroll/periods", { period_key: pk }); toast.success("Periode dibuat"); setPk(""); load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e.message)); } };
  const act = async (id, fn) => { try { await fn(); toast.success("Berhasil"); load(); if (open?.period?.id === id) openPeriod(id); } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e.message)); } };
  return (
    <div className="space-y-4">
      <div className="rm-glass flex items-end gap-3 rounded-2xl p-4">
        <label className="text-xs font-semibold text-zinc-400">Periode (YYYY-MM)<input value={pk} onChange={(e) => setPk(e.target.value)} placeholder="2026-09" className="rm-input mt-1 block w-40" data-testid="payroll-period-input" /></label>
        <button onClick={create} className="rm-btn-primary" data-testid="payroll-create-btn">Buat Periode</button>
      </div>
      <div className="grid gap-2" data-testid="payroll-periods">
        {periods.map((p) => (
          <div key={p.id} className="rm-glass rounded-2xl p-4" data-testid={`payroll-period-${p.period_key}`}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3"><span className="font-display text-lg font-bold">{p.period_key}</span><span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${STATUS_PILL[p.status]}`}>{p.status}</span></div>
              <div className="flex items-center gap-3"><span className="text-sm tabular-nums">{fmtIDR(p.totals?.net_total_idr)} • {p.totals?.staff_count || 0} staf</span><button onClick={() => openPeriod(p.id)} className="rm-btn-ghost text-xs" data-testid={`payroll-open-${p.period_key}`}>Lihat</button></div>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              {(p.status === "draft" || p.status === "review") && <button onClick={() => act(p.id, () => api.post(`/compensation/payroll/periods/${p.id}/generate`))} className="rm-btn-ghost text-xs" data-testid={`payroll-generate-${p.period_key}`}>Hitung Ulang</button>}
              {p.status === "draft" && <button onClick={() => act(p.id, () => api.post(`/compensation/payroll/periods/${p.id}/transition`, { to: "review" }))} className="rm-btn-ghost text-xs">→ Review</button>}
              {p.status === "review" && <button onClick={() => act(p.id, () => api.post(`/compensation/payroll/periods/${p.id}/transition`, { to: "approved" }))} className="rm-btn-ghost text-xs">→ Setujui</button>}
              {p.status === "approved" && <button onClick={() => act(p.id, () => api.post(`/compensation/payroll/periods/${p.id}/transition`, { to: "paid" }))} className="rm-btn-ghost text-xs">→ Tandai Dibayar</button>}
              {p.status === "paid" && <button onClick={() => act(p.id, () => api.post(`/compensation/payroll/periods/${p.id}/transition`, { to: "finalized" }))} className="rm-btn-primary text-xs" data-testid={`payroll-finalize-${p.period_key}`}>Finalisasi</button>}
            </div>
          </div>
        ))}
        {!periods.length && <div className="rm-glass rounded-2xl p-6 text-center text-sm text-zinc-400">Belum ada periode payroll.</div>}
      </div>
      {open && (
        <div className="rm-glass rounded-2xl p-4" data-testid="payroll-detail">
          <div className="mb-2 flex items-center gap-2 text-sm font-bold">Rincian {open.period.period_key}{open.period.status === "finalized" && <span className="rounded-full bg-violet-500/20 px-2 py-0.5 text-[10px] font-bold uppercase text-violet-300">final</span>}</div>
          <div className="overflow-auto">
            <table className="w-full text-sm"><thead><tr className="text-left text-xs uppercase text-zinc-500"><th className="py-1">Staf</th><th>Gaji</th><th>Tunjangan</th><th>Bonus</th><th>Penyesuaian</th><th className="text-right">Net</th>{open.period.status === "finalized" && <th className="text-right">Slip</th>}</tr></thead>
              <tbody>{open.items.map((it) => (<tr key={it.id} className="border-t border-white/5" data-testid={`payroll-item-${it.staff_user_id}`}><td className="py-1.5">{it.staff_name}{it.needs_review && <span className="ml-1 text-[10px] text-amber-400">⚠ review</span>}</td><td className="tabular-nums">{fmtIDR(it.salary_idr)}</td><td className="tabular-nums">{fmtIDR(it.allowance_idr)}</td><td className="tabular-nums">{fmtIDR(it.bonus_idr)}</td><td className="tabular-nums">{fmtIDR(it.adjustment_idr)}</td><td className="text-right font-bold tabular-nums">{fmtIDR(it.net_payable_idr)}</td>{open.period.status === "finalized" && <td className="text-right"><button onClick={() => downloadPayslip(open.period.id, it.staff_user_id).catch((e) => toast.error(formatApiError(e.response?.data?.detail || e.message)))} className="inline-flex items-center gap-1 rounded-full bg-white/10 px-2.5 py-1 text-xs font-semibold text-white transition-colors hover:bg-white/20" data-testid={`payslip-admin-download-${it.staff_user_id}`}><Download className="h-3.5 w-3.5" />Slip</button></td>}</tr>))}</tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function StaffTab() {
  const [staff, setStaff] = useState([]);
  const [sel, setSel] = useState(null);
  const [salary, setSalary] = useState({ new_idr: "", effective_date: "", reason: "" });
  const [allow, setAllow] = useState({ name: "", amount_idr: "", effective_from: "" });
  const load = useCallback(() => api.get("/compensation/staff").then((r) => setStaff(r.data.staff || [])).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  const saveSalary = async () => { try { await api.post("/compensation/salary", { staff_user_id: sel, new_idr: Number(salary.new_idr), effective_date: salary.effective_date, reason: salary.reason }); toast.success("Gaji diperbarui"); setSalary({ new_idr: "", effective_date: "", reason: "" }); load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e.message)); } };
  const saveAllow = async () => { try { await api.post("/compensation/allowances", { staff_user_id: sel, name: allow.name, amount_idr: Number(allow.amount_idr), effective_from: allow.effective_from }); toast.success("Tunjangan ditambah"); setAllow({ name: "", amount_idr: "", effective_from: "" }); } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e.message)); } };
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="rm-glass rounded-2xl p-4" data-testid="staff-comp-list">
        <div className="mb-2 text-sm font-bold">Staf ({staff.length})</div>
        <div className="max-h-[420px] space-y-1 overflow-auto">
          {staff.map((s) => (
            <button key={s.user_id} onClick={() => setSel(s.user_id)} className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm ${sel === s.user_id ? "bg-white/10" : "hover:bg-white/5"}`} data-testid={`staff-row-${s.user_id}`}>
              <span className="min-w-0 truncate">{s.name} <span className="text-xs text-zinc-500">{s.email}</span></span>
              <span className="tabular-nums text-zinc-400">{fmtIDR(s.salary_idr)}{s.allowance_idr ? ` +${fmtIDR(s.allowance_idr)}` : ""}</span>
            </button>
          ))}
        </div>
      </div>
      <div className="space-y-4">
        <div className="rm-glass rounded-2xl p-4">
          <div className="mb-2 text-sm font-bold">Ubah Gaji {sel ? "" : "(pilih staf)"}</div>
          <div className="grid gap-2">
            <input disabled={!sel} value={salary.new_idr} onChange={(e) => setSalary({ ...salary, new_idr: e.target.value })} placeholder="Gaji baru (IDR)" className="rm-input" data-testid="salary-amount" />
            <input disabled={!sel} type="date" value={salary.effective_date} onChange={(e) => setSalary({ ...salary, effective_date: e.target.value })} className="rm-input" data-testid="salary-effective" />
            <input disabled={!sel} value={salary.reason} onChange={(e) => setSalary({ ...salary, reason: e.target.value })} placeholder="Alasan" className="rm-input" />
            <button disabled={!sel} onClick={saveSalary} className="rm-btn-primary disabled:opacity-40" data-testid="salary-save">Simpan Gaji</button>
          </div>
        </div>
        <div className="rm-glass rounded-2xl p-4">
          <div className="mb-2 text-sm font-bold">Tunjangan Cepat</div>
          <div className="grid gap-2">
            <input disabled={!sel} value={allow.name} onChange={(e) => setAllow({ ...allow, name: e.target.value })} placeholder="Nama (Transport / Makan)" className="rm-input" data-testid="allow-name" />
            <input disabled={!sel} value={allow.amount_idr} onChange={(e) => setAllow({ ...allow, amount_idr: e.target.value })} placeholder="Jumlah (IDR)" className="rm-input" data-testid="allow-amount" />
            <input disabled={!sel} type="date" value={allow.effective_from} onChange={(e) => setAllow({ ...allow, effective_from: e.target.value })} className="rm-input" data-testid="allow-effective" />
            <button disabled={!sel} onClick={saveAllow} className="rm-btn-primary disabled:opacity-40" data-testid="allow-save">Tambah Tunjangan</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function BonusPreviewTab() {
  const now = new Date();
  const [pk, setPk] = useState(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const load = useCallback((key) => {
    setLoading(true);
    api.get(`/compensation/bonus/preview?period_key=${key}`).then((r) => setData(r.data)).catch((e) => { setData(null); toast.error(formatApiError(e.response?.data?.detail || e.message)); }).finally(() => setLoading(false));
  }, []);
  useEffect(() => { load(pk); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div className="space-y-4" data-testid="bonus-preview-tab">
      <div className="rm-glass flex flex-wrap items-end gap-3 rounded-2xl p-4">
        <label className="text-xs font-semibold text-zinc-400">Periode (YYYY-MM)<input value={pk} onChange={(e) => setPk(e.target.value)} placeholder="2026-06" className="rm-input mt-1 block w-40" data-testid="bonus-preview-period" /></label>
        <button onClick={() => load(pk)} className="rm-btn-primary" data-testid="bonus-preview-load">Hitung</button>
      </div>
      {data && (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rm-glass rounded-2xl p-5"><div className="text-[11px] font-bold uppercase tracking-widest text-zinc-500">Total Pendapatan Xendit ({data.period_key})</div><div className="mt-1 font-display text-2xl font-extrabold tabular-nums" data-testid="bonus-preview-revenue">{fmtIDR(data.revenue_idr)}</div><div className="mt-1 text-xs text-zinc-500">Submit, subscription, WAMI & layanan tambahan yang dibayar bulan ini.</div></div>
            <div className="rm-glass rounded-2xl p-5"><div className="text-[11px] font-bold uppercase tracking-widest text-zinc-500">Total Bonus Semua Staf</div><div className="mt-1 font-display text-2xl font-extrabold rm-gradient-text tabular-nums">{fmtIDR(data.total_bonus_idr)}</div><div className="mt-1 text-xs text-zinc-500">{data.items?.length || 0} staf menerima bonus.</div></div>
          </div>
          <div className="rm-glass rounded-2xl p-4">
            <div className="mb-2 text-sm font-bold">Bonus per Staf</div>
            {(!data.items || !data.items.length) ? <p className="text-sm text-zinc-500">Belum ada skema aktif atau tidak ada staf yang memenuhi periode ini.</p> : (
              <div className="overflow-auto"><table className="w-full text-sm"><thead><tr className="text-left text-xs uppercase text-zinc-500"><th className="py-1">Staf</th><th>Role</th><th>Skema</th><th className="text-right">Bonus</th></tr></thead>
                <tbody>{data.items.map((it) => (<tr key={it.staff_user_id} className="border-t border-white/5" data-testid={`bonus-preview-item-${it.staff_user_id}`}><td className="py-1.5">{it.name}</td><td className="text-zinc-400">{roleLabel(it.role)}</td><td className="text-xs text-zinc-500">{(it.breakdown || []).map((b) => b.calc_mode === "tiered" ? `${b.scheme_name} (bertingkat)` : `${b.scheme_name} (${b.percent}%)`).join(", ")}</td><td className="text-right font-bold tabular-nums">{fmtIDR(it.bonus_idr)}</td></tr>))}</tbody>
              </table></div>
            )}
          </div>
        </>
      )}
      {loading && !data && <p className="text-sm text-zinc-500">Memuat…</p>}
    </div>
  );
}

function SchemesTab() {
  const [schemes, setSchemes] = useState([]);
  const [roles, setRoles] = useState([]);
  const [staff, setStaff] = useState([]);
  const [form, setForm] = useState({ name: "", scope: "all", role_key: "", staff_user_id: "", calc_mode: "flat", percent: "", tiers: [{ up_to: "", percent: "" }], lifetime: true, effective_from: "", effective_to: "" });
  const load = useCallback(() => {
    api.get("/compensation/bonus/schemes").then((r) => setSchemes(r.data.schemes || [])).catch(() => {});
    api.get("/compensation/staff").then((r) => { const s = r.data.staff || []; setStaff(s); setRoles([...new Set(s.map((x) => x.role).filter(Boolean))]); }).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);
  const setTier = (i, key, val) => setForm((f) => ({ ...f, tiers: f.tiers.map((t, j) => (j === i ? { ...t, [key]: val } : t)) }));
  const addTier = () => setForm((f) => ({ ...f, tiers: [...f.tiers, { up_to: "", percent: "" }] }));
  const removeTier = (i) => setForm((f) => ({ ...f, tiers: f.tiers.filter((_, j) => j !== i) }));
  const create = async () => {
    try {
      const payload = { name: form.name, scope: form.scope, calc_mode: form.calc_mode,
        role_key: form.scope === "role" ? form.role_key : null, staff_user_id: form.scope === "staff" ? form.staff_user_id : null,
        effective_from: form.lifetime ? null : (form.effective_from || null), effective_to: form.lifetime ? null : (form.effective_to || null) };
      if (form.calc_mode === "tiered") {
        payload.tiers = form.tiers.filter((t) => t.percent !== "").map((t) => ({ up_to: t.up_to === "" ? null : Number(t.up_to), percent: Number(t.percent) }));
      } else {
        payload.percent = Number(form.percent);
      }
      await api.post("/compensation/bonus/schemes", payload);
      toast.success("Skema bonus dibuat");
      setForm({ name: "", scope: "all", role_key: "", staff_user_id: "", calc_mode: "flat", percent: "", tiers: [{ up_to: "", percent: "" }], lifetime: true, effective_from: "", effective_to: "" });
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e.message)); }
  };
  const toggle = async (s) => { try { await api.patch(`/compensation/bonus/schemes/${s.id}`, { active: !s.active }); load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e.message)); } };
  const remove = async (id) => { try { await api.delete(`/compensation/bonus/schemes/${id}`); toast.success("Skema dinonaktifkan"); load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e.message)); } };
  const scopeText = (s) => s.scope === "all" ? "Semua Staf" : s.scope === "role" ? `Role: ${roleLabel(s.role_key)}` : `Staf: ${(staff.find((x) => x.user_id === s.staff_user_id) || {}).name || s.staff_user_id}`;
  const periodText = (s) => (!s.effective_from && !s.effective_to) ? "Lifetime" : `${s.effective_from || "—"} s/d ${s.effective_to || "seterusnya"}`;
  const rateText = (s) => s.calc_mode === "tiered"
    ? (s.tiers || []).map((t) => `${t.percent}% ${t.up_to ? `s/d ${fmtIDR(t.up_to)}` : "di atasnya"}`).join(" · ")
    : `${s.percent}%`;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="rm-glass rounded-2xl p-4" data-testid="schemes-list">
        <div className="mb-2 text-sm font-bold">Skema Bonus</div>
        <p className="mb-3 text-xs text-zinc-500">Bonus = persentase × total pendapatan Xendit bulan itu. Tiap staf yang cocok menerima persentase penuh (tidak dibagi). Mode bertingkat dihitung marginal per lapisan pendapatan.</p>
        {schemes.map((s) => (
          <div key={s.id} className="flex items-center justify-between border-b border-white/5 py-2 text-sm last:border-0" data-testid={`scheme-${s.id}`}>
            <div className="min-w-0">
              <div className="font-semibold">{s.name} <span className="rm-gradient-text font-bold">{s.calc_mode === "tiered" ? "Bertingkat" : `${s.percent}%`}</span></div>
              <div className="text-xs text-zinc-500">{scopeText(s)} • {periodText(s)}{!s.active && " • nonaktif"}</div>
              {s.calc_mode === "tiered" && <div className="text-[11px] text-zinc-500">{rateText(s)}</div>}
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => toggle(s)} className="rm-btn-ghost text-xs" data-testid={`scheme-toggle-${s.id}`}>{s.active ? "Nonaktifkan" : "Aktifkan"}</button>
              <button onClick={() => remove(s.id)} className="rounded-lg p-1.5 text-zinc-400 transition-colors hover:bg-white/10 hover:text-red-300" data-testid={`scheme-delete-${s.id}`}><Trash2 className="h-4 w-4" /></button>
            </div>
          </div>
        ))}
        {!schemes.length && <p className="text-sm text-zinc-500">Belum ada skema.</p>}
      </div>
      <div className="rm-glass rounded-2xl p-4">
        <div className="mb-2 text-sm font-bold">Tambah Skema</div>
        <div className="grid gap-2">
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Nama skema (mis. Bonus Tim Finance)" className="rm-input" data-testid="scheme-name" />
          <label className="text-xs font-semibold text-zinc-400">Cakupan
            <select value={form.scope} onChange={(e) => setForm({ ...form, scope: e.target.value })} className="rm-input mt-1 block w-full" data-testid="scheme-scope"><option value="all">Semua Staf</option><option value="role">Role Tertentu</option><option value="staff">Staf Tertentu</option></select>
          </label>
          {form.scope === "role" && (
            <select value={form.role_key} onChange={(e) => setForm({ ...form, role_key: e.target.value })} className="rm-input" data-testid="scheme-role"><option value="" disabled>Pilih role…</option>{roles.map((r) => <option key={r} value={r}>{roleLabel(r)}</option>)}</select>
          )}
          {form.scope === "staff" && (
            <select value={form.staff_user_id} onChange={(e) => setForm({ ...form, staff_user_id: e.target.value })} className="rm-input" data-testid="scheme-staff"><option value="" disabled>Pilih staf…</option>{staff.map((s) => <option key={s.user_id} value={s.user_id}>{s.name}</option>)}</select>
          )}
          <label className="text-xs font-semibold text-zinc-400">Mode bonus
            <select value={form.calc_mode} onChange={(e) => setForm({ ...form, calc_mode: e.target.value })} className="rm-input mt-1 block w-full" data-testid="scheme-mode"><option value="flat">Persen Tunggal</option><option value="tiered">Bertingkat (marginal)</option></select>
          </label>
          {form.calc_mode === "flat" ? (
            <label className="text-xs font-semibold text-zinc-400">Persentase dari total pendapatan
              <input value={form.percent} onChange={(e) => setForm({ ...form, percent: e.target.value })} placeholder="mis. 5" className="rm-input mt-1 block w-full" data-testid="scheme-percent" />
            </label>
          ) : (
            <div className="rounded-xl border border-white/10 p-3" data-testid="scheme-tiers">
              <div className="mb-1 text-xs font-semibold text-zinc-400">Tingkatan (marginal). Kosongkan "sampai" pada baris terakhir = tanpa batas.</div>
              {form.tiers.map((t, i) => (
                <div key={i} className="mb-2 grid grid-cols-[1fr_5rem_auto] items-center gap-2">
                  <input value={t.up_to} onChange={(e) => setTier(i, "up_to", e.target.value)} placeholder="sampai (IDR)" className="rm-input" data-testid={`tier-upto-${i}`} />
                  <input value={t.percent} onChange={(e) => setTier(i, "percent", e.target.value)} placeholder="%" className="rm-input" data-testid={`tier-percent-${i}`} />
                  {form.tiers.length > 1
                    ? <button onClick={() => removeTier(i)} className="rounded-lg p-1.5 text-zinc-400 hover:bg-white/10 hover:text-red-300" data-testid={`tier-remove-${i}`}><Trash2 className="h-4 w-4" /></button>
                    : <span className="w-7" />}
                </div>
              ))}
              <button onClick={addTier} className="rm-btn-ghost text-xs" data-testid="tier-add">+ Tambah Tingkatan</button>
            </div>
          )}
          <label className="flex items-center gap-2 text-sm text-zinc-300"><input type="checkbox" checked={form.lifetime} onChange={(e) => setForm({ ...form, lifetime: e.target.checked })} data-testid="scheme-lifetime" />Berlaku lifetime (selamanya)</label>
          {!form.lifetime && (
            <div className="flex gap-2">
              <label className="flex-1 text-xs font-semibold text-zinc-400">Mulai<input type="date" value={form.effective_from} onChange={(e) => setForm({ ...form, effective_from: e.target.value })} className="rm-input mt-1 block w-full" data-testid="scheme-from" /></label>
              <label className="flex-1 text-xs font-semibold text-zinc-400">Sampai (opsional)<input type="date" value={form.effective_to} onChange={(e) => setForm({ ...form, effective_to: e.target.value })} className="rm-input mt-1 block w-full" data-testid="scheme-to" /></label>
            </div>
          )}
          <button onClick={create} className="rm-btn-primary" data-testid="scheme-create">Simpan Skema</button>
        </div>
      </div>
    </div>
  );
}

function AdjustmentsTab() {
  const { hasPermission } = useAuth();
  const [rows, setRows] = useState([]);
  const [staff, setStaff] = useState([]);
  const [form, setForm] = useState({ staff_user_id: "", period_key: "", amount_idr: "", reason: "" });
  const load = useCallback(() => { api.get("/compensation/adjustments").then((r) => setRows(r.data.adjustments || [])).catch(() => {}); api.get("/compensation/staff").then((r) => setStaff(r.data.staff || [])).catch(() => {}); }, []);
  useEffect(() => { load(); }, [load]);
  const create = async () => { try { await api.post("/compensation/adjustments", { ...form, amount_idr: Number(form.amount_idr) }); toast.success("Penyesuaian dibuat"); setForm({ staff_user_id: "", period_key: "", amount_idr: "", reason: "" }); load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e.message)); } };
  const approve = async (id) => { try { await api.post(`/compensation/adjustments/${id}/approve`); toast.success("Disetujui"); load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e.message)); } };
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="rm-glass rounded-2xl p-4" data-testid="adjustments-list">
        <div className="mb-2 text-sm font-bold">Penyesuaian</div>
        {rows.map((a) => (<div key={a.id} className="flex items-center justify-between border-b border-white/5 py-2 text-sm last:border-0"><span>{a.period_key} • <span className={a.amount_idr < 0 ? "text-red-300" : "text-emerald-300"}>{fmtIDR(a.amount_idr)}</span> <span className="text-xs text-zinc-500">{a.reason}</span></span><span className="flex items-center gap-2"><span className="text-xs">{a.status}</span>{a.status === "pending" && hasPermission("compensation.adjustment.approve") && <button onClick={() => approve(a.id)} className="rm-btn-ghost text-xs" data-testid={`adj-approve-${a.id}`}>Setujui</button>}</span></div>))}
        {!rows.length && <p className="text-sm text-zinc-500">Belum ada penyesuaian.</p>}
      </div>
      <div className="rm-glass rounded-2xl p-4">
        <div className="mb-2 text-sm font-bold">Buat Penyesuaian</div>
        <div className="grid gap-2">
          <select value={form.staff_user_id} onChange={(e) => setForm({ ...form, staff_user_id: e.target.value })} className="rm-input" data-testid="adj-staff"><option value="" disabled>Pilih staf…</option>{staff.map((s) => <option key={s.user_id} value={s.user_id}>{s.name}</option>)}</select>
          <input value={form.period_key} onChange={(e) => setForm({ ...form, period_key: e.target.value })} placeholder="Periode (2026-09)" className="rm-input" data-testid="adj-period" />
          <input value={form.amount_idr} onChange={(e) => setForm({ ...form, amount_idr: e.target.value })} placeholder="Jumlah (+/- IDR)" className="rm-input" data-testid="adj-amount" />
          <input value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} placeholder="Alasan" className="rm-input" data-testid="adj-reason" />
          <button onClick={create} className="rm-btn-primary" data-testid="adj-create">Simpan</button>
        </div>
      </div>
    </div>
  );
}
