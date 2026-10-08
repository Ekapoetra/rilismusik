import React, { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { openXenditCheckout, pollPaymentUntilTerminal } from "@/api/payments";
import { CreditCard, Crown, Music, ShoppingBag, RefreshCw } from "lucide-react";
import { PlansDialog, useLabelPlan } from "@/components/v13/Plans";
import { planName } from "@/lib/plans";

const fmtIDR = (n) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
const TYPE_LABELS = { annual_subscription: "Paket Tahunan", pay_per_release: "Biaya Rilisan per Lagu", release_shortfall: "Kekurangan Paket Album", wami_addon: "WAMI Registrasi", custom_service: "Layanan Tambahan" };

export default function Invoices() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [items, setItems] = useState([]);
  const [products, setProducts] = useState([]);
  const [chooseOpen, setChooseOpen] = useState(false);
  const plan = useLabelPlan();
  const [loading, setLoading] = useState(false);
  const [pollingId, setPollingId] = useState(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    const [{ data: invoices }, { data: services }] = await Promise.all([
      api.get("/label/invoices"), api.get("/payments/products"),
    ]);
    setItems(invoices); setProducts(services);
  }, []);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const paymentId = searchParams.get("payment_id");
    if (!paymentId) return;
    let active = true;
    setPollingId(paymentId); setMsg("Mengonfirmasi pembayaran ke Xendit…");
    pollPaymentUntilTerminal(paymentId, () => {}, 75)
      .then(async (result) => {
        if (!active) return;
        if (result.status === "paid") setMsg("Pembayaran berhasil dikonfirmasi.");
        else if (result.status === "pending") setMsg("Pembayaran masih diproses. Status akan diperbarui otomatis.");
        else setErr(`Pembayaran berstatus ${result.status}.`);
        setPollingId(null); setSearchParams({}); await load();
      })
      .catch((e) => active && setErr(formatApiError(e.response?.data?.detail || e.message)))
      .finally(() => active && setPollingId(null));
    return () => { active = false; };
  }, [searchParams, setSearchParams, load]);

  const createAndCheckout = async (path, payload) => {
    setErr(""); setMsg(""); setLoading(true);
    try {
      const { data } = await api.post(path, payload);
      await openXenditCheckout(data.id);
    } catch (e) { setErr(formatApiError(e.response?.data?.detail || e.message)); setLoading(false); }
  };

  const payExisting = async (id) => {
    setErr(""); setLoading(true);
    try { await openXenditCheckout(id); }
    catch (e) { setErr(formatApiError(e.response?.data?.detail || e.message)); setLoading(false); }
  };

  return (
    <div className="space-y-7 max-w-5xl">
      <div className="flex justify-between items-center flex-wrap gap-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Invoice & Subscription</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter">Pembayaran</h1>
          <p className="text-sm text-zinc-400 mt-1">Checkout aman melalui Xendit Production. Status dikonfirmasi otomatis oleh sistem.</p>
        </div>
        <button className="rm-btn-primary flex items-center gap-2" onClick={() => setChooseOpen(true)} disabled={loading} data-testid="label-subscription-button">
          <Crown className="w-4 h-4" /> Ubah Paket
        </button>
      </div>
      {msg && <div className="rounded-2xl bg-emerald-500/15 text-emerald-300 px-4 py-3 text-sm" data-testid="payment-success-message">{pollingId && <RefreshCw className="inline w-4 h-4 mr-2 animate-spin" />}{msg}</div>}
      {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm" data-testid="payment-error-message">{err}</div>}

      <div className="rm-card p-4 text-xs text-zinc-400 flex flex-col md:flex-row md:items-center justify-between gap-2" data-testid="invoices-legal-entity">
        <div><div className="text-zinc-200 font-semibold">Ditagihkan oleh: PT. Jeeres Group Indonesia</div><div>Jl. Sintang Pontianak RT 12 / RW 5, Kec. Sintang 78614, Indonesia</div></div>
        <div className="text-zinc-500">NIB <span className="text-zinc-300 font-mono">2202260059749</span> • WA 085864137150</div>
      </div>

      {products.length > 0 && (
        <section className="space-y-3" data-testid="label-payment-services-section">
          <div><div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Layanan Tambahan</div><h2 className="font-display text-xl font-bold">Pilihan layanan</h2></div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {products.map((product) => (
              <div key={product.id} className="rm-card p-5 flex flex-col gap-3" data-testid={`payment-service-${product.id}`}>
                <ShoppingBag className="w-5 h-5 text-pink-300" />
                <div><div className="font-bold">{product.name}</div><div className="text-xs text-zinc-500 mt-1">{product.description}</div></div>
                <div className="font-display text-xl font-extrabold mt-auto">{fmtIDR(product.amount)}</div>
                <button className="rm-btn-ghost" disabled={loading} onClick={() => createAndCheckout(`/payments/service/${product.id}`, {})} data-testid={`payment-service-buy-${product.id}`}>Pesan via Xendit</button>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="space-y-3">
        <div><div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Riwayat</div><h2 className="font-display text-xl font-bold">Invoice</h2></div>
        <div className="rm-card overflow-hidden">
          {items.length === 0 ? <div className="p-10 text-center text-zinc-500 text-sm">Belum ada invoice.</div> : items.map((invoice) => {
            const Icon = invoice.type === "wami_addon" ? Music : invoice.type === "custom_service" ? ShoppingBag : CreditCard;
            const tier = invoice.tier ? ` — ${planName(invoice.tier)}` : "";
            return (
              <div key={invoice.id} className="px-5 py-4 border-b border-white/5 last:border-0 flex items-center justify-between gap-3 flex-wrap" data-testid={`invoice-row-${invoice.id}`}>
                <div className="flex items-center gap-3 min-w-0"><div className="w-10 h-10 rounded-xl bg-white/[0.06] text-zinc-400 grid place-items-center"><Icon className="w-4 h-4" /></div><div className="min-w-0"><div className="font-semibold text-sm">{TYPE_LABELS[invoice.type] || invoice.description}{tier}</div><div className="text-xs text-zinc-500 truncate">{invoice.xendit_session_id || invoice.reference_id || invoice.id} • {invoice.created_at?.slice(0, 10)}</div></div></div>
                <div className="flex items-center gap-3"><div className="font-display font-extrabold">{fmtIDR(invoice.amount)}</div><StatusPill status={invoice.status} />{["pending", "expired", "cancelled", "failed"].includes(invoice.status) && <button className="rm-btn-primary text-xs" onClick={() => payExisting(invoice.id)} disabled={loading} data-testid={`invoice-pay-${invoice.id}`}>{invoice.status === "pending" ? "Bayar via Xendit" : "Coba Bayar Lagi"}</button>}</div>
              </div>
            );
          })}
        </div>
      </section>

      {chooseOpen && <PlansDialog entitlements={plan} onClose={() => setChooseOpen(false)} />}
    </div>
  );
}

function StatusPill({ status }) {
  const style = { pending: "bg-amber-500/15 text-amber-300", paid: "bg-emerald-500/15 text-emerald-300", expired: "bg-white/[0.06] text-zinc-400", failed: "bg-red-500/15 text-red-300", cancelled: "bg-white/[0.06] text-zinc-400" };
  return <span className={`px-2.5 py-1 rounded-full text-xs font-bold capitalize ${style[status] || "bg-white/[0.06] text-zinc-400"}`} data-testid={`payment-status-${status}`}>{status}</span>;
}