import React, { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { CreditCard, Crown, Disc3, Eye, RefreshCw, Plus, ShoppingBag, Pencil, Trash2 } from "lucide-react";
import PaymentDetailDialog from "./payments/PaymentDetailDialog";
import { formatIDR, PAYMENT_STATUS, PAYMENT_TYPES } from "./payments/paymentPresentation";
import { FinancialPeriodOverview, jakartaPeriod, monthLabel } from "@/components/admin/FinancialPeriodOverview";

const fmtIDR = formatIDR;

export default function AdminPayments() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [items, setItems] = useState([]);
  const [products, setProducts] = useState([]);
  const [status, setStatus] = useState("");
  const [ptype, setPtype] = useState("");
  const [syncing, setSyncing] = useState(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [form, setForm] = useState({ name: "", description: "", amount: "" });
  const [editingId, setEditingId] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [selectedPayment, setSelectedPayment] = useState(null);
  const [incomePeriod, setIncomePeriod] = useState(jakartaPeriod);
  const [incomeSummary, setIncomeSummary] = useState(null);
  const needsAction = searchParams.get("needs_action") === "true";
  const requestedPaymentId = searchParams.get("payment_id");
  const canManage = user?.role === "super_admin" || user?.role === "admin_finance";

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/admin/payments", { params: { status: status || undefined, ptype: ptype || undefined, needs_action: needsAction || undefined } });
      setItems(data);
      if (requestedPaymentId) setSelectedPayment(data.find((row) => row.id === requestedPaymentId) || null);
      else setSelectedPayment((current) => current ? data.find((row) => row.id === current.id) || current : null);
      if (canManage) {
        const { data: catalog } = await api.get("/payments/admin/products");
        setProducts(catalog);
      }
    } catch (error) { setErr(formatApiError(error.response?.data?.detail)); }
  }, [status, ptype, canManage, needsAction, requestedPaymentId]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    api.get("/admin/payments/summary", { params: incomePeriod })
      .then(({ data }) => setIncomeSummary(data))
      .catch((error) => setErr(formatApiError(error.response?.data?.detail)));
  }, [incomePeriod]);

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
      if (editingId) await api.patch(`/payments/admin/products/${editingId}`, { ...form, amount: Number(form.amount) });
      else await api.post("/payments/admin/products", { ...form, amount: Number(form.amount), active: true });
      setForm({ name: "", description: "", amount: "" }); setEditingId(null); setMsg(editingId ? "Layanan diperbarui." : "Layanan baru ditambahkan."); await load();
    } catch (error) { setErr(formatApiError(error.response?.data?.detail)); }
  };

  const toggleProduct = async (product) => {
    try { await api.patch(`/payments/admin/products/${product.id}`, { active: !product.active }); await load(); }
    catch (error) { setErr(formatApiError(error.response?.data?.detail)); }
  };
  const editProduct = (product) => { setEditingId(product.id); setForm({ name: product.name, description: product.description || "", amount: String(product.amount) }); };
  const deleteProduct = async () => { try { await api.delete(`/payments/admin/products/${deleteTarget.id}`); setDeleteTarget(null); setMsg("Layanan dihapus dari katalog aktif."); await load(); } catch (error) { setErr(formatApiError(error.response?.data?.detail)); } };

  const openPayment = (payment) => {
    setSelectedPayment(payment);
    const next = new URLSearchParams(searchParams); next.set("payment_id", payment.id); setSearchParams(next);
  };
  const closePayment = () => {
    setSelectedPayment(null);
    const next = new URLSearchParams(searchParams); next.delete("payment_id"); setSearchParams(next);
  };
  const toggleNeedsAction = () => {
    const next = new URLSearchParams(searchParams); next.delete("payment_id");
    if (needsAction) next.delete("needs_action"); else next.set("needs_action", "true");
    setSelectedPayment(null); setSearchParams(next);
  };

  return (
    <div className="space-y-7">
      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Keuangan</div>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">Pembayaran</h1>
        <p className="text-sm text-zinc-400 mt-1">Invoice Xendit dan tindak lanjut layanan setelah pembayaran.</p>
      </div>
      {msg && <div className="rounded-2xl bg-emerald-500/15 text-emerald-300 px-4 py-3 text-sm" data-testid="admin-payment-message">{msg}</div>}
      {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm" data-testid="admin-payment-error">{err}</div>}

      {incomeSummary && <FinancialPeriodOverview
        title="Pemasukan Xendit"
        description={`Semua invoice berstatus Dibayar pada ${monthLabel(incomePeriod.month, incomePeriod.year)}.`}
        year={incomePeriod.year} month={incomePeriod.month} years={incomeSummary.available_years}
        onYearChange={(year) => setIncomePeriod((current) => ({ ...current, year }))}
        onMonthChange={(month) => setIncomePeriod((current) => ({ ...current, month }))}
        metrics={[{
          key: "income", label: `Pemasukan ${monthLabel(incomePeriod.month, incomePeriod.year)}`,
          amount: incomeSummary.selected.amount_idr, count: incomeSummary.selected.count,
          yearAmount: incomeSummary.year_total.amount_idr, colorClass: "text-emerald-300", barClass: "bg-emerald-400",
        }]}
        monthly={incomeSummary.monthly.map((row) => ({ ...row, income: row.amount_idr }))}
        testIdPrefix="admin-payment-income"
      />}

      {canManage && (
        <section className="space-y-3" data-testid="admin-payment-products">
          <div><div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Katalog</div><h2 className="font-display text-xl font-bold">Layanan Tambahan</h2></div>
          <form onSubmit={addProduct} className="rm-card p-4 grid md:grid-cols-12 gap-3 items-end">
            <div className="md:col-span-3"><label className="rm-label">Nama layanan</label><input required className="rm-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="payment-product-name" /></div>
            <div className="md:col-span-4"><label className="rm-label">Deskripsi</label><input className="rm-input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} data-testid="payment-product-description" /></div>
            <div className="md:col-span-3"><label className="rm-label">Harga IDR</label><input required min="1000" type="number" className="rm-input" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} data-testid="payment-product-amount" /></div>
            <button className="rm-btn-primary md:col-span-2 flex items-center justify-center gap-2" type="submit" data-testid="payment-product-submit">{editingId ? <Pencil className="w-4 h-4" /> : <Plus className="w-4 h-4" />} {editingId ? "Simpan" : "Tambah"}</button>
            {editingId && <button type="button" className="rm-btn-ghost md:col-span-12" onClick={() => { setEditingId(null); setForm({ name: "", description: "", amount: "" }); }} data-testid="payment-product-edit-cancel">Batal Edit</button>}
          </form>
          {products.length > 0 && <div className="grid md:grid-cols-3 gap-3">{products.map((product) => (
            <div key={product.id} className="rm-card p-4 flex items-start gap-3" data-testid={`admin-payment-product-${product.id}`}>
              <ShoppingBag className="w-5 h-5 text-pink-300 mt-1" /><div className="flex-1"><div className="font-bold">{product.name}</div><div className="text-xs text-zinc-500">{fmtIDR(product.amount)}</div></div>
              <div className="flex gap-1"><button className="grid h-8 w-8 place-items-center rounded-md text-zinc-300 hover:bg-white/10" title="Edit layanan" onClick={() => editProduct(product)} data-testid={`payment-product-edit-${product.id}`}><Pencil className="w-3.5 h-3.5" /></button><button className="grid h-8 w-8 place-items-center rounded-md text-red-300 hover:bg-red-500/15" title="Hapus layanan" onClick={() => setDeleteTarget(product)} data-testid={`payment-product-delete-${product.id}`}><Trash2 className="w-3.5 h-3.5" /></button><button className="rm-btn-ghost text-xs" onClick={() => toggleProduct(product)} data-testid={`payment-product-toggle-${product.id}`}>{product.active ? "Nonaktifkan" : "Aktifkan"}</button></div>
            </div>
          ))}</div>}
        </section>
      )}
      {deleteTarget && <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4" onClick={() => setDeleteTarget(null)}><div className="rm-glass-strong w-full max-w-md rounded-[24px] border border-red-500/30 p-6 space-y-4" onClick={(event) => event.stopPropagation()} data-testid="payment-product-delete-modal"><h3 className="font-display text-xl font-extrabold text-red-200">Hapus Layanan</h3><p className="text-sm text-zinc-300">Hapus <b>{deleteTarget.name}</b> dari katalog? Layanan yang sudah dipakai invoice lama akan diarsipkan agar histori tetap utuh.</p><div className="flex justify-end gap-2"><button className="rm-btn-ghost" onClick={() => setDeleteTarget(null)} data-testid="payment-product-delete-cancel">Batal</button><button className="rm-btn-primary" onClick={deleteProduct} data-testid="payment-product-delete-confirm">Hapus</button></div></div></div>}

      <section className="space-y-3">
        <div className="rm-card p-4 flex gap-3 flex-wrap items-end">
          <div className="min-w-[190px]"><label className="rm-label">Status</label><select className="rm-input" value={status} onChange={(e) => setStatus(e.target.value)} data-testid="admin-payments-status"><option value="">Semua</option><option value="pending">Menunggu Pembayaran</option><option value="paid">Dibayar</option><option value="expired">Kedaluwarsa</option><option value="failed">Gagal</option><option value="cancelled">Dibatalkan</option></select></div>
          <div className="min-w-[190px]"><label className="rm-label">Tipe</label><select className="rm-input" value={ptype} onChange={(e) => setPtype(e.target.value)} data-testid="admin-payments-type"><option value="">Semua</option><option value="pay_per_release">Pay Per Release</option><option value="annual_subscription">Langganan Tahunan</option><option value="wami_addon">WAMI</option><option value="custom_service">Layanan Tambahan</option></select></div>
          <button type="button" className={needsAction ? "rm-btn-primary" : "rm-btn-ghost"} onClick={toggleNeedsAction} data-testid="admin-payments-needs-action-filter">{needsAction ? "Menampilkan yang perlu ditindaklanjuti" : "Perlu Ditindaklanjuti"}</button>
        </div>
        <div className="rm-card overflow-hidden">
          <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5"><div className="col-span-3">Invoice</div><div className="col-span-3">Tipe</div><div className="col-span-2">Nominal</div><div className="col-span-2">Status</div><div className="col-span-2 text-right">Aksi</div></div>
          {items.length === 0 ? <div className="p-8 text-center text-zinc-500 text-sm" data-testid="admin-payments-empty">{needsAction ? "Tidak ada pembayaran yang perlu ditindaklanjuti." : "Belum ada invoice."}</div> : items.map((payment) => (
            <div key={payment.id} role="button" tabIndex={0} onClick={() => openPayment(payment)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") openPayment(payment); }} className="px-5 py-4 grid grid-cols-12 gap-3 items-center border-b border-white/5 last:border-0 cursor-pointer transition-colors hover:bg-white/[0.035] focus:outline-none focus:ring-1 focus:ring-inset focus:ring-rose-400/50" data-testid={`admin-payment-row-${payment.id}`}>
              <div className="col-span-12 md:col-span-3 flex items-center gap-3 min-w-0"><div className="w-9 h-9 rounded-md bg-white/[0.06] text-zinc-400 grid place-items-center"><CreditCard className="w-4 h-4" /></div><div className="min-w-0"><div className="font-semibold text-sm truncate" data-testid={`admin-payment-invoice-${payment.id}`}>{payment.reference_id || payment.id}</div><div className="text-xs text-zinc-500 truncate" data-testid={`admin-payment-label-${payment.id}`}>{payment.label_name}</div></div></div>
              <div className="col-span-6 md:col-span-3 text-sm flex items-center gap-2" data-testid={`admin-payment-type-${payment.id}`}>{payment.type === "annual_subscription" ? <Crown className="w-4 h-4 text-amber-500" /> : <Disc3 className="w-4 h-4 text-rose-500" />}{PAYMENT_TYPES[payment.type] || payment.type}</div>
              <div className="col-span-6 md:col-span-2 font-display font-extrabold" data-testid={`admin-payment-amount-${payment.id}`}>{fmtIDR(payment.amount)}</div>
              <div className="col-span-6 md:col-span-2"><span data-testid={`admin-payment-status-${payment.id}`} className={`px-2.5 py-1 rounded-full text-xs font-bold ${payment.status === "paid" ? "bg-emerald-500/15 text-emerald-300" : payment.status === "pending" ? "bg-amber-500/15 text-amber-300" : "bg-white/[0.06] text-zinc-400"}`}>{PAYMENT_STATUS[payment.status] || payment.status}</span>{payment.admin_action_required && <div className="mt-1 text-[11px] font-semibold text-rose-300" data-testid={`admin-payment-action-required-${payment.id}`}>Perlu ditindaklanjuti</div>}</div>
              <div className="col-span-6 md:col-span-2 flex justify-end gap-2"><button type="button" className="rm-btn-ghost text-xs inline-flex items-center gap-1" onClick={(event) => { event.stopPropagation(); openPayment(payment); }} data-testid={`admin-payment-detail-${payment.id}`}><Eye className="w-3.5 h-3.5" /> Detail</button>{payment.status === "pending" && payment.xendit_session_id && <button type="button" className="rm-btn-ghost text-xs inline-flex items-center gap-1" onClick={(event) => { event.stopPropagation(); sync(payment.id); }} disabled={syncing === payment.id} data-testid={`admin-payment-sync-${payment.id}`}><RefreshCw className={`w-3.5 h-3.5 ${syncing === payment.id ? "animate-spin" : ""}`} /> Sinkronkan</button>}</div>
            </div>
          ))}
        </div>
      </section>
      <PaymentDetailDialog payment={selectedPayment} onClose={closePayment} onUpdated={(updated) => { setSelectedPayment(updated); setItems((current) => current.map((row) => row.id === updated.id ? updated : row)); }} onMessage={(message) => { setMsg(message); load(); }} />
    </div>
  );
}