import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { Sparkles, ExternalLink, RefreshCw, Loader2 } from "lucide-react";

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
  const [data, setData] = useState({ items: [], counts: {}, labels: {} });
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [busy, setBusy] = useState("");
  const [backfilling, setBackfilling] = useState(false);
  const [editing, setEditing] = useState(null);
  const [deliveryUrl, setDeliveryUrl] = useState("");
  const [deliveryNote, setDeliveryNote] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get("/admin/addon-orders", { params: filter === "all" ? {} : { status: filter } });
      setData(r.data);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail) || "Gagal memuat"); }
    finally { setLoading(false); }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

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
    setDeliveryUrl(order.delivery_url || "");
    setDeliveryNote(order.delivery_note || "");
  };
  const saveDelivery = async () => {
    setBusy(editing.id);
    try {
      await api.patch(`/admin/addon-orders/${editing.id}/delivery`, { delivery_url: deliveryUrl, delivery_note: deliveryNote });
      toast.success("Hasil tersimpan & label diberi tahu");
      setEditing(null);
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail) || "Gagal"); }
    finally { setBusy(""); }
  };

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
            <p className="mt-1 text-xs text-zinc-500">Tautan hasil (file/preset) yang bisa diakses label. Menyimpan tautan otomatis menandai order sebagai <b>Terkirim</b>.</p>
            <label className="mt-4 block text-xs font-bold uppercase tracking-widest text-zinc-500">Tautan Hasil (URL)</label>
            <input value={deliveryUrl} onChange={(e) => setDeliveryUrl(e.target.value)} placeholder="https://…" className="rm-input mt-1" data-testid="admin-addon-delivery-url" />
            <label className="mt-3 block text-xs font-bold uppercase tracking-widest text-zinc-500">Catatan (opsional)</label>
            <textarea value={deliveryNote} onChange={(e) => setDeliveryNote(e.target.value)} className="rm-input mt-1 min-h-[80px]" data-testid="admin-addon-delivery-note" />
            <div className="mt-5 flex justify-end gap-2">
              <button onClick={() => setEditing(null)} className="rm-btn-ghost">Batal</button>
              <button onClick={saveDelivery} disabled={busy === editing.id} className="rm-btn-primary" data-testid="admin-addon-delivery-save">{busy === editing.id ? "Menyimpan…" : "Simpan Hasil"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
