import React, { useCallback, useEffect, useState } from "react";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { CreditCard, Crown, Disc3, RefreshCw, Plus, ShoppingBag } from "lucide-react";

const fmtIDR = (n) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);

export default function AdminPayments() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [products, setProducts] = useState([]);
  const [status, setStatus] = useState("");
  const [ptype, setPtype] = useState("");
  const [syncing, setSyncing] = useState(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [form, setForm] = useState({ name: "", description: "", amount: "" });
  const canManage = user?.role === "super_admin" || user?.role === "admin_finance";

  const load = useCallback(async () => {
    const { data } = await api.get("/admin/payments", { params: { status: status || undefined, ptype: ptype || undefined } });
    setItems(data);
    if (canManage) {
      const { data: catalog } = await api.get("/payments/admin/products");
      setProducts(catalog);
    }
  }, [status, ptype, canManage]);
  useEffect(() => { load(); }, [load]);

  const sync = async (id) => {
    setSyncing(id); setErr(""); setMsg("");
    try {
      const { data } = await api.get(`/payments/${id}/status`);
      setMsg(`Status ${id.slice(0, 8)}: ${data.status}`); await load();
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setSyncing(null); }
  };

  const addProduct = async (e) => {
    e.preventDefault(); setErr(""); setMsg("");
    try {
      await api.post("/payments/admin/products", { ...form, amount: Number(form.amount), active: true });
      setForm({ name: "", description: "", amount: "" }); setMsg("Layanan baru ditambahkan."); await load();
    } catch (error) { setErr(formatApiError(error.response?.data?.detail)); }
  };

  const toggleProduct = async (product) => {
    try { await api.patch(`/payments/admin/products/${product.id}`, { active: !product.active }); await load(); }
    catch (error) { setErr(formatApiError(error.response?.data?.detail)); }
  };

  return (
    <div className="space-y-7">
      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Finance</div>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">Xendit Payments</h1>
        <p className="text-sm text-zinc-400 mt-1">Production Payment Sessions • konfirmasi status melalui polling backend.</p>
      </div>
      {msg && <div className="rounded-2xl bg-emerald-500/15 text-emerald-300 px-4 py-3 text-sm" data-testid="admin-payment-message">{msg}</div>}
      {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm" data-testid="admin-payment-error">{err}</div>}

      {canManage && (
        <section className="space-y-3" data-testid="admin-payment-products">
          <div><div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Katalog</div><h2 className="font-display text-xl font-bold">Layanan Tambahan</h2></div>
          <form onSubmit={addProduct} className="rm-card p-4 grid md:grid-cols-12 gap-3 items-end">
            <div className="md:col-span-3"><label className="rm-label">Nama layanan</label><input required className="rm-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="payment-product-name" /></div>
            <div className="md:col-span-4"><label className="rm-label">Deskripsi</label><input className="rm-input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} data-testid="payment-product-description" /></div>
            <div className="md:col-span-3"><label className="rm-label">Harga IDR</label><input required min="1000" type="number" className="rm-input" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} data-testid="payment-product-amount" /></div>
            <button className="rm-btn-primary md:col-span-2 flex items-center justify-center gap-2" type="submit" data-testid="payment-product-submit"><Plus className="w-4 h-4" /> Tambah</button>
          </form>
          {products.length > 0 && <div className="grid md:grid-cols-3 gap-3">{products.map((product) => (
            <div key={product.id} className="rm-card p-4 flex items-start gap-3" data-testid={`admin-payment-product-${product.id}`}>
              <ShoppingBag className="w-5 h-5 text-pink-300 mt-1" /><div className="flex-1"><div className="font-bold">{product.name}</div><div className="text-xs text-zinc-500">{fmtIDR(product.amount)}</div></div>
              <button className="rm-btn-ghost text-xs" onClick={() => toggleProduct(product)} data-testid={`payment-product-toggle-${product.id}`}>{product.active ? "Nonaktifkan" : "Aktifkan"}</button>
            </div>
          ))}</div>}
        </section>
      )}

      <section className="space-y-3">
        <div className="rm-card p-4 flex gap-3 flex-wrap items-end">
          <div className="min-w-[160px]"><label className="rm-label">Status</label><select className="rm-input" value={status} onChange={(e) => setStatus(e.target.value)} data-testid="admin-payments-status"><option value="">Semua</option><option value="pending">Pending</option><option value="paid">Paid</option><option value="expired">Expired</option><option value="failed">Failed</option><option value="cancelled">Cancelled</option></select></div>
          <div className="min-w-[180px]"><label className="rm-label">Tipe</label><select className="rm-input" value={ptype} onChange={(e) => setPtype(e.target.value)} data-testid="admin-payments-type"><option value="">Semua</option><option value="pay_per_release">Pay Per Release</option><option value="annual_subscription">Annual Subscription</option><option value="wami_addon">WAMI</option><option value="custom_service">Layanan Tambahan</option></select></div>
        </div>
        <div className="rm-card overflow-hidden">
          <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5"><div className="col-span-3">Invoice</div><div className="col-span-3">Tipe</div><div className="col-span-2">Nominal</div><div className="col-span-2">Status</div><div className="col-span-2 text-right">Aksi</div></div>
          {items.length === 0 ? <div className="p-8 text-center text-zinc-500 text-sm">Belum ada invoice.</div> : items.map((payment) => (
            <div key={payment.id} className="px-5 py-4 grid grid-cols-12 gap-3 items-center border-b border-white/5 last:border-0" data-testid={`admin-payment-row-${payment.id}`}>
              <div className="col-span-12 md:col-span-3 flex items-center gap-3 min-w-0"><div className="w-9 h-9 rounded-xl bg-white/[0.06] text-zinc-400 grid place-items-center"><CreditCard className="w-4 h-4" /></div><div className="min-w-0"><div className="font-semibold text-sm truncate">{payment.xendit_session_id || payment.reference_id || payment.id}</div><div className="text-xs text-zinc-500 truncate">{payment.created_at?.slice(0, 16)?.replace("T", " ")}</div></div></div>
              <div className="col-span-6 md:col-span-3 text-sm capitalize flex items-center gap-2">{payment.type === "annual_subscription" ? <Crown className="w-4 h-4 text-amber-500" /> : <Disc3 className="w-4 h-4 text-rose-500" />}{payment.type.replace(/_/g, " ")}</div>
              <div className="col-span-6 md:col-span-2 font-display font-extrabold">{fmtIDR(payment.amount)}</div>
              <div className="col-span-6 md:col-span-2"><span className={`px-2.5 py-1 rounded-full text-xs font-bold capitalize ${payment.status === "paid" ? "bg-emerald-500/15 text-emerald-300" : payment.status === "pending" ? "bg-amber-500/15 text-amber-300" : "bg-white/[0.06] text-zinc-400"}`}>{payment.status}</span></div>
              <div className="col-span-6 md:col-span-2 text-right">{payment.status === "pending" && payment.xendit_session_id && <button className="rm-btn-ghost text-xs inline-flex items-center gap-1" onClick={() => sync(payment.id)} disabled={syncing === payment.id} data-testid={`admin-payment-sync-${payment.id}`}><RefreshCw className={`w-3.5 h-3.5 ${syncing === payment.id ? "animate-spin" : ""}`} /> Sinkronkan</button>}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}