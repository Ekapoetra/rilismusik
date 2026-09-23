import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, CalendarDays, ClipboardCheck, RefreshCw, Send, Sparkles, Wallet } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { useV7Resource } from "@/components/admin/v7/useV7Resource";
import { Panel, MoreLink, ResourceState, number, dateWib, timeWib, monthWib } from "@/components/admin/v7/V7Primitives";

const STATUS = { PRESENT: "Hadir", LATE: "Terlambat", ABSENT: "Tidak hadir", LEAVE: "Cuti / izin", HOLIDAY: "Libur", NOT_RECORDED: "Belum tercatat" };
const LEAVE_STATUS = { pending: "Menunggu persetujuan", approved: "Disetujui", rejected: "Ditolak" };
const BLANK_LEAVE = { type: "annual", start_date: "", end_date: "", reason: "" };
function AttendanceBadge({ status }) { return <span className={`v7-badge ${status === "LATE" || status === "ABSENT" ? "is-waiting" : ""}`}>{STATUS[status] || status || "Belum tercatat"}</span>; }

export default function V7StaffOverview() {
  const { user, hasPermission } = useAuth();
  const canTeam = hasPermission("staff.attendance.view");
  const canPerformance = hasPermission("performance.view_team");
  const [period, setPeriod] = useState(monthWib);
  const me = useV7Resource(canTeam ? null : "/admin/status/me");
  const team = useV7Resource(canTeam ? "/admin/status/team" : null);
  const performance = useV7Resource(canPerformance ? `/admin/performance/overview?period=${period}` : hasPermission("performance.view_own") ? `/admin/performance/me?period=${period}` : null);
  const leave = useV7Resource("/admin/leave");
  const [form, setForm] = useState(BLANK_LEAVE);
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState(null);
  const scores = (performance.data?.rows || []).map(row => row.overall_score).filter(value => typeof value === "number" && Number.isFinite(value));
  const score = canPerformance ? scores.length ? scores.reduce((sum, value) => sum + value, 0) / scores.length : null : performance.data?.overall_score;
  const links = [
    ["staff.view", "/admin/staff", "Manajemen Staff", "Profil dan penugasan", ClipboardCheck],
    ["staff.attendance.view", "/admin/attendance", "Absensi", "Riwayat dan koreksi status", CalendarDays],
    ["compensation.view_own", "/admin/compensation/me", "Kompensasi Saya", "Rincian dan slip gaji", Wallet],
    ["compensation.payroll.view", "/admin/compensation/payroll", "Payroll", "Periode dan pembayaran", Wallet],
    ["staff.config.manage", "/admin/staff/configuration", "Aturan Kerja", "Jadwal dan kebijakan", ClipboardCheck],
    ["performance.config.manage", "/admin/performance/configuration", "Konfigurasi KPI", "Bobot dan target kinerja", Sparkles],
  ].filter(([permission]) => hasPermission(permission));
  const submit = async event => {
    event.preventDefault();
    if (sending) return;
    const submitted = Object.fromEntries(new FormData(event.currentTarget));
    if (!submitted.start_date || !submitted.end_date || submitted.end_date < submitted.start_date || submitted.reason.trim().length < 3) { setNotice({ error: true, text: "Periksa rentang tanggal dan isi alasan minimal 3 karakter." }); return; }
    setSending(true); setNotice(null);
    try { await api.post("/admin/leave", { ...submitted, reason: submitted.reason.trim() }); setForm(BLANK_LEAVE); setNotice({ text: "Permohonan berhasil dikirim untuk persetujuan." }); leave.reload(); }
    catch (error) { setNotice({ error: true, text: formatApiError(error.response?.data?.detail) }); }
    finally { setSending(false); }
  };
  return <div className="v7-page" data-testid="v7-staff-overview">
    <div className="v7-heading"><div><div className="v7-eyebrow">WORKSPACE / STAFF</div><h1>{canTeam ? "Overview Staff" : `Halo, ${user?.name || "Tim Rilis Musik"}.`}</h1><p>Kehadiran, kinerja, dan kebutuhan kerja dalam satu tempat.</p></div><div className="v7-date"><CalendarDays size={15} />{dateWib(new Date())}<small>Waktu Indonesia Barat</small></div></div>
    <div className="v7-focus"><span className="v7-dot" /><div><strong>Ruang kerja untuk tim yang terus bergerak.</strong><small>Gunakan catatan kehadiran dan hasil pekerjaan untuk meninjau aktivitasmu.</small></div><button className="v7-icon-btn" aria-label="Perbarui data staff" onClick={() => { me.reload(); team.reload(); performance.reload(); leave.reload(); }}><RefreshCw size={16} /></button></div>
    {canTeam && <ResourceState resource={team}><div className="v7-stat-grid is-four">{[["Total Staff", team.data?.rows.length, "Staff dalam daftar kehadiran"], ["Hadir", team.data?.rows.filter(row => ["PRESENT", "LATE"].includes(row.status)).length, "Termasuk yang terlambat"], ["Terlambat", team.data?.rows.filter(row => row.status === "LATE").length, "Berdasarkan aturan kerja"], ["Cuti / Izin", team.data?.rows.filter(row => row.status === "LEAVE").length, "Status kehadiran hari ini"]].map(([label, value, hint], index) => <div className={`v7-stat ${index === 0 ? "is-featured" : ""}`} key={label}><span>{label}</span><strong>{number(value)}</strong><small>{hint}</small></div>)}</div></ResourceState>}
    <div className="v7-staff-grid">
      <div className="v7-stack">
        {canTeam ? <Panel title="Kehadiran Hari Ini" subtitle="Bukti waktu menggunakan login pertama yang tercatat." action={<MoreLink to="/admin/attendance">Kelola absensi</MoreLink>}><ResourceState resource={team}><div className="v7-table-wrap"><table className="v7-table"><thead><tr><th>Staff</th><th>Login pertama · WIB</th><th>Status</th></tr></thead><tbody>{team.data?.rows.map(row => <tr key={row.user_id}><td><span className="v7-avatar">{(row.name || "S").slice(0, 2).toUpperCase()}</span><strong translate="no">{row.name}</strong></td><td>{timeWib(row.evidence_login_at)}</td><td><AttendanceBadge status={row.status} /></td></tr>)}</tbody></table>{team.data?.rows.length === 0 && <div className="v7-empty">Belum ada staff dalam daftar.</div>}</div></ResourceState></Panel> : <Panel title="Kehadiran Saya" subtitle="Catatan 30 hari terakhir."><ResourceState resource={me}>{me.data?.is_staff ? <><div className="v7-attendance-today"><div><small>Status hari ini</small><AttendanceBadge status={me.data.today?.status} /></div><div><small>Login pertama · WIB</small><strong>{timeWib(me.data.today?.evidence_login_at)}</strong></div></div><div className="v7-attendance-counts">{Object.entries(me.data.summary_30d || {}).map(([key, value]) => <div key={key}><strong>{number(value)}</strong><small>{STATUS[key] || key}</small></div>)}</div><p className="v7-footnote">Kehadiran mengikuti login pertama dan aturan kerja. Waktu keluar serta durasi kerja belum dicatat.</p></> : <div className="v7-empty">Akun Super Admin tidak dinilai sebagai staff.</div>}</ResourceState></Panel>}
        {(canPerformance || hasPermission("performance.view_own")) && <Panel title={canPerformance ? "Kinerja Tim" : "Kinerja Saya"} subtitle="Nilai mengikuti konfigurasi dan bukti pekerjaan pada periode ini." action={<label className="v7-month"><span className="sr-only">Periode kinerja</span><input aria-label="Periode kinerja" type="month" value={period} onChange={event => { if (event.target.value) setPeriod(event.target.value); }} /></label>}><ResourceState resource={performance}><div className="v7-score-summary"><div><strong>{number(score)}</strong><small>{canPerformance ? "Rata-rata skor tersedia" : "Skor keseluruhan"}</small></div><div><span className="v7-badge">{performance.data?.period_state === "finalized" ? "Periode final" : "Periode berjalan"}</span><p>{score == null ? "Data belum cukup untuk menghasilkan skor." : canPerformance ? `${scores.length} staff memiliki skor yang dapat dihitung.` : "Rincian komponen dan bukti pekerjaan tersedia pada halaman kinerja."}</p><MoreLink to={canPerformance ? "/admin/performance" : "/admin/my-performance"}>Lihat rincian kinerja</MoreLink></div></div>{canPerformance && <div className="v7-performance-list">{performance.data?.rows.slice(0, 6).map(row => <div key={row.user_id}><span><strong>{row.name}</strong><small>{row.role_name} · {number(row.completed_count)} tahapan selesai</small></span><div className="v7-progress"><i style={{ width: `${Math.max(0, Math.min(100, row.overall_score || 0))}%` }} /></div><b>{number(row.overall_score)}</b></div>)}</div>}<p className="v7-footnote">Absensi ditampilkan terpisah dan tidak dimasukkan ke skor KPI.</p></ResourceState></Panel>}
      </div>
      <aside className="v7-stack"><section className="v7-insight"><span className="v7-glass-tag"><Sparkles size={16} /> Workspace Staff</span><h2>Fokus bekerja.<br />Administrasi tetap rapi.</h2><p>Pantau catatan kerja, ajukan izin, dan tinjau kompensasi sesuai akses akunmu.</p><small translate="no">{user?.name} · {user?.role_name || user?.role}</small></section><Panel title="Akses Cepat" subtitle="Sesuai hak akses akunmu."><div>{links.map(([, route, title, subtitle, Icon]) => <Link key={route} to={route} className="v7-action-row"><Icon size={18} /><span><strong>{title}</strong><small>{subtitle}</small></span><ArrowUpRight size={16} /></Link>)}{links.length === 0 && <div className="v7-empty">Belum ada modul tambahan pada akunmu.</div>}</div></Panel></aside>
    </div>
    <div className="v7-dashboard-grid">
      {user?.role !== "super_admin" && <Panel title="Ajukan Cuti / Izin" subtitle="Permohonan akan diteruskan untuk persetujuan."><form className="v7-leave-form" onSubmit={submit}><label>Jenis permohonan<select name="type" value={form.type} onChange={event => setForm({ ...form, type: event.target.value })}><option value="annual">Cuti tahunan</option><option value="sick">Sakit</option><option value="permit">Izin</option></select></label><div><label>Tanggal mulai<input name="start_date" required type="date" value={form.start_date} onChange={event => setForm({ ...form, start_date: event.target.value })} /></label><label>Tanggal selesai<input name="end_date" required min={form.start_date || undefined} type="date" value={form.end_date} onChange={event => setForm({ ...form, end_date: event.target.value })} /></label></div><label>Alasan<textarea name="reason" required minLength={3} maxLength={500} rows={3} value={form.reason} onChange={event => setForm({ ...form, reason: event.target.value })} placeholder="Tuliskan alasan permohonanmu" /></label>{notice && <p className={notice.error ? "v7-error" : "v7-success"} role={notice.error ? "alert" : "status"}>{notice.text}</p>}<button type="submit" className="v7-primary" disabled={sending}><Send size={15} />{sending ? "Mengirim…" : "Kirim permohonan"}</button></form></Panel>}
      <Panel title={canTeam || hasPermission("staff.leave.approve") ? "Permohonan Cuti / Izin" : "Riwayat Permohonan Saya"} subtitle="Sepuluh permohonan terbaru yang dapat kamu lihat." action={hasPermission("staff.attendance.view") && <MoreLink to="/admin/attendance">Kelola permohonan</MoreLink>}><ResourceState resource={leave}>{leave.data?.items.length ? leave.data.items.slice(0, 10).map(item => <div className="v7-leave-row" key={item.id}><div><strong>{item.staff_name || user?.name}</strong><small>{dateWib(item.start_date)} – {dateWib(item.end_date)}</small><p>{item.reason}</p></div><span className={`v7-badge ${item.status === "pending" ? "is-waiting" : ""}`}>{LEAVE_STATUS[item.status] || item.status}</span></div>) : <div className="v7-empty">Belum ada permohonan.</div>}</ResourceState></Panel>
    </div>
    <footer className="v7-footer"><span>RILIS MUSIK</span><span>Waktu ditampilkan dalam WIB</span></footer>
  </div>;
}
