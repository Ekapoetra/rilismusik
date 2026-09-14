import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { toast } from "@/components/ui/sonner";
import { Sparkles, ExternalLink, RefreshCw, Loader2, Plus, Pencil, Trash2, ShoppingBag, UploadCloud } from "lucide-react";

const STATUS_STYLE = {
  pending: "bg-zinc-500/15 text-zinc-300",
  in_progress: "bg-amber-500/15 text-amber-300",
  delivered: "bg-sky-500/15 text-sky-300",
  completed: "bg-emerald-500/15 text-emerald-300",
  cancelled: "bg-red-500/15 text-red-300",
};
const NEXT_ACTIONS = {
  pending: [["in_progress", "Mulai Proses"], ["cancelled", "Batalkan"]],
  in_progress: [["delivered", "Tandai Terkirim"], ["cancelled", "Batalkan"]],
  delivered: [["completed", "Tandai Selesai"]],
  completed: [],
  cancelled: [],
};
const FILTERS = [["all", "Semua"], ["pending", "Menunggu"], ["in_progress", "Diproses"], ["delivered", "Terkirim"], ["completed", "Selesai"], ["cancelled", "Dibatalkan"]];

export default function AdminAddonOrders() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission("addon.manage");
  const [data, setData] = useState({ items: [], counts: {}, labels: {} });
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [busy, setBusy] = useState("");
  const [backfilling, setBackfilling] = useState(false);
  const [editing, setEditing] = useState(null);
  const [deliveryUrl, setDeliveryUrl] = useState("");
  const [deliveryNote, setDeliveryNote] = useState("");
  const [deliveryFile, setDeliveryFile] = useState(null);
  // Catalog state
  const [products, setProducts] = useState([]);
  const [pform, setPform] = useState({ name: "", description: "", amount: "", delivery_type: "link" });
  const [editingProduct, setEditingProduct] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get("/admin/addon-orders", { params: filter === "all" ? {} : { status: filter } });
      setData(r.data);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail) || "Gagal memuat"); }
    finally { setLoading(false); }
  }, [filter]);

  const loadProducts = useCallback(async () => {
    if (!canManage) return;
    try { const r = await api.get("/payments/admin/products"); setProducts(r.data || []); }
    catch (e) { /* silent */ }
  }, [canManage]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { loadProducts(); }, [loadProducts]);

  const changeStatus = async (order, status) => {
    setBusy(order.id);
    try {
      await api.patch(`/admin/addon-orders/${order.id}/status`, { status });
      toast.success("Status diperbarui");
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail) || "Gagal"); }
    finally { setBusy(""); }
  };

  const openDelivery = (order) => {
    setEditing(order);
    setDeliveryUrl(order.delivery_url && !order.delivery_filename ? order.delivery_url : "");
    setDeliveryNote(order.delivery_note || "");
    setDeliveryFile(null);
  };
  const saveDelivery = async () => {
    setBusy(editing.id);
    try {
      if (editing.delivery_type === "file") {
        if (!deliveryFile) { toast.error("Pilih file hasil untuk diunggah"); setBusy(""); return; }
        const fd = new FormData(); fd.append("file", deliveryFile);
        await api.post(`/admin/addon-orders/${editing.id}/delivery-file`, fd, { headers: { "Content-Type": "multipart/form-data" } });
        toast.success("File hasil diunggah & label diberi tahu");
      } else {
        await api.patch(`/admin/addon-orders/${editing.id}/delivery`, { delivery_url: deliveryUrl, delivery_note: deliveryNote });
        toast.success("Hasil tersimpan & label diberi tahu");
      }
      setEditing(null);
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail) || "Gagal"); }
    finally { setBusy(""); }
  };

  const submitProduct = async (e) => {
    e.preventDefault();
    try {
      const payload = { ...pform, amount: Number(pform.amount) };
      if (editingProduct) await api.patch(`/payments/admin/products/${editingProduct}`, payload);
      else await api.post("/payments/admin/products", { ...payload, active: true });
      toast.success(editingProduct ? "Layanan diperbarui" : "Layanan baru ditambahkan");
      setPform({ name: "", description: "", amount: "", delivery_type: "link" }); setEditingProduct(null);
      await loadProducts();
    } catch (err) { toast.error(formatApiError(err.response?.data?.detail) || "Gagal"); }
  };
  const editProduct = (p) => { setEditingProduct(p.id); setPform({ name: p.name, description: p.description || "", amount: String(p.amount), delivery_type: p.delivery_type || "link" }); };
  const toggleProduct = async (p) => { try { await api.patch(`/payments/admin/products/${p.id}`, { active: !p.active }); await loadProducts(); } catch (err) { toast.error(formatApiError(err.response?.data?.detail)); } };
  const removeProduct = async () => { try { await api.delete(`/payments/admin/products/${deleteTarget.id}`); setDeleteTarget(null); toast.success("Layanan dihapus/diarsipkan"); await loadProducts(); } catch (err) { toast.error(formatApiError(err.response?.data?.detail)); } };

  const backfill = async () => {
    setBackfilling(true);
    try {
      const r = await api.post("/admin/addon-orders/backfill");
      toast.success(`Backfill selesai: ${r.data.orders_created} order dibuat dari ${r.data.scanned_payments} pembayaran`);
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail) || "Gagal"); }
    finally { setBackfilling(false); }
  };

  const counts = data.counts || {};
  return (
    <div className="mx-auto max-w-6xl space-y-6" data-testid="admin-addon-orders-page">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-[#FF7FC0]" />
          <div>
            <h1 className="font-display text-2xl font-extrabold tracking-tight">Layanan Tambahan</h1>
            <p className="text-sm text-zinc-500">Kelola add-on berbayar (visualizer, link preset, dll) dari rilisan.</p>
          </div>
        </div>
        <button onClick={backfill} disabled={backfilling} className="rm-btn-ghost inline-flex items-center gap-2" data-testid="admin-addon-backfill">
          {backfilling ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />} Backfill dari Pembayaran
        </button>
      </div>

      {canManage && (
        <section className="rm-card p-5" data-testid="admin-addon-catalog">
          <div className="mb-3 flex items-center gap-2">
            <ShoppingBag className="h-5 w-5 text-[#FF7FC0]" />
            <h2 className="font-display text-lg font-bold tracking-tight">Katalog Layanan Tambahan</h2>
          </div>
          <p className="mb-4 text-xs text-zinc-500">Layanan yang bisa dibeli label saat submit rilisan. Pilih tipe pengiriman: <b>Tautan</b> (smart link/preset) atau <b>Berkas</b> (mis. video visualizer, admin mengunggah file).</p>
          <form onSubmit={submitProduct} className="grid gap-3 md:grid-cols-12 md:items-end">
            <div className="md:col-span-3"><label className="rm-label">Nama layanan</label><input required className="rm-input" value={pform.name} onChange={(e) => setPform({ ...pform, name: e.target.value })} data-testid="addon-product-name" /></div>
            <div className="md:col-span-3"><label className="rm-label">Deskripsi</label><input className="rm-input" value={pform.description} onChange={(e) => setPform({ ...pform, description: e.target.value })} data-testid="addon-product-description" /></div>
            <div className="md:col-span-2"><label className="rm-label">Harga IDR</label><input required min="1000" type="number" className="rm-input" value={pform.amount} onChange={(e) => setPform({ ...pform, amount: e.target.value })} data-testid="addon-product-amount" /></div>
            <div className="md:col-span-2"><label className="rm-label">Pengiriman</label><select className="rm-input" value={pform.delivery_type} onChange={(e) => setPform({ ...pform, delivery_type: e.target.value })} data-testid="addon-product-delivery-type"><option value="link">Tautan (link)</option><option value="file">Berkas (upload)</option></select></div>
            <button className="rm-btn-primary md:col-span-2 flex items-center justify-center gap-2" type="submit" data-testid="addon-product-submit">{editingProduct ? <Pencil className="h-4 w-4" /> : <Plus className="h-4 w-4" />} {editingProduct ? "Simpan" : "Tambah"}</button>
            {editingProduct && <button type="button" className="rm-btn-ghost md:col-span-12" onClick={() => { setEditingProduct(null); setPform({ name: "", description: "", amount: "", delivery_type: "link" }); }} data-testid="addon-product-edit-cancel">Batal Edit</button>}
          </form>
          {products.length > 0 && (
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              {products.map((p) => (
                <div key={p.id} className={`rounded-lg border p-4 ${p.active ? "border-white/10 bg-white/[0.02]" : "border-white/5 bg-white/[0.01] opacity-60"}`} data-testid={`addon-product-${p.id}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-bold">{p.name}</div>
                      <div className="text-xs text-zinc-500">Rp {Number(p.amount || 0).toLocaleString("id-ID")}</div>
                      <span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-[10px] font-bold ${p.delivery_type === "file" ? "bg-sky-500/15 text-sky-300" : "bg-zinc-500/15 text-zinc-300"}`}>{p.delivery_type === "file" ? "Berkas" : "Tautan"}</span>
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <button className="grid h-8 w-8 place-items-center rounded-md text-zinc-300 hover:bg-white/10" title="Edit" onClick={() => editProduct(p)} data-testid={`addon-product-edit-${p.id}`}><Pencil className="h-3.5 w-3.5" /></button>
                      <button className="grid h-8 w-8 place-items-center rounded-md text-red-300 hover:bg-red-500/15" title="Hapus" onClick={() => setDeleteTarget(p)} data-testid={`addon-product-delete-${p.id}`}><Trash2 className="h-3.5 w-3.5" /></button>
                    </div>
                  </div>
                  <button className="rm-btn-ghost mt-3 w-full py-1.5 text-xs" onClick={() => toggleProduct(p)} data-testid={`addon-product-toggle-${p.id}`}>{p.active ? "Nonaktifkan" : "Aktifkan"}</button>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      <div className="flex flex-wrap gap-2" data-testid="admin-addon-filters">
        {FILTERS.map(([key, label]) => (
          <button key={key} onClick={() => setFilter(key)} data-testid={`admin-addon-filter-${key}`}
            className={`rounded-full px-3.5 py-1.5 text-xs font-bold transition-colors ${filter === key ? "bg-gradient-to-r from-[#FF1F8E] to-[#A24EFF] text-white" : "bg-white/[0.05] text-zinc-400 hover:text-white"}`}>
            {label}{key !== "all" && counts[key] ? ` (${counts[key]})` : ""}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="rm-card p-10 text-center text-zinc-500" data-testid="admin-addon-loading"><Loader2 className="mx-auto h-6 w-6 animate-spin" /></div>
      ) : data.items.length === 0 ? (
        <div className="rm-card p-10 text-center text-sm text-zinc-500" data-testid="admin-addon-empty">
          Tidak ada order add-on untuk filter ini. Gunakan <b>Backfill</b> untuk memuat add-on dari pembayaran yang sudah lunas.
        </div>
      ) : (
        <div className="space-y-3">
          {data.items.map((o) => (
            <div key={o.id} className="rm-card p-4" data-testid={`admin-addon-order-${o.id}`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-bold">{o.product_name}</span>
                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold ${STATUS_STYLE[o.status] || STATUS_STYLE.pending}`} data-testid={`admin-addon-status-${o.id}`}>{o.status_label}</span>
                  </div>
                  <div className="mt-0.5 truncate text-xs text-zinc-500">
                    {o.label_name || "Label"} • {o.release_id ? <Link to={`/admin/releases/${o.release_id}`} className="rm-gradient-text font-semibold">{o.release_title || "Rilisan"}</Link> : "—"} • Rp {Number(o.amount || 0).toLocaleString("id-ID")}
                  </div>
                  {o.delivery_url && <a href={o.delivery_url} target="_blank" rel="noopener noreferrer" className="mt-1 inline-flex items-center gap-1 text-xs font-semibold rm-gradient-text">Hasil <ExternalLink className="h-3 w-3" /></a>}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <button onClick={() => openDelivery(o)} disabled={o.status === "cancelled"} className="rm-btn-ghost py-1.5 text-xs" data-testid={`admin-addon-delivery-${o.id}`}>Lampirkan Hasil</button>
                  {(NEXT_ACTIONS[o.status] || []).map(([status, label]) => (
                    <button key={status} onClick={() => changeStatus(o, status)} disabled={busy === o.id}
                      className={`py-1.5 text-xs ${status === "cancelled" ? "rm-btn-ghost text-red-300" : "rm-btn-primary"}`} data-testid={`admin-addon-action-${status}-${o.id}`}>
                      {busy === o.id ? "…" : label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {editing && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4" data-testid="admin-addon-delivery-modal" onClick={() => setEditing(null)}>
          <div className="w-full max-w-lg rounded-2xl border border-white/10 bg-zinc-950 p-6" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-display text-lg font-bold">Lampirkan Hasil — {editing.product_name}</h3>
            {editing.delivery_type === "file" ? (
              <>
                <p className="mt-1 text-xs text-zinc-500">Unggah berkas hasil (mis. video visualizer). File tersimpan aman & bisa diunduh label. Mengunggah otomatis menandai order <b>Terkirim</b>.</p>
                <label className="mt-4 flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-white/20 bg-white/[0.02] px-4 py-8 text-sm text-zinc-300 hover:border-[#FF1F8E]/50" data-testid="admin-addon-delivery-filepick">
                  <UploadCloud className="h-5 w-5" />
                  {deliveryFile ? deliveryFile.name : "Pilih file hasil (mp4, mov, zip, pdf, gambar, dll)"}
                  <input type="file" className="sr-only" accept=".mp4,.mov,.webm,.zip,.rar,.png,.jpg,.jpeg,.pdf,.mp3,.wav,.gif" onChange={(e) => setDeliveryFile(e.target.files?.[0] || null)} data-testid="admin-addon-delivery-file" />
                </label>
                {editing.delivery_filename && <p className="mt-2 text-[11px] text-zinc-500">File saat ini: {editing.delivery_filename}</p>}
              </>
            ) : (
              <>
                <p className="mt-1 text-xs text-zinc-500">Tautan hasil (smart link/preset) yang bisa diakses label. Menyimpan tautan otomatis menandai order sebagai <b>Terkirim</b>.</p>
                <label className="mt-4 block text-xs font-bold uppercase tracking-widest text-zinc-500">Tautan Hasil (URL)</label>
                <input value={deliveryUrl} onChange={(e) => setDeliveryUrl(e.target.value)} placeholder="https://…" className="rm-input mt-1" data-testid="admin-addon-delivery-url" />
                <label className="mt-3 block text-xs font-bold uppercase tracking-widest text-zinc-500">Catatan (opsional)</label>
                <textarea value={deliveryNote} onChange={(e) => setDeliveryNote(e.target.value)} className="rm-input mt-1 min-h-[80px]" data-testid="admin-addon-delivery-note" />
              </>
            )}
            <div className="mt-5 flex justify-end gap-2">
              <button onClick={() => setEditing(null)} className="rm-btn-ghost">Batal</button>
              <button onClick={saveDelivery} disabled={busy === editing.id} className="rm-btn-primary" data-testid="admin-addon-delivery-save">{busy === editing.id ? "Menyimpan…" : (editing.delivery_type === "file" ? "Unggah Hasil" : "Simpan Hasil")}</button>
            </div>
          </div>
        </div>
      )}

      {deleteTarget && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4" onClick={() => setDeleteTarget(null)} data-testid="admin-addon-product-delete-modal">
          <div className="w-full max-w-md rounded-2xl border border-red-500/30 bg-zinc-950 p-6" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-display text-lg font-extrabold text-red-200">Hapus Layanan</h3>
            <p className="mt-2 text-sm text-zinc-300">Hapus <b>{deleteTarget.name}</b> dari katalog? Layanan yang sudah dipakai invoice lama akan diarsipkan agar histori tetap utuh.</p>
            <div className="mt-5 flex justify-end gap-2">
              <button className="rm-btn-ghost" onClick={() => setDeleteTarget(null)}>Batal</button>
              <button className="rm-btn-primary" onClick={removeProduct} data-testid="admin-addon-product-delete-confirm">Hapus</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
