import React, { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { openXenditCheckout, pollPaymentUntilTerminal } from "@/api/payments";
import { fmtIDR, fmtDateTimeWib } from "@/utils/format";
import Notice from "@/components/shared/Notice";
import PageHeader from "@/components/shared/PageHeader";
import { Coins, RefreshCw, ShoppingCart, CalendarClock, Gift } from "lucide-react";

const KIND_LABELS = {
  purchase: "Pembelian", spend: "Pemakaian", refund: "Pengembalian",
  burn: "Hangus", admin_grant: "Penyesuaian Admin", "refund-skipped": "Kuota Kedaluwarsa",
};
const SOURCE_LABELS = { purchased: "Token Beli", daily: "Kuota Harian" };
const TIER_LABELS = {
  pay_per_release: "Pay Per Release", annual_normal: "Annual Normal",
  annual_vip: "Annual VIP", multi_label: "Multi Label",
};

export default function Wallet() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [wallet, setWallet] = useState(null);
  const [benefits, setBenefits] = useState(null);
  // Raw input string so clearing / retyping works; validated on submit.
  const [qty, setQty] = useState("5");
  // Token invoice created but checkout failed: retry the same invoice instead
  // of creating a duplicate one.
  const [pendingPurchase, setPendingPurchase] = useState(null); // { id, quantity }
  const [loading, setLoading] = useState(false);
  const [pollingId, setPollingId] = useState(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    const { data } = await api.get("/token/wallet");
    setWallet(data);
    api.get("/label/benefits").then((r) => setBenefits(r.data)).catch(() => {});
  }, []);
  useEffect(() => { load().catch((e) => setErr(formatApiError(e.response?.data?.detail || e.message))); }, [load]);

  useEffect(() => {
    const paymentId = searchParams.get("payment_id");
    if (!paymentId) return;
    let active = true;
    setPollingId(paymentId); setMsg("Mengonfirmasi pembayaran ke Xendit…");
    pollPaymentUntilTerminal(paymentId, () => {}, 75)
      .then(async (result) => {
        if (!active) return;
        if (result.status === "paid") setMsg("Pembayaran berhasil — token sudah masuk dompet.");
        else if (result.status === "pending") setMsg("Pembayaran masih diproses. Status akan diperbarui otomatis.");
        else setErr(`Pembayaran berstatus ${result.status}.`);
        setPollingId(null); setSearchParams({}); await load();
      })
      .catch((e) => active && setErr(formatApiError(e.response?.data?.detail || e.message)))
      .finally(() => active && setPollingId(null));
    return () => { active = false; };
  }, [searchParams, setSearchParams, load]);

  const qtyNum = parseInt(qty, 10);
  const buy = async () => {
    setErr(""); setMsg("");
    if (!Number.isFinite(qtyNum) || qtyNum < 1) { setErr("Jumlah token minimal 1."); return; }
    const quantity = Math.min(500, qtyNum);
    if (String(quantity) !== qty) setQty(String(quantity));
    setLoading(true);
    try {
      let paymentId = pendingPurchase?.quantity === quantity ? pendingPurchase.id : null;
      if (!paymentId) {
        const { data } = await api.post("/payments/token-purchase", { quantity });
        paymentId = data.id;
        setPendingPurchase({ id: paymentId, quantity });
      }
      await openXenditCheckout(paymentId);
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail || e.message));
      setLoading(false);
    }
  };

  const daily = wallet?.daily || {};
  return (
    <div className="space-y-7 max-w-4xl">
      <PageHeader eyebrow="Dompet Token" title="Token"
        sub="Token adalah opsi pembayaran alternatif — harga Rupiah tetap tersedia di semua checkout." />
      {msg && <Notice kind="success" testId="wallet-success">{pollingId && <RefreshCw className="inline w-4 h-4 mr-2 animate-spin" />}{msg}</Notice>}
      {err && <Notice kind="error" testId="wallet-error">{err}</Notice>}

      <div className="grid sm:grid-cols-2 gap-4">
        <div className="rm-card p-5" data-testid="wallet-balance-card">
          <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-zinc-500 font-bold"><Coins className="w-4 h-4 text-pink-300" /> Token Beli</div>
          <div className="font-display text-4xl font-extrabold mt-3" data-testid="wallet-balance">{wallet?.token_balance ?? "…"}</div>
          <div className="text-xs text-zinc-500 mt-1">Tidak pernah hangus. Dikembalikan bila rilisan ditolak.</div>
        </div>
        <div className="rm-card p-5" data-testid="wallet-daily-card">
          <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-zinc-500 font-bold"><CalendarClock className="w-4 h-4 text-amber-300" /> Kuota Harian Paket</div>
          <div className="font-display text-4xl font-extrabold mt-3" data-testid="wallet-daily-remaining">
            {wallet ? `${daily.remaining}/${daily.quota}` : "…"}
          </div>
          <div className="text-xs text-zinc-500 mt-1">
            {TIER_LABELS[daily.tier] || daily.tier || "—"} • reset setiap hari (WIB) • tidak menumpuk
          </div>
        </div>
      </div>

      {benefits && benefits.has_benefits && (
        <section className="rm-card p-5 space-y-3" data-testid="wallet-benefits-card">
          <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-zinc-500 font-bold"><Gift className="w-4 h-4 text-pink-300" /> Layanan Gratis Paket</div>
          {benefits.quota > 0 && (
            <div className="flex flex-wrap items-baseline gap-2">
              <span className="font-display text-2xl font-extrabold" data-testid="benefit-remaining">{benefits.remaining}/{benefits.quota}</span>
              <span className="text-xs text-zinc-500">tersisa bulan ini • reset tanggal 1 (WIB) • berlaku untuk WAMI & layanan tambahan</span>
            </div>
          )}
          {benefits.grants.length > 0 && (
            <ul className="space-y-1.5 text-xs">
              {benefits.grants.map((g) => (
                <li key={g.id} className="rm-glass rounded-lg px-3 py-2 flex items-center gap-2" data-testid={`benefit-grant-${g.id}`}>
                  <Gift className="w-3.5 h-3.5 text-amber-300" />
                  <span className="font-semibold text-amber-200">Bonus {g.quantity - g.used}×</span>
                  <span>{g.service === "wami" ? "Registrasi WAMI" : g.service === "any" ? "layanan gratis apa pun" : "layanan tambahan"}</span>
                  <span className="text-zinc-500">• berlaku s/d {fmtDateTimeWib(g.expires_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <section className="rm-card p-5 space-y-4" data-testid="wallet-buy-section">
        <div>
          <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Beli Token</div>
          <div className="text-sm text-zinc-400 mt-1">
            {wallet ? fmtIDR(wallet.token_price_idr) : "…"} per token — dibayar via Xendit seperti biasa.
          </div>
        </div>
        <div className="flex items-end gap-3 flex-wrap">
          <div>
            <label className="text-xs text-zinc-500">Jumlah token</label>
            <input type="number" min={1} max={500} value={qty}
              onChange={(e) => setQty(e.target.value)}
              className="rm-input mt-1 w-28" data-testid="wallet-buy-qty" />
          </div>
          <div className="text-sm text-zinc-300 pb-2.5" data-testid="wallet-buy-total">
            = {fmtIDR((Number.isFinite(qtyNum) && qtyNum > 0 ? Math.min(500, qtyNum) : 0) * (wallet?.token_price_idr || 0))}
          </div>
          <button className="rm-btn-primary flex items-center gap-2" onClick={buy} disabled={loading || !wallet} data-testid="wallet-buy-button">
            <ShoppingCart className="w-4 h-4" /> {loading ? "Membuka Xendit…" : "Beli via Xendit"}
          </button>
        </div>
      </section>

      <section className="space-y-3">
        <div><div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Riwayat</div><h2 className="font-display text-xl font-bold">Mutasi Token</h2></div>
        <div className="rm-card overflow-hidden" data-testid="wallet-ledger">
          {!wallet || wallet.ledger.length === 0 ? (
            <div className="p-10 text-center text-zinc-500 text-sm">Belum ada mutasi token.</div>
          ) : wallet.ledger.map((entry) => (
            <div key={entry.id} className="px-5 py-3.5 border-b border-white/5 last:border-0 flex items-center justify-between gap-3" data-testid={`ledger-${entry.id}`}>
              <div className="min-w-0">
                <div className="font-semibold text-sm">{KIND_LABELS[entry.kind] || entry.kind} • {SOURCE_LABELS[entry.source] || entry.source}</div>
                <div className="text-xs text-zinc-500 truncate">{entry.note || entry.ref_type || "—"} • {fmtDateTimeWib(entry.created_at)}</div>
              </div>
              <div className={`font-display font-extrabold ${entry.amount > 0 ? "text-emerald-300" : entry.amount < 0 ? "text-red-300" : "text-zinc-400"}`}>
                {entry.amount > 0 ? `+${entry.amount}` : entry.amount}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
