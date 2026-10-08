import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { ChevronDown, ChevronUp, Download, RefreshCw } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

const idr = (value) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(value || 0);
const day = (value) => (value ? new Date(value).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Jakarta" }) : "—");
const monthName = (period) => {
  if (!period || !/^\d{4}-\d{2}$/.test(period)) return period || "—";
  return new Date(`${period}-01T00:00:00Z`).toLocaleDateString("id-ID", { month: "long", year: "numeric", timeZone: "UTC" });
};

function useReport(path) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const load = useCallback(async (refresh = false) => {
    setState((current) => ({ ...current, loading: true, error: null }));
    try {
      const { data } = await api.get(path, { params: refresh ? { refresh: true } : {} });
      setState({ data, error: null, loading: false });
    } catch (error) {
      setState((current) => ({ ...current, error: formatApiError(error.response?.data?.detail), loading: false }));
    }
  }, [path]);
  useEffect(() => { load(); }, [load]);
  return { ...state, reload: () => load(true) };
}

function Card({ label, value, note, testid }) {
  return <div className="v13-metric" data-testid={testid}><h3>{label}</h3><strong>{value}</strong>{note && <div className="mt-auto pt-3 text-xs text-[var(--ui-muted)]">{note}</div>}</div>;
}

function Toolbar({ generatedAt, onReload, loading, children }) {
  const { t } = useAppPreferences();
  return <div className="flex flex-wrap items-center justify-between gap-3">
    <div className="flex flex-wrap items-center gap-2">{children}</div>
    <div className="flex items-center gap-3 text-xs text-[var(--ui-muted)]">{generatedAt && <span>{t("Diperbarui")} {new Date(generatedAt).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Jakarta" })}</span>}<button type="button" className="v13-chevron" onClick={onReload} disabled={loading} aria-label={t("Muat ulang")} title={t("Muat ulang")}><RefreshCw className={loading ? "animate-spin" : ""} /></button></div>
  </div>;
}

function Chips({ options, value, onChange }) {
  const { t } = useAppPreferences();
  return <div className="v13-tabs" role="group">{options.map(([key, label, count]) => <a key={key} href={`#${key}`} onClick={(event) => { event.preventDefault(); onChange(key); }} className={value === key ? "is-active" : ""} aria-pressed={value === key}>{t(label)}{count !== undefined && <span className="ml-1 opacity-60">{count}</span>}</a>)}</div>;
}

const CONDITION = {
  check_source: ["red", "Periksa sumber"],
  has_request: ["blue", "Ada pengajuan"],
  minimum_reached: ["green", "Minimum tercapai"],
  accumulating: [undefined, "Saldo terkumpul"],
  settled: [undefined, "Lunas"],
};
const AGE_LABELS = [["d0_90", "0–90 hari"], ["d91_180", "91–180 hari"], ["d181_365", "181–365 hari"], ["d365_plus", ">365 hari"], ["unknown", "Tidak diketahui"]];

function downloadCsv(rows) {
  const header = ["Label/penerima", "Jumlah label", "Belum diajukan", "Diproses", "Menunggu dana", "Dana >365 hari", "Pendapatan terakhir", "Periode", "Pembayaran terakhir", "Kondisi"];
  const body = rows.map((row) => [row.name, row.label_count, row.available_idr, row.processing_idr, row.pending_idr, row.age.d365_plus, row.last_income?.amount_idr ?? "", row.last_income?.period ?? "", row.last_paid_at ?? "", CONDITION[row.condition]?.[1] || row.condition]);
  const csv = [header, ...body].map((line) => line.map((cell) => `"${String(cell ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  link.download = `pemantauan-dana-${new Date().toISOString().slice(0, 10)}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

function FundsDetail({ row }) {
  const { t } = useAppPreferences();
  const total = AGE_LABELS.reduce((sum, [key]) => sum + Math.max(0, row.age[key]), 0) || 1;
  return <div className="grid gap-5 bg-[var(--ui-raised)] p-5 md:grid-cols-2" data-testid={`funds-detail-${row.id}`}>
    <div className="space-y-2">
      <div className="v13-section-label">{t("Umur dana belum diajukan")}</div>
      {AGE_LABELS.map(([key, label]) => <div key={key} className="grid grid-cols-[110px_1fr_auto] items-center gap-3 text-sm"><span className="text-[var(--ui-muted)]">{t(label)}</span><span className="h-1.5 overflow-hidden rounded-full bg-[var(--ui-surface)]"><span className="block h-full rounded-full bg-[#3a8dff]" style={{ width: `${Math.max(0, row.age[key]) / total * 100}%` }} /></span><span className="tabular-nums">{idr(row.age[key])}</span></div>)}
      <p className="pt-1 text-xs text-[var(--ui-muted)]">{t("Umur dihitung dari akhir bulan laporan; penyesuaian saldo tidak punya tanggal sumber.")}</p>
    </div>
    <div className="space-y-2">
      <div className="v13-section-label">{t("Rincian label")}</div>
      {row.labels.map((label) => <div key={label.id} className="flex items-center justify-between gap-3 text-sm"><span className="truncate" translate="no">{label.label_name}</span><span className="shrink-0 tabular-nums">{idr(label.available_idr)}{label.processing_idr > 0 && <span className="text-[var(--ui-muted)]"> · {t("diproses")} {idr(label.processing_idr)}</span>}</span></div>)}
      <div className="flex justify-between pt-2 text-sm"><span className="text-[var(--ui-muted)]">{t("Rekening bank")}</span><span>{row.bank_verified ? t("Terverifikasi") : t("Belum terverifikasi")}</span></div>
      <div className="flex justify-between text-sm"><span className="text-[var(--ui-muted)]">{t("Total pernah dibayar")}</span><span className="tabular-nums">{idr(row.paid_idr)}</span></div>
      {row.anomalies.length > 0 && <p className="text-sm text-[var(--v13-urgent)]">{t("Saldo sumber negatif — periksa penyesuaian atau penarikan.")}</p>}
    </div>
  </div>;
}

function FundsPage() {
  const { t } = useAppPreferences();
  const report = useReport("/admin/finance-monitor/funds");
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(null);
  const [limit, setLimit] = useState(50);
  const data = report.data;
  const min = data?.min_withdraw_idr || 1000000;
  const filters = useMemo(() => ({
    all: () => true,
    available: (row) => row.available_idr > 0,
    processing: (row) => row.processing_idr > 0,
    eligible: (row) => row.available_idr > min && row.processing_idr === 0,
    inactive: (row) => row.inactive,
    old: (row) => row.age.d365_plus > 0,
    unknown: (row) => row.age.unknown !== 0,
    never: (row) => row.never_paid && row.available_idr > 0,
  }), [min]);
  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (data?.rows || []).filter(filters[filter]).filter((row) => !q || row.labels.some((label) => (label.label_name || "").toLowerCase().includes(q)));
  }, [data, filter, filters, query]);
  const count = (key) => (data?.rows || []).filter(filters[key]).length;
  if (report.error && !data) return <p role="alert" className="text-[var(--v13-urgent)]">{report.error}</p>;
  if (!data) return <p role="status" className="text-[var(--ui-muted)]">{t("Menghitung saldo seluruh label…")}</p>;
  const totals = data.totals;
  return <div className="space-y-5" data-testid="finance-funds">
    <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      <Card label={t("Hak label belum dibayar")} value={idr(totals.unpaid_idr)} note={`${totals.accounts} ${t("akun penerima")}`} testid="funds-unpaid" />
      <Card label={t("Belum diajukan")} value={idr(totals.available_idr)} note={t("Bagian dari hak belum dibayar")} testid="funds-available" />
      <Card label={t("Pengajuan diproses")} value={idr(totals.processing_idr)} note={t("Bagian dari hak belum dibayar")} testid="funds-processing" />
      <Card label={t("Tersedia >365 hari")} value={idr(totals.age_365_plus_idr)} note={t("Bagian dari belum diajukan")} testid="funds-old" />
    </div>
    <p className="text-sm text-[var(--ui-muted)]">{t("Umur belum diketahui")}: {idr(totals.age_unknown_idr)} · {t("Pendapatan menunggu dana distributor")}: {idr(totals.pending_idr)} · {t("Hak royalti bukan pendapatan perusahaan walau belum ditarik.")}</p>
    <Toolbar generatedAt={data.generated_at} onReload={report.reload} loading={report.loading}>
      <Chips value={filter} onChange={(key) => { setFilter(key); setLimit(50); }} options={[["all", "Semua", data.rows.length], ["available", "Belum diajukan", count("available")], ["processing", "Diproses", count("processing")], ["eligible", "Minimum tercapai", count("eligible")], ["inactive", "Tidak aktif", count("inactive")], ["old", ">365 hari", count("old")], ["unknown", "Umur tidak diketahui", count("unknown")], ["never", "Belum pernah dibayar", count("never")]]} />
    </Toolbar>
    <section className="v13-card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 pt-5"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("Cari label")} className="v13-select w-64" data-testid="funds-search" /><button type="button" onClick={() => downloadCsv(rows)} className="inline-flex items-center gap-2 text-sm text-[var(--ui-muted)] hover:text-[var(--ui-text)]" data-testid="funds-export"><Download className="h-4 w-4" />{t("Unduh daftar")}</button></div>
      <div className="overflow-x-auto"><table className="w-full min-w-[860px] text-sm">
        <thead><tr className="text-left text-xs text-[var(--ui-muted)]">{["Label/penerima", "Belum diajukan", "Dana >365 hari", "Pendapatan terakhir", "Pembayaran terakhir", "Kondisi", ""].map((head) => <th key={head} className="px-5 py-3 font-normal">{t(head)}</th>)}</tr></thead>
        <tbody>{rows.slice(0, limit).map((row) => { const [tone, label] = CONDITION[row.condition] || []; const expanded = open === row.id; return <React.Fragment key={row.id}>
          <tr className="border-t border-[var(--ui-border)]" data-testid={`funds-row-${row.id}`}>
            <td className="px-5 py-3"><div className="font-medium" translate="no">{row.name}</div><div className="text-xs text-[var(--ui-muted)]">{row.label_count > 1 ? `${row.label_count} ${t("label")} · ` : ""}{row.inactive ? t("Tidak ada aktivitas rilis >90 hari") : `${t("Aktivitas")} ${day(row.last_activity_at)}`}</div></td>
            <td className="px-5 py-3 tabular-nums">{idr(row.available_idr)}{row.processing_idr > 0 && <div className="text-xs text-[var(--ui-muted)]">{t("diproses")} {idr(row.processing_idr)}</div>}</td>
            <td className="px-5 py-3 tabular-nums">{row.age.d365_plus ? idr(row.age.d365_plus) : "—"}</td>
            <td className="px-5 py-3 tabular-nums">{row.last_income ? <>{idr(row.last_income.amount_idr)}<div className="text-xs text-[var(--ui-muted)]">{monthName(row.last_income.period)}</div></> : "—"}</td>
            <td className="px-5 py-3">{day(row.last_paid_at)}</td>
            <td className="px-5 py-3"><span className="v13-pill" data-tone={tone}>{t(label)}</span></td>
            <td className="px-5 py-3 text-right"><button type="button" className="v13-chevron" aria-expanded={expanded} aria-label={t("Rincian")} onClick={() => setOpen(expanded ? null : row.id)}>{expanded ? <ChevronUp /> : <ChevronDown />}</button></td>
          </tr>
          {expanded && <tr><td colSpan={7} className="p-0"><FundsDetail row={row} /></td></tr>}
        </React.Fragment>; })}</tbody>
      </table></div>
      {rows.length === 0 && <p className="px-5 py-8 text-center text-sm text-[var(--ui-muted)]">{t("Tidak ada akun pada filter ini.")}</p>}
      {rows.length > limit && <div className="p-4 text-center"><button type="button" className="text-sm text-[var(--ui-muted)] hover:text-[var(--ui-text)]" onClick={() => setLimit((value) => value + 100)}>{t("Tampilkan lebih banyak")} ({rows.length - limit})</button></div>}
    </section>
  </div>;
}

function CataloguePage() {
  const { t } = useAppPreferences();
  const report = useReport("/admin/finance-monitor/catalogue");
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(50);
  const data = report.data;
  const rows = useMemo(() => (data?.rows || []).filter((row) => !query.trim() || (row.label_name || "").toLowerCase().includes(query.trim().toLowerCase())), [data, query]);
  if (report.error && !data) return <p role="alert" className="text-[var(--v13-urgent)]">{report.error}</p>;
  if (!data) return <p role="status" className="text-[var(--ui-muted)]">{t("Memuat perkembangan katalog…")}</p>;
  return <div className="space-y-5" data-testid="finance-catalogue">
    <p className="text-sm text-[var(--ui-muted)]">{t("Membandingkan")} {monthName(data.period)} {t("dengan")} {monthName(data.previous_period)}. {t("Data yang belum ada tidak dianggap nol, dan penurunan pendapatan tidak memengaruhi akses label.")}</p>
    <Toolbar generatedAt={data.generated_at} onReload={report.reload} loading={report.loading}><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("Cari label")} className="v13-select w-64" /></Toolbar>
    <section className="v13-card overflow-x-auto"><table className="w-full min-w-[720px] text-sm">
      <thead><tr className="text-left text-xs text-[var(--ui-muted)]">{["Label", "Periode laporan", "Pendapatan", "Perbandingan", "Rilisan 90 hari"].map((head) => <th key={head} className="px-5 py-3 font-normal">{t(head)}</th>)}</tr></thead>
      <tbody>{rows.slice(0, limit).map((row) => <tr key={row.label_id} className="border-t border-[var(--ui-border)]">
        <td className="px-5 py-3 font-medium" translate="no">{row.label_name}</td>
        <td className="px-5 py-3">{monthName(data.period)}</td>
        <td className="px-5 py-3 tabular-nums">{idr(row.revenue_idr)}</td>
        <td className="px-5 py-3">{!data.comparable ? <span className="text-xs text-[var(--ui-muted)]">{t("Data belum sebanding")}</span> : row.change_pct === null ? <span className="text-xs text-[var(--ui-muted)]">{t("Dasar Rp0 · tanpa persentase")}</span> : <span className="v13-trend" data-trend={row.change_pct < 0 ? "down" : "up"}>{row.change_pct < 0 ? <ChevronDown /> : <ChevronUp />}{row.change_pct > 0 ? "+" : ""}{row.change_pct}%</span>}</td>
        <td className="px-5 py-3 tabular-nums">{row.releases_90d}</td>
      </tr>)}</tbody>
    </table>
    {rows.length > limit && <div className="p-4 text-center"><button type="button" className="text-sm text-[var(--ui-muted)] hover:text-[var(--ui-text)]" onClick={() => setLimit((value) => value + 100)}>{t("Tampilkan lebih banyak")} ({rows.length - limit})</button></div>}
    </section>
  </div>;
}

const RECEIPT_STATUS = { dana_received: ["green", "Dialokasikan"], published: ["mustard", "Menunggu dana"], receiving: ["blue", "Diproses"], receive_error: ["red", "Perlu dicocokkan"] };

function CashPage() {
  const { t } = useAppPreferences();
  const report = useReport("/admin/finance-monitor/cash");
  const [form, setForm] = useState({ amount_idr: "", observed_at: "", scope: "", note: "" });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const data = report.data;
  const save = async (event) => {
    event.preventDefault();
    setSaving(true); setMessage(null);
    try {
      await api.post("/admin/finance-monitor/cash-observations", { ...form, amount_idr: Number(String(form.amount_idr).replace(/\D/g, "")), observed_at: new Date(form.observed_at).toISOString() });
      setForm({ amount_idr: "", observed_at: "", scope: "", note: "" });
      setMessage({ ok: true, text: t("Posisi kas tercatat.") });
      report.reload();
    } catch (error) {
      setMessage({ ok: false, text: formatApiError(error.response?.data?.detail) });
    } finally { setSaving(false); }
  };
  if (report.error && !data) return <p role="alert" className="text-[var(--v13-urgent)]">{report.error}</p>;
  if (!data) return <p role="status" className="text-[var(--ui-muted)]">{t("Memuat rekonsiliasi kas…")}</p>;
  const totals = data.totals;
  return <div className="space-y-5" data-testid="finance-cash">
    <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      <Card label={t("Dana distributor tercatat")} value={idr(totals.received_idr)} note={`${t("Hak label di dalamnya")} ${idr(totals.received_label_idr)}`} testid="cash-received" />
      <Card label={t("Hak label menunggu dana")} value={idr(totals.pending_label_idr)} note={t("Laporan terbit, dana belum diterima")} testid="cash-pending" />
      <Card label={t("Pembayaran terkonfirmasi")} value={idr(totals.paid_idr)} note={t("Penarikan berstatus dibayar")} testid="cash-paid" />
      <Card label={t("Kas teramati terakhir")} value={totals.latest_cash_idr === null ? "—" : idr(totals.latest_cash_idr)} note={data.observations[0] ? `${day(data.observations[0].observed_at)} · ${data.observations[0].scope}` : t("Belum ada catatan")} testid="cash-observed" />
    </div>
    <p className="text-sm text-[var(--ui-muted)]">{t("Kesimpulan selisih kas")}: <strong>{t("Belum dapat disimpulkan")}</strong> — {t("buku besar belum memuat mutasi bank, jadi posisi kas dicatat manual dan tidak mengubah saldo.")}</p>
    <Toolbar generatedAt={data.generated_at} onReload={report.reload} loading={report.loading} />
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
      <section className="v13-card overflow-x-auto"><div className="v13-card-head"><h2>{t("Penerimaan distributor")}</h2></div><table className="w-full min-w-[640px] text-sm">
        <thead><tr className="text-left text-xs text-[var(--ui-muted)]">{["Laporan", "Bruto", "Hak label", "Diterima", "Status"].map((head) => <th key={head} className="px-5 py-3 font-normal">{t(head)}</th>)}</tr></thead>
        <tbody>{data.receipts.map((item) => { const [tone, label] = RECEIPT_STATUS[item.status] || []; return <tr key={item.id} className="border-t border-[var(--ui-border)]">
          <td className="px-5 py-3"><div className="max-w-[260px] truncate font-medium">{item.filename || item.id}</div><div className="text-xs text-[var(--ui-muted)]">{item.period && item.period !== "multi" ? monthName(item.period) : t("Multi periode")}</div></td>
          <td className="px-5 py-3 tabular-nums">{idr(item.gross_idr)}</td><td className="px-5 py-3 tabular-nums">{idr(item.label_idr)}</td><td className="px-5 py-3">{day(item.received_at)}</td>
          <td className="px-5 py-3"><span className="v13-pill" data-tone={tone}>{t(label || item.status)}</span></td>
        </tr>; })}</tbody>
      </table></section>
      <section className="v13-card"><div className="v13-card-head"><h2>{t("Catat posisi kas")}</h2></div>
        <form className="v13-card-body space-y-3" onSubmit={save} data-testid="cash-form">
          <label className="block text-sm">{t("Jumlah (Rp)")}<input required inputMode="numeric" value={form.amount_idr} onChange={(event) => setForm({ ...form, amount_idr: event.target.value })} className="v13-select mt-1 w-full" /></label>
          <label className="block text-sm">{t("Per tanggal")}<input required type="datetime-local" max={new Date().toISOString().slice(0, 16)} value={form.observed_at} onChange={(event) => setForm({ ...form, observed_at: event.target.value })} className="v13-select mt-1 w-full" /></label>
          <label className="block text-sm">{t("Cakupan rekening")}<input required maxLength={150} value={form.scope} onChange={(event) => setForm({ ...form, scope: event.target.value })} className="v13-select mt-1 w-full" /></label>
          <label className="block text-sm">{t("Catatan")}<textarea maxLength={1000} rows={3} value={form.note} onChange={(event) => setForm({ ...form, note: event.target.value })} className="mt-1 w-full rounded-[10px] bg-[var(--ui-raised)] p-2 text-sm outline-none" /></label>
          <button type="submit" disabled={saving} className="w-full rounded-full bg-[var(--ui-text)] py-2.5 text-sm text-[var(--ui-surface)] disabled:opacity-50">{saving ? t("Menyimpan…") : t("Simpan posisi kas")}</button>
          {message && <p role={message.ok ? "status" : "alert"} className={`text-sm ${message.ok ? "text-[var(--v13-up)]" : "text-[var(--v13-urgent)]"}`}>{message.text}</p>}
        </form>
        {data.observations.length > 0 && <div className="v13-card-body pt-0">{data.observations.map((item) => <div key={item.id} className="v13-row"><div className="min-w-0"><div className="v13-row-title tabular-nums">{idr(item.amount_idr)}</div><div className="v13-row-sub truncate">{day(item.observed_at)} · {item.scope}</div></div><span className="text-xs text-[var(--ui-muted)]">{item.recorded_by_name}</span></div>)}</div>}
      </section>
    </div>
  </div>;
}

export default function FinanceMonitor() {
  const { pathname } = useLocation();
  if (pathname.endsWith("/catalogue")) return <CataloguePage />;
  if (pathname.endsWith("/cash")) return <CashPage />;
  return <FundsPage />;
}
