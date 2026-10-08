import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { openXenditCheckout, pollPaymentUntilTerminal } from "@/api/payments";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { PLAN_EVENT } from "@/components/v13/Plans";
import { TOKEN_EVENT, TokenHistory } from "@/components/v13/Tokens";
import { planName } from "@/lib/plans";

const idr = (n) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
const day = (iso) => (iso ? new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Jakarta" }) : "—");
const KINDS = { annual_subscription: "plan", token_pack: "token", custom_service: "service", wami_addon: "service", pay_per_release: "release", release_shortfall: "release" };
const KIND_NAMES = { plan: "Paket", token: "Token", service: "Layanan", release: "Rilisan" };
const TYPE_NAMES = { token_pack: "Pembelian token", annual_subscription: "Paket", pay_per_release: "Biaya rilisan per lagu", release_shortfall: "Kekurangan paket album", wami_addon: "Registrasi WAMI", custom_service: "Layanan tambahan" };
const STATUS = { pending: ["mustard", "Menunggu pembayaran"], paid: ["green", "Berhasil"], expired: [undefined, "Kedaluwarsa"], failed: ["red", "Gagal"], cancelled: [undefined, "Dibatalkan"] };
const FOLLOW_UP = ["expired", "failed", "cancelled"];

// Prototype result line ("Pembayaran / Hasil").
function resultText(item, t) {
  if (item.refund_status === "refunded") return t("Dana dikembalikan");
  if (item.status !== "paid") return t("Pembelian belum dipenuhi");
  if (item.type === "token_pack") return `${item.token_quantity || ""} ${t("token telah ditambahkan")}`.trim();
  if (item.type === "annual_subscription") return `${t("Paket")} ${planName(item.tier)} ${t("diterapkan")}`;
  if (item.type === "pay_per_release" || item.type === "release_shortfall") return t("Rilisan diproses");
  return t("Permintaan telah diterima");
}

export default function Invoices() {
  const { t } = useAppPreferences();
  const [searchParams, setSearchParams] = useSearchParams();
  const [items, setItems] = useState(null);
  const [tab, setTab] = useState("transactions");
  const [filters, setFilters] = useState({ q: "", kind: "", status: "", from: "", to: "", followUp: false });
  const [loading, setLoading] = useState(false);
  const [pollingId, setPollingId] = useState(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    const { data } = await api.get("/label/invoices");
    setItems(Array.isArray(data) ? data : []);
  }, []);
  useEffect(() => { load().catch((e) => setErr(formatApiError(e.response?.data?.detail))); }, [load]);

  useEffect(() => {
    const paymentId = searchParams.get("payment_id");
    if (!paymentId) return undefined;
    let active = true;
    setPollingId(paymentId); setMsg(t("Mengonfirmasi pembayaran ke Xendit…"));
    pollPaymentUntilTerminal(paymentId, () => {}, 75)
      .then(async (result) => {
        if (!active) return;
        if (result.status === "paid") setMsg(t("Pembayaran berhasil dikonfirmasi."));
        else if (result.status === "pending") setMsg(t("Pembayaran masih diproses. Status akan diperbarui otomatis."));
        else setErr(`${t("Pembayaran berstatus")} ${result.status}.`);
        setPollingId(null); setSearchParams({}); await load();
        window.dispatchEvent(new Event(TOKEN_EVENT)); window.dispatchEvent(new Event(PLAN_EVENT));
      })
      .catch((e) => active && setErr(formatApiError(e.response?.data?.detail || e.message)))
      .finally(() => active && setPollingId(null));
    return () => { active = false; };
  }, [searchParams, setSearchParams, load, t]);

  const payExisting = async (id) => {
    setErr(""); setLoading(true);
    try { await openXenditCheckout(id); }
    catch (e) { setErr(formatApiError(e.response?.data?.detail || e.message)); setLoading(false); }
  };

  const all = useMemo(() => items || [], [items]);
  const rows = useMemo(() => all.filter((item) => {
    if (tab === "refunds" && !item.refund_status) return false;
    const text = `${item.description || ""} ${TYPE_NAMES[item.type] || ""} ${item.reference_id || ""}`.toLowerCase();
    if (filters.q && !text.includes(filters.q.toLowerCase())) return false;
    if (filters.kind && KINDS[item.type] !== filters.kind) return false;
    if (filters.status && item.status !== filters.status) return false;
    if (filters.from && String(item.created_at).slice(0, 10) < filters.from) return false;
    if (filters.to && String(item.created_at).slice(0, 10) > filters.to) return false;
    if (filters.followUp && !FOLLOW_UP.includes(item.status)) return false;
    return true;
  }), [all, tab, filters]);
  const sum = (list) => list.reduce((total, item) => total + (item.amount || 0), 0);
  const pending = all.filter((item) => item.status === "pending");
  const paid = all.filter((item) => item.status === "paid");
  const followUp = all.filter((item) => FOLLOW_UP.includes(item.status));

  return <div className="space-y-5" data-testid="label-transactions">
    <header><div className="v13-section-label">{t("Pembelian & Pembayaran")}</div><h1 className="mt-1 text-3xl">{t("Transaksi")}</h1><p className="mt-1 text-sm text-[var(--ui-muted)]">{t("Pembayaran yang jelas. Setiap pembelian terselesaikan.")}</p></header>
    {msg && <div role="status" className="text-sm text-[var(--v13-up)]" data-testid="payment-success-message">{pollingId && <RefreshCw className="mr-2 inline h-4 w-4 animate-spin" />}{msg}</div>}
    {err && <div role="alert" className="text-sm text-[var(--v13-urgent)]" data-testid="payment-error-message">{err}</div>}
    <div className="grid gap-3 md:grid-cols-3">
      <div className="v13-metric"><h3>{t("Menunggu pembayaran")}</h3><strong>{pending.length}</strong><div className="mt-auto pt-3 text-xs text-[var(--ui-muted)]">{idr(sum(pending))}</div></div>
      <div className="v13-metric"><h3>{t("Pembayaran berhasil")}</h3><strong>{paid.length}</strong><div className="mt-auto pt-3 text-xs text-[var(--ui-muted)]">{idr(sum(paid))}</div></div>
      <div className="v13-metric"><h3>{t("Perlu tindak lanjut")}</h3><strong>{followUp.length}</strong><div className="mt-auto pt-3 text-xs text-[var(--ui-muted)]">{t("Kedaluwarsa, gagal, atau dibatalkan")}</div></div>
    </div>
    <nav className="v13-tabs" style={{ display: "inline-flex" }}>{[["transactions", "Transaksi"], ["refunds", "Pengembalian Dana"]].map(([key, name]) => <a key={key} href={`#${key}`} onClick={(event) => { event.preventDefault(); setTab(key); }} className={tab === key ? "is-active" : ""}>{t(name)}</a>)}</nav>
    <section className="v13-card overflow-hidden">
      <div className="flex flex-wrap items-end gap-2 px-5 pt-5">
        <input value={filters.q} onChange={(event) => setFilters({ ...filters, q: event.target.value })} placeholder={t("Cari pembelian")} className="v13-select w-56" />
        <select value={filters.kind} onChange={(event) => setFilters({ ...filters, kind: event.target.value })} className="v13-select"><option value="">{t("Semua jenis")}</option>{Object.entries(KIND_NAMES).map(([key, name]) => <option key={key} value={key}>{t(name)}</option>)}</select>
        <select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })} className="v13-select"><option value="">{t("Semua status")}</option>{Object.entries(STATUS).map(([key, [, name]]) => <option key={key} value={key}>{t(name)}</option>)}</select>
        <label className="text-xs text-[var(--ui-muted)]">{t("Dari")}<input type="date" value={filters.from} onChange={(event) => setFilters({ ...filters, from: event.target.value })} className="v13-select ml-1" /></label>
        <label className="text-xs text-[var(--ui-muted)]">{t("Sampai")}<input type="date" value={filters.to} onChange={(event) => setFilters({ ...filters, to: event.target.value })} className="v13-select ml-1" /></label>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={filters.followUp} onChange={(event) => setFilters({ ...filters, followUp: event.target.checked })} />{t("Perlu tindak lanjut")}</label>
        <button type="button" className="text-sm text-[var(--ui-muted)] underline" onClick={() => setFilters({ q: "", kind: "", status: "", from: "", to: "", followUp: false })}>{t("Reset filter")}</button>
      </div>
      <div className="overflow-x-auto"><table className="mt-3 w-full min-w-[720px] text-sm">
        <thead><tr className="text-left text-xs uppercase tracking-wide text-[var(--ui-muted)]">{["Pembelian", "Tanggal", "Nominal", "Pembayaran / Hasil", ""].map((head) => <th key={head} className="px-5 py-3 font-normal">{t(head)}</th>)}</tr></thead>
        <tbody>{items === null ? <tr><td colSpan={5} className="px-5 py-8 text-center text-[var(--ui-muted)]">{t("Memuat transaksi…")}</td></tr> : rows.length === 0 ? <tr><td colSpan={5} className="px-5 py-8 text-center text-[var(--ui-muted)]">{t("Belum ada transaksi.")}</td></tr> : rows.map((item) => { const [tone, name] = STATUS[item.status] || [undefined, item.status]; return <tr key={item.id} className="border-t border-[var(--ui-border)]" data-testid={`invoice-row-${item.id}`}>
          <td className="px-5 py-3"><div className="font-medium">{t(TYPE_NAMES[item.type] || "Pembayaran")}{item.tier ? ` · ${planName(item.tier)}` : ""}</div><div className="max-w-[300px] truncate text-xs text-[var(--ui-muted)]">{item.description || item.reference_id}</div></td>
          <td className="px-5 py-3">{day(item.created_at)}</td>
          <td className="px-5 py-3 tabular-nums">{idr(item.amount)}</td>
          <td className="px-5 py-3"><span className="v13-pill" data-tone={tone} data-testid={`payment-status-${item.status}`}>{t(name)}</span><div className="mt-1 text-xs text-[var(--ui-muted)]">{resultText(item, t)}</div></td>
          <td className="px-5 py-3 text-right">{["pending", "expired", "cancelled", "failed"].includes(item.status) && item.refund_status !== "refunded" && <button type="button" className="v13-plan-cta px-4 py-1.5 text-xs" style={{ width: "auto" }} onClick={() => payExisting(item.id)} disabled={loading} data-testid={`invoice-pay-${item.id}`}>{item.status === "pending" ? t("Bayar sekarang") : t("Coba bayar lagi")}</button>}</td>
        </tr>; })}</tbody>
      </table></div>
    </section>
    <TokenHistory />
    <p className="text-xs text-[var(--ui-muted)]" data-testid="invoices-legal-entity">{t("Ditagihkan oleh")} PT. Jeeres Group Indonesia · Jl. Sintang Pontianak RT 12 / RW 5, Kec. Sintang 78614 · NIB 2202260059749 · {t("Pembayaran diproses aman melalui Xendit.")}</p>
  </div>;
}
