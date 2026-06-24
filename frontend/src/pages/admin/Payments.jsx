import React, { useEffect, useState } from "react";
import { api } from "@/api/client";
import { CreditCard, Crown, Disc3 } from "lucide-react";

function fmtIDR(n) {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
}

export default function AdminPayments() {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("");
  const [ptype, setPtype] = useState("");

  const load = async () => {
    const { data } = await api.get("/admin/payments", { params: { status: status || undefined, ptype: ptype || undefined } });
    setItems(data);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [status, ptype]);

  const mockPay = async (id) => {
    await api.post(`/payments/mock-pay/${id}`);
    load();
  };

  return (
    <div className="space-y-5">
      <div>
        <div className="text-xs uppercase tracking-widest text-slate-500 font-bold">Finance</div>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">Xendit Payments</h1>
        <p className="text-sm text-slate-600 mt-1">Pantau semua invoice (Pay Per Release + Annual Subscription). Mode MOCK.</p>
      </div>
      <div className="rm-card p-4 flex gap-3 flex-wrap items-end">
        <div className="min-w-[160px]">
          <label className="rm-label">Status</label>
          <select className="rm-input" value={status} onChange={(e) => setStatus(e.target.value)} data-testid="admin-payments-status">
            <option value="">Semua</option>
            <option value="pending">Pending</option>
            <option value="paid">Paid</option>
            <option value="expired">Expired</option>
            <option value="failed">Failed</option>
          </select>
        </div>
        <div className="min-w-[180px]">
          <label className="rm-label">Tipe</label>
          <select className="rm-input" value={ptype} onChange={(e) => setPtype(e.target.value)} data-testid="admin-payments-type">
            <option value="">Semua</option>
            <option value="pay_per_release">Pay Per Release</option>
            <option value="annual_subscription">Annual Subscription</option>
          </select>
        </div>
      </div>
      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-slate-500 bg-slate-50/60 border-b border-slate-100">
          <div className="col-span-3">Invoice</div>
          <div className="col-span-3">Tipe</div>
          <div className="col-span-2">Nominal</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-2 text-right">Aksi</div>
        </div>
        {items.length === 0 ? <div className="p-8 text-center text-slate-500 text-sm">Belum ada invoice.</div> : items.map((i) => (
          <div key={i.id} className="px-5 py-4 grid grid-cols-12 gap-3 items-center border-b border-slate-50 last:border-0">
            <div className="col-span-12 md:col-span-3 flex items-center gap-3 min-w-0">
              <div className="w-9 h-9 rounded-xl bg-slate-100 text-slate-600 grid place-items-center"><CreditCard className="w-4 h-4" /></div>
              <div className="min-w-0">
                <div className="font-semibold text-sm truncate">{i.xendit_invoice_id}</div>
                <div className="text-xs text-slate-500 truncate">{i.created_at?.slice(0, 16)?.replace("T", " ")}</div>
              </div>
            </div>
            <div className="col-span-6 md:col-span-3 text-sm capitalize flex items-center gap-2">
              {i.type === "annual_subscription" ? <Crown className="w-4 h-4 text-amber-600" /> : <Disc3 className="w-4 h-4 text-rose-500" />}
              {i.type.replace(/_/g, " ")}
            </div>
            <div className="col-span-6 md:col-span-2 font-display font-extrabold tracking-tight">{fmtIDR(i.amount)}</div>
            <div className="col-span-6 md:col-span-2"><span className={`px-2.5 py-1 rounded-full text-xs font-bold capitalize ${i.status === "paid" ? "bg-emerald-50 text-emerald-700" : i.status === "pending" ? "bg-amber-50 text-amber-700" : "bg-slate-100 text-slate-600"}`}>{i.status}</span></div>
            <div className="col-span-6 md:col-span-2 text-right">
              {i.status === "pending" && <button className="rm-btn-primary text-xs" onClick={() => mockPay(i.id)} data-testid={`admin-mock-pay-${i.id}`}>Mark Paid (MOCK)</button>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
