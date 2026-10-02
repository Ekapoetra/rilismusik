import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, CalendarDays, CheckCheck, ChevronLeft, ChevronRight, RefreshCw, Sparkles, X } from "lucide-react";
import { useAuth } from "@/api/AuthContext";
import { useV7Resource } from "@/components/admin/v7/useV7Resource";
import { Panel, MoreLink, ResourceState, WorkRow, number, rupiah, dateWib, timeWib } from "@/components/admin/v7/V7Primitives";

const TILES = [
  ["all", "Total Pekerjaan", "Pekerjaan aktif", "total"],
  ["new", "Antrean Baru", "Belum ditangani", "new"],
  ["in_progress", "Dalam Penanganan", "Tahapan sedang berjalan", "in_progress"],
  ["waiting", "Menunggu Pihak Lain", "Bagian dari penanganan", "waiting"],
];
function Trend({ value, count = false }) {
  if (!value) return null;
  return <small className={`v7-trend ${value.direction === "down" ? "is-down" : ""}`}>{value.direction === "up" ? "↗" : value.direction === "down" ? "↘" : "—"} {value.pct == null ? "Belum ada pembanding" : `${number(Math.abs(value.pct))}% ${count ? "perubahan penambahan" : "perubahan"}`}<span>Dibanding rentang sebelumnya yang setara</span></small>;
}
export default function V7Dashboard() {
  const { user, hasPermission } = useAuth();
  const [bucket, setBucket] = useState(null);
  const [page, setPage] = useState(1);
  const [period, setPeriod] = useState("month");
  const dashboard = useV7Resource(`/admin/dashboard/v7?bucket=${bucket || "all"}&page=${page}&page_size=20`, 60000);
  const metrics = useV7Resource(`/admin/dashboard/metrics?period=${period}`, 60000);
  const activity = useV7Resource(hasPermission("activity.view") ? "/admin/activity-logs?limit=6" : null);
  const data = dashboard.data;
  const summary = data?.summary;
  const select = (key) => { setBucket((current) => current === key ? null : key); setPage(1); };
  const overdue = data?.my_work?.reduce((sum, item) => sum + item.overdue_count, 0);
  const metricsList = [
    ["sales_revenue", "Pendapatan Layanan", true, "Pembayaran Xendit yang diterima"],
    ["royalty_income", "Pendapatan Royalti", true, metrics.data?.royalty_income?.period ? `Impor terakhir · ${metrics.data.royalty_income.period}` : "Belum ada laporan royalti"],
    ["total_labels", "Total Label", false, "Seluruh label terdaftar"],
    ["total_artists", "Total Artis", false, "Seluruh artis terdaftar"],
    ["total_releases", "Total Rilisan", false, "Seluruh rilisan terdaftar"],
    ["active_members", "Label Aktif", false, "Akun aktif dan tidak diblokir"],
  ].filter(([key]) => key !== "royalty_income" || hasPermission("royalty.view") || hasPermission("analytics.view"));
  return <div className="v7-page" data-testid="v7-platform-dashboard">
    <div className="v7-heading"><div><div className="v7-eyebrow">WORKSPACE / PLATFORM</div><h1>Halo, <span translate="no">{user?.name || "Tim Rilis Musik"}</span>.</h1><p>Ringkasan pekerjaan dan layanan dalam cakupan aksesmu.</p></div><div className="v7-date"><CalendarDays size={15} />{dateWib(new Date())}<small>WIB · {data ? `Diperbarui ${timeWib(data.generated_at)}` : "Memuat ringkasan"}</small></div></div>
    <ResourceState resource={dashboard}>
      <div className="v7-focus"><span className="v7-dot" /><div><strong>{overdue ? `${number(overdue)} tahapan melewati SLA` : "Mulai dari pekerjaan yang perlu perhatianmu"}</strong><small>{overdue ? "Periksa tindak lanjut pada antrean pekerjaanmu." : "Pantau antrean baru dan pekerjaan yang menunggu pihak lain."}</small></div>{hasPermission("work.view") && <MoreLink to="/admin/work">Tinjau prioritas</MoreLink>}</div>
      <div className="v7-stat-grid">
        {TILES.map(([key, label, hint, field], index) => <button key={key} type="button" className={`v7-stat ${index === 0 ? "is-featured" : ""} ${bucket === key ? "is-selected" : ""}`} onClick={() => select(key)} aria-expanded={bucket === key} aria-controls="v7-work-details" data-testid={`v7-summary-${key}`}><span>{label}</span><i><ArrowUpRight size={20} /></i><strong>{number(summary?.[field])}</strong><small>{hint}</small></button>)}
        {hasPermission("work.view") ? <Link className="v7-stat" to="/admin/work"><span>Selesai Hari Ini</span><i><CheckCheck size={19} /></i><strong>{number(summary?.completed_today)}</strong><small>Tahapan selesai · hari WIB</small></Link> : <div className="v7-stat"><span>Selesai Hari Ini</span><strong>—</strong><small>Di luar cakupan aksesmu</small></div>}
      </div>
      {bucket && <Panel className="v7-details" title={TILES.find(([key]) => key === bucket)?.[1]} subtitle={`${number(data?.details.total)} pekerjaan dalam cakupan aksesmu`} action={<button type="button" className="v7-icon-btn" aria-label="Tutup rincian pekerjaan" onClick={() => setBucket(null)}><X size={18} /></button>}><div id="v7-work-details">{data?.details.items.length ? data.details.items.map(item => <WorkRow key={item.key} item={item} progress />) : <div className="v7-empty">Tidak ada pekerjaan pada kategori ini.</div>}</div>{data?.details.pages > 1 && <div className="v7-pagination"><button disabled={page === 1} onClick={() => setPage(p => p - 1)} aria-label="Halaman sebelumnya"><ChevronLeft size={16} /></button><span>Halaman {page} dari {data.details.pages}</span><button disabled={page >= data.details.pages} onClick={() => setPage(p => p + 1)} aria-label="Halaman berikutnya"><ChevronRight size={16} /></button></div>}</Panel>}
      <div className="v7-dashboard-grid">
        <Panel title="Antrean Pekerjaan" subtitle="Pekerjaan baru yang dapat kamu lihat." action={<button className="v7-text-link" onClick={() => select("new")}>Lihat semua <ArrowUpRight size={15} /></button>}>
          {data?.queue_preview.length ? data.queue_preview.map(item => <WorkRow key={item.key} item={item} />) : <div className="v7-empty">Antrean baru sudah kosong.</div>}
        </Panel>
        <div className="v7-my-work-stack"><Panel title="Pekerjaan Saya" subtitle="Sesuai tanggung jawab akunmu." action={hasPermission("work.view") && <MoreLink to="/admin/work" />}>
          {data?.my_work == null ? <div className="v7-empty">Akunmu belum memiliki akses antrean kerja.</div> : data.my_work.filter(item => item.open_count > 0).length ? data.my_work.filter(item => item.open_count > 0).slice(0, 4).map(item => <Link to={item.link} className="v7-action-row" key={item.work_type}><span><strong>{item.label_id}</strong><small>{number(item.open_count)} tahapan terbuka{item.overdue_count ? ` · ${number(item.overdue_count)} melewati SLA` : ""}</small></span><ArrowUpRight size={17} /></Link>) : <div className="v7-empty">Tidak ada pekerjaan terbuka untukmu.</div>}
        </Panel><Panel title="Statistik Pekerjaan" subtitle="Seluruh pekerjaan yang dapat dilihat akun ini."><div className="v7-work-stats"><strong>{number(summary?.total)}</strong><div className="v7-tick-track" aria-label={`${summary?.new || 0} antrean; ${summary?.in_progress || 0} dalam penanganan`}><i style={{ width: `${summary?.total ? summary.new / summary.total * 100 : 0}%` }} /></div><div className="v7-legend"><span><i />{number(summary?.new)} Antrean</span><span><i />{number(summary?.in_progress)} Dalam penanganan</span></div></div></Panel></div>
      </div>
      <Panel title="Dalam Penanganan" subtitle="Persentase menunjukkan tahapan proses, bukan kecepatan kerja." action={<button className="v7-text-link" onClick={() => select("in_progress")}>Semua penanganan <ArrowUpRight size={15} /></button>}>
        {data?.in_progress_preview.length ? data.in_progress_preview.map(item => <WorkRow key={item.key} item={item} progress />) : <div className="v7-empty">Belum ada pekerjaan dalam penanganan.</div>}
      </Panel>
      {data?.is_manager && <Panel title="Monitor Tim" subtitle="Pekerjaan yang didelegasikan kepada tim; terpisah dari Pekerjaan Saya." action={<MoreLink to="/admin/work" />}><div className="v7-team-work">{data.team_work?.length ? data.team_work.map(item => <Link to={item.link} key={item.work_type}><span>{item.label_id}</span><strong>{number(item.open_count)}</strong><small>{number(item.overdue_count)} melewati SLA</small></Link>) : <div className="v7-empty">Belum ada tanggung jawab yang didelegasikan.</div>}</div></Panel>}
    </ResourceState>
    <div className="v7-section-heading"><h2>Ringkasan Platform</h2><label>Periode <select value={period} onChange={event => setPeriod(event.target.value)}><option value="today">Hari ini</option><option value="week">Minggu ini</option><option value="month">Bulan ini</option></select></label><button className="v7-icon-btn" onClick={() => { dashboard.reload(); metrics.reload(); activity.reload(); }} aria-label="Perbarui dashboard"><RefreshCw size={16} /></button></div>
    <ResourceState resource={metrics}>
      <div className="v7-finance-grid">
        {metrics.data?.requested_withdrawal && <Panel title="Penarikan periode ini" subtitle="Penarikan dibayar dan permintaan yang masih terbuka." action={<MoreLink to="/admin/withdraw" />}><div className="v7-money"><strong>{rupiah(metrics.data.requested_withdrawal.value)}</strong><Trend value={metrics.data.requested_withdrawal.trend} /><p>Pembayaran dihitung dari tanggal bayar. Permintaan terbuka dihitung dari tanggal permintaan.</p></div></Panel>}
        <section className="v7-insight"><span className="v7-glass-tag"><Sparkles size={16} /> Wawasan</span><strong>{number(summary?.waiting)}</strong><h2>Menunggu tindak lanjut pihak lain.</h2><p>{summary == null ? "Ringkasan pekerjaan belum tersedia." : summary.waiting ? "Periksa status terakhir sebelum menghubungi label atau distributor kembali." : "Saat ini tidak ada pekerjaan dalam cakupanmu yang tercatat menunggu pihak lain."}</p>{summary != null && <button onClick={() => select("waiting")}>Tinjau pekerjaan <ArrowUpRight size={17} /></button>}<small>Berdasarkan status pekerjaan saat ini.</small></section>
      </div>
      <div className="v7-platform-grid">{metricsList.map(([key, label, money, hint]) => <section className="v7-metric" key={key}><h3>{label}</h3><strong>{money ? rupiah(metrics.data?.[key]?.value) : number(metrics.data?.[key]?.value)}</strong><p>{hint}</p>{key === "royalty_income" ? <small>Nilai impor terakhir dalam rupiah pada kurs impor.</small> : <><Trend value={metrics.data?.[key]?.trend} count={!money} />{!money && <small>{number(metrics.data?.[key]?.added)} ditambahkan pada periode ini</small>}</>}</section>)}</div>
    </ResourceState>
    {data && <Panel title="Komposisi Pekerjaan Aktif" subtitle="Jumlah pekerjaan per kategori dalam cakupan aksesmu."><div className="v7-category-bars">{data.categories.length ? data.categories.map(item => <div key={item.category}><span>{item.category}</span><div><i style={{ width: `${item.count / Math.max(...data.categories.map(c => c.count), 1) * 100}%` }} /></div><strong>{number(item.count)}</strong></div>) : <div className="v7-empty">Belum ada pekerjaan aktif.</div>}</div></Panel>}
    {hasPermission("activity.view") && <Panel title="Aktivitas Operasional" subtitle="Perubahan terbaru pada pekerjaan dan layanan." action={<MoreLink to="/admin/activity-logs" />}><ResourceState resource={activity}><div className="v7-activity-grid">{activity.data?.length ? activity.data.map(log => <div key={log.id}><span className="v7-dot" /><div><strong>{log.user_name || "Sistem"}</strong><p>{String(log.action || "Aktivitas").replaceAll("_", " ")}</p><small>{log.reference_id || log.module}</small></div><time>{timeWib(log.created_at)}</time></div>) : <div className="v7-empty">Belum ada aktivitas.</div>}</div></ResourceState></Panel>}
    <footer className="v7-footer"><span>RILIS MUSIK</span><span>Waktu ditampilkan dalam WIB</span></footer>
  </div>;
}
