import React, { useEffect, useState } from "react";
import { X } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { openXenditCheckout } from "@/api/payments";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { LabelAddonOrders } from "@/components/label/LabelAddonOrders";

const idr = (n) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
const ORDER_STATUS = { unpaid: ["mustard", "Menunggu pembayaran"], paid: ["blue", "Menunggu pemeriksaan"], in_progress: ["blue", "Sedang dikerjakan"], completed: ["green", "Selesai"], cancelled: [undefined, "Ditutup"] };

function OrderDialog({ product, releases, onClose }) {
  const { t } = useAppPreferences();
  const [releaseId, setReleaseId] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const { data } = await api.post(`/payments/service/${product.id}`, { release_id: releaseId || null, note });
      await openXenditCheckout(data.id);
    } catch (requestError) { setError(formatApiError(requestError.response?.data?.detail || requestError.message)); setBusy(false); }
  };
  return <div className="v13-dialog" role="dialog" aria-modal="true" aria-label={t("Pesan layanan")} data-testid="addon-order-dialog">
    <button type="button" className="v13-dialog-backdrop" aria-label={t("Tutup")} onClick={onClose} />
    <form className="v13-dialog-panel space-y-4" style={{ width: "min(520px, 100%)" }} onSubmit={submit}>
      <div className="flex items-start justify-between gap-4"><div><div className="v13-section-label">{t("Pesan layanan")}</div><h2 className="mt-1 text-2xl font-medium">{product.name}</h2></div><button type="button" className="v13-chevron" onClick={onClose} aria-label={t("Tutup")}><X /></button></div>
      <label className="block text-sm">{t("Rilisan")}<select value={releaseId} onChange={(event) => setReleaseId(event.target.value)} className="v13-select mt-1 w-full" style={{ height: 40 }}><option value="">{t("Tidak terkait rilisan")}</option>{releases.map((release) => <option key={release.id} value={release.id}>{release.release_title}</option>)}</select></label>
      <label className="block text-sm">{t("Arahan & kebutuhan")}<textarea value={note} onChange={(event) => setNote(event.target.value)} maxLength={2000} rows={4} className="mt-1 w-full rounded-[10px] bg-[var(--ui-raised)] p-3 text-sm outline-none" /></label>
      <div className="flex items-center justify-between text-sm"><span className="text-[var(--ui-muted)]">{t("Harga")}</span><strong className="text-xl font-normal">{idr(product.amount)}</strong></div>
      {error && <p role="alert" className="text-sm text-[var(--v13-urgent)]">{error}</p>}
      <button type="submit" className="v13-plan-cta" disabled={busy}>{busy ? t("Membuka Xendit…") : t("Lanjutkan pembayaran")}</button>
    </form>
  </div>;
}

// V13 page111: my orders plus the service catalogue.
export default function LabelAddons() {
  const { t } = useAppPreferences();
  const [tab, setTab] = useState("orders");
  const [products, setProducts] = useState(null);
  const [orders, setOrders] = useState(null);
  const [releases, setReleases] = useState([]);
  const [ordering, setOrdering] = useState(null);
  useEffect(() => {
    api.get("/payments/products").then(({ data }) => setProducts(data || [])).catch(() => setProducts([]));
    api.get("/label/service-orders").then(({ data }) => setOrders(data.items || [])).catch(() => setOrders([]));
    api.get("/releases/", { params: { limit: 200, include_revenue: false } }).then(({ data }) => setReleases(Array.isArray(data) ? data : [])).catch(() => {});
  }, []);
  return <div className="space-y-5" data-testid="label-addons">
    <header className="flex flex-wrap items-end justify-between gap-4"><div><div className="v13-section-label">{t("Layanan Tambahan")}</div><h1 className="mt-1 text-3xl">{t("Dukungan untuk setiap rilisan.")}</h1></div><button type="button" className="v13-plan-cta px-5" style={{ width: "auto" }} onClick={() => setTab("catalog")} data-testid="addon-order-start">{t("Pesan layanan")}</button></header>
    <nav className="v13-tabs" style={{ display: "inline-flex" }}>{[["orders", "Pesanan Saya"], ["catalog", "Pilihan Layanan"]].map(([key, name]) => <a key={key} href={`#${key}`} onClick={(event) => { event.preventDefault(); setTab(key); }} className={tab === key ? "is-active" : ""}>{t(name)}</a>)}</nav>
    {tab === "orders" ? <div className="space-y-5">
      <section className="v13-card"><div className="v13-card-head"><h2>{t("Pesanan layanan")}</h2></div><div className="v13-card-body">
        {orders === null ? <p role="status" className="py-4 text-sm text-[var(--ui-muted)]">{t("Memuat pesanan…")}</p> : orders.length === 0 ? <p className="py-4 text-sm text-[var(--ui-muted)]">{t("Belum ada pesanan layanan.")}</p> : orders.map((order) => { const [tone, name] = ORDER_STATUS[order.status] || [undefined, order.status]; const release = releases.find((item) => item.id === order.release_id); return <div key={order.id} className="v13-row"><div className="min-w-0"><div className="v13-row-title">{order.name}</div><div className="v13-row-sub truncate">{[release?.release_title, idr(order.amount), new Date(order.created_at).toLocaleDateString("id-ID", { timeZone: "Asia/Jakarta" })].filter(Boolean).join(" · ")}</div></div><span className="v13-pill" data-tone={tone}>{t(name)}</span></div>; })}
      </div></section>
      <LabelAddonOrders title={t("Layanan dari pengajuan rilisan")} showRelease />
    </div> : <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {products === null ? <p role="status" className="text-sm text-[var(--ui-muted)]">{t("Memuat layanan…")}</p> : products.length === 0 ? <p className="text-sm text-[var(--ui-muted)]">{t("Belum ada layanan tersedia.")}</p> : products.map((product) => <div key={product.id} className="v13-plan-card" style={{ minHeight: 220 }} data-testid={`addon-product-${product.id}`}>
        <h3 className="text-lg font-medium">{product.name}</h3><p className="mt-2 flex-1 text-sm text-[var(--ui-muted)]">{product.description}</p>
        <div className="mt-4 flex items-center justify-between"><strong className="text-xl font-normal">{idr(product.amount)}</strong><button type="button" className="v13-plan-cta px-4 py-2 text-sm" style={{ width: "auto" }} onClick={() => setOrdering(product)} data-testid={`addon-order-${product.id}`}>{t("Pesan")}</button></div>
      </div>)}
    </div>}
    {ordering && <OrderDialog product={ordering} releases={releases} onClose={() => setOrdering(null)} />}
  </div>;
}
