import React, { useEffect, useState } from "react";
import { api, formatApiError } from "@/api/client";
import { CreditCard, Crown } from "lucide-react";

function fmtIDR(n) {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
}

export default function Invoices() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const load = async () => {
    const { data } = await api.get("/label/invoices");
    setItems(data);
  };
  useEffect(() => { load(); }, []);

  const createSub = async () => {
    setErr("");
    setLoading(true);
    try {
      await api.post("/payments/subscription");
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
          <div className="text-xs uppercase tracking-widest text-slate-500 font-bold">Invoice & Subscription</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter">Invoice</h1>
        </div>
        <button className="rm-btn-primary flex items-center gap-2" onClick={createSub} disabled={loading} data-testid="label-subscription-button">
          <Crown className="w-4 h-4" /> Beli Subscription Tahunan (Rp 500.000)
        </button>
      </div>
      {err && <div className="rounded-2xl bg-red-50 text-red-700 px-4 py-3 text-sm">{err}</div>}

      <div className="rm-card overflow-hidden">
        {items.length === 0 ? (
          <div className="p-10 text-center text-slate-500 text-sm">Belum ada invoice.</div>
        ) : items.map((i) => (
          <div key={i.id} className="px-5 py-4 border-b border-slate-50 last:border-0 flex items-center justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-600 grid place-items-center"><CreditCard className="w-4 h-4" /></div>
              <div className="min-w-0">
                <div className="font-semibold text-sm">{i.type === "annual_subscription" ? "Annual Subscription" : "Pay Per Release"}</div>
                <div className="text-xs text-slate-500">{i.xendit_invoice_id} • {i.created_at?.slice(0, 10)}</div>
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
        ))}
      </div>
    </div>
  );
}

function StatusPill({ s }) {
  const map = {
    pending: "bg-amber-50 text-amber-700",
    paid: "bg-emerald-50 text-emerald-700",
    expired: "bg-slate-100 text-slate-600",
    failed: "bg-red-50 text-red-700",
    cancelled: "bg-slate-100 text-slate-600",
  };
  return <span className={`px-2.5 py-1 rounded-full text-xs font-bold capitalize ${map[s] || "bg-slate-100 text-slate-600"}`}>{s}</span>;
}
