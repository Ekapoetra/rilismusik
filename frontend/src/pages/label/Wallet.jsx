import React, { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { openXenditCheckout, pollPaymentUntilTerminal } from "@/api/payments";
import { Coins, RefreshCw, ShoppingCart, CalendarClock } from "lucide-react";

const fmtIDR = (n) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
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
  const [qty, setQty] = useState(5);
  const [loading, setLoading] = useState(false);
  const [pollingId, setPollingId] = useState(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    const { data } = await api.get("/token/wallet");
    setWallet(data);
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

  const buy = async () => {
    setErr(""); setMsg(""); setLoading(true);
    try {
      const { data } = await api.post("/payments/token-purchase", { quantity: qty });
      await openXenditCheckout(data.id);
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail || e.message));
      setLoading(false);
    }
  };

  const daily = wallet?.daily || {};
  return (
    <div className="space-y-7 max-w-4xl">
      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Dompet Token</div>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">Token</h1>
        <p className="text-sm text-zinc-400 mt-1">
          Token adalah opsi pembayaran alternatif — harga Rupiah tetap tersedia di semua checkout.
        </p>
      </div>
      {msg && <div className="rounded-2xl bg-emerald-500/15 text-emerald-300 px-4 py-3 text-sm">{pollingId && <RefreshCw className="inline w-4 h-4 mr-2 animate-spin" />}{msg}</div>}
      {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm">{err}</div>}

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
              onChange={(e) => setQty(Math.max(1, Math.min(500, parseInt(e.target.value, 10) || 1)))}
              className="rm-input mt-1 w-28" data-testid="wallet-buy-qty" />
          </div>
          <div className="text-sm text-zinc-300 pb-2.5" data-testid="wallet-buy-total">
            = {fmtIDR(qty * (wallet?.token_price_idr || 0))}
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
                <div className="text-xs text-zinc-500 truncate">{entry.note || entry.ref_type || "—"} • {entry.created_at?.slice(0, 16).replace("T", " ")}</div>
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
