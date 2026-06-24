import React, { useEffect, useState } from "react";
import { api, formatApiError } from "@/api/client";
import { CreditCard, Crown, Star, Music } from "lucide-react";

function fmtIDR(n) {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
}

const TIERS = [
  {
    key: "annual_normal",
    name: "Annual Normal",
    price: 350000,
    desc: "Unlimited release tanpa biaya per release.",
    icon: Crown,
    perks: ["Submit unlimited release", "Prioritas review", "Tanpa biaya per release"],
  },
  {
    key: "annual_vip",
    name: "Annual VIP",
    price: 500000,
    desc: "Plus GRATIS WAMI + konten promosi.",
    icon: Star,
    vip: true,
    perks: [
      "Submit unlimited release",
      "Prioritas review",
      "GRATIS daftar LMKN-WAMI semua lagu",
      "GRATIS konten promosi (JPG)",
      "Status WAMI real-time",
    ],
  },
];

const INVOICE_TYPE_LABELS = {
  annual_subscription: "Annual Subscription",
  pay_per_release: "Pay Per Release",
  wami_addon: "WAMI Registrasi",
};

export default function Invoices() {
  const [items, setItems] = useState([]);
  const [chooseOpen, setChooseOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const load = async () => {
    const { data } = await api.get("/label/invoices");
    setItems(data);
  };
  useEffect(() => { load(); }, []);

  const createSub = async (tier) => {
    setErr(""); setLoading(true);
    try {
      await api.post("/payments/subscription", { tier });
      setChooseOpen(false);
      await load();
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setLoading(false); }
  };

  const pay = async (id) => {
    setErr("");
    try {
      await api.post(`/payments/mock-pay/${id}`);
      await load();
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
  };

  return (
    <div className="space-y-5 max-w-5xl">
      <div className="flex justify-between items-center flex-wrap gap-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Invoice & Subscription</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter">Invoice</h1>
          <p className="text-sm text-zinc-400 mt-1">Beli paket tahunan untuk submit unlimited release atau bayar per rilis.</p>
        </div>
        <button
          className="rm-btn-primary flex items-center gap-2"
          onClick={() => setChooseOpen(true)}
          disabled={loading}
          data-testid="label-subscription-button"
        >
          <Crown className="w-4 h-4" /> Pilih Paket Tahunan
        </button>
      </div>
      {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm">{err}</div>}

      <div className="rm-card overflow-hidden">
        {items.length === 0 ? (
          <div className="p-10 text-center text-zinc-500 text-sm">Belum ada invoice.</div>
        ) : items.map((i) => {
          const IconCmp = i.type === "wami_addon" ? Music : CreditCard;
          const label = INVOICE_TYPE_LABELS[i.type] || i.type;
          const tierSuffix = i.tier ? ` — ${i.tier === "annual_vip" ? "VIP" : "Normal"}` : "";
          return (
            <div key={i.id} className="px-5 py-4 border-b border-white/5 last:border-0 flex items-center justify-between gap-3 flex-wrap" data-testid={`invoice-row-${i.id}`}>
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-10 h-10 rounded-xl bg-white/[0.06] text-zinc-400 grid place-items-center"><IconCmp className="w-4 h-4" /></div>
                <div className="min-w-0">
                  <div className="font-semibold text-sm">{label}{tierSuffix}</div>
                  <div className="text-xs text-zinc-500">{i.xendit_invoice_id} • {i.created_at?.slice(0, 10)}</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="font-display font-extrabold tracking-tight">{fmtIDR(i.amount)}</div>
                <StatusPill s={i.status} />
                {i.status === "pending" && (
                  <button className="rm-btn-primary text-xs" onClick={() => pay(i.id)} data-testid={`invoice-pay-${i.id}`}>Bayar (MOCK)</button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Tier choice modal */}
      {chooseOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 grid place-items-center p-4" onClick={() => setChooseOpen(false)}>
          <div onClick={(e) => e.stopPropagation()} className="w-full max-w-3xl rm-glass-strong rounded-[24px] p-6 space-y-4">
            <div>
              <h3 className="font-display font-extrabold text-2xl tracking-tighter">Pilih Paket Subscription</h3>
              <p className="text-sm text-zinc-400 mt-1">Bandingkan benefit Normal vs VIP. Anda bisa upgrade kapan saja.</p>
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              {TIERS.map((t) => {
                const Icon = t.icon;
                return (
                  <div
                    key={t.key}
                    className={`rounded-2xl p-5 flex flex-col ${t.vip ? "rm-glass-strong border border-pink-500/30" : "rm-glass"}`}
                  >
                    <div className="flex items-center gap-2">
                      <Icon className={`w-5 h-5 ${t.vip ? "text-pink-300" : "text-zinc-400"}`} />
                      <span className="text-xs uppercase tracking-widest font-bold text-zinc-400">{t.name}</span>
                    </div>
                    <div className="mt-3 flex items-baseline gap-1">
                      <span className={`font-display text-3xl font-extrabold tracking-tighter ${t.vip ? "rm-gradient-text" : ""}`}>{fmtIDR(t.price)}</span>
                      <span className="text-xs text-zinc-500">/ tahun</span>
                    </div>
                    <p className="text-xs text-zinc-400 mt-1">{t.desc}</p>
                    <ul className="mt-4 space-y-1.5 text-xs text-zinc-200 flex-1">
                      {t.perks.map((p, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className={`mt-0.5 font-bold ${t.vip ? "rm-gradient-text" : "text-zinc-400"}`}>✓</span>{p}
                        </li>
                      ))}
                    </ul>
                    <button
                      onClick={() => createSub(t.key)}
                      disabled={loading}
                      className={`mt-5 ${t.vip ? "rm-btn-primary" : "rm-btn-ghost"}`}
                      data-testid={`label-pick-tier-${t.key}`}
                    >
                      {loading ? "Membuat invoice…" : `Pilih ${t.name}`}
                    </button>
                  </div>
                );
              })}
            </div>
            <button className="rm-btn-ghost w-full text-sm" onClick={() => setChooseOpen(false)}>Tutup</button>
          </div>
        </div>
      )}
    </div>
  );
}

function StatusPill({ s }) {
  const map = {
    pending: "bg-amber-500/15 text-amber-300",
    paid: "bg-emerald-500/15 text-emerald-300",
    expired: "bg-white/[0.06] text-zinc-400",
    failed: "bg-red-500/15 text-red-300",
    cancelled: "bg-white/[0.06] text-zinc-400",
  };
  return <span className={`px-2.5 py-1 rounded-full text-xs font-bold capitalize ${map[s] || "bg-white/[0.06] text-zinc-400"}`}>{s}</span>;
}
