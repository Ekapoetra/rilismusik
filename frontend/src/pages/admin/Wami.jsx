import React, { useEffect, useState } from "react";
import { api, formatApiError } from "@/api/client";
import { Music, CheckCircle2, Clock, AlertTriangle, X, Star } from "lucide-react";

const STATUS_LABELS = {
  unpaid: "Belum Bayar",
  pending: "Menunggu Diproses",
  in_progress: "Sedang Diproses",
  registered: "Terdaftar",
  rejected: "Ditolak",
  cancelled: "Dibatalkan",
};

const STATUS_STYLES = {
  unpaid: { bg: "rgba(239,68,68,0.15)", color: "#FCA5A5", dot: "#EF4444" },
  pending: { bg: "rgba(245,158,11,0.18)", color: "#FCD34D", dot: "#F59E0B" },
  in_progress: { bg: "rgba(255,31,142,0.18)", color: "#FF8AC0", dot: "#FF1F8E" },
  registered: { bg: "rgba(16,185,129,0.18)", color: "#6EE7B7", dot: "#10B981" },
  rejected: { bg: "rgba(239,68,68,0.18)", color: "#FCA5A5", dot: "#EF4444" },
  cancelled: { bg: "rgba(255,255,255,0.06)", color: "#A1A1B5", dot: "#71717A" },
};

const NEXT_STATUS_OPTIONS = ["in_progress", "registered", "rejected", "cancelled"];

function fmtIDR(n) { return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0); }

export default function AdminWami() {
  const [items, setItems] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [modal, setModal] = useState(null);  // order being updated
  const [form, setForm] = useState({ status: "in_progress", note: "", wami_reference: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    const params = statusFilter ? { status: statusFilter } : {};
    const { data } = await api.get("/wami/admin", { params });
    setItems(data);
  };

  useEffect(() => { load(); }, [statusFilter]);

  const openUpdate = (o) => {
    setModal(o);
    setForm({ status: o.status === "unpaid" ? "cancelled" : (o.status === "pending" ? "in_progress" : "registered"), note: o.admin_note || "", wami_reference: o.wami_reference || "" });
    setErr("");
  };

  const submit = async () => {
    setBusy(true); setErr(""); setMsg("");
    try {
      await api.post(`/wami/admin/${modal.id}/status`, form);
      setMsg(`Status WAMI ${modal.track_title} diubah ke ${STATUS_LABELS[form.status]}.`);
      setModal(null);
      load();
    } catch (e2) { setErr(formatApiError(e2.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-5 max-w-7xl">
      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Royalty Operations</div>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">WAMI Registrations</h1>
        <p className="text-sm text-zinc-400 mt-1">Proses pendaftaran LMKN—WAMI untuk lagu label.</p>
      </div>

      {msg && <div className="rounded-2xl bg-emerald-500/15 text-emerald-300 px-4 py-3 text-sm">{msg}</div>}

      <div className="flex gap-2 flex-wrap">
        {["", "unpaid", "pending", "in_progress", "registered", "rejected", "cancelled"].map((s) => (
          <button
            key={s || "all"}
            onClick={() => setStatusFilter(s)}
            className={`px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest ${statusFilter === s ? "text-white" : "rm-glass text-zinc-400"}`}
            style={statusFilter === s ? { background: "linear-gradient(135deg, #FF1F8E, #A24EFF)" } : {}}
            data-testid={`admin-wami-filter-${s || "all"}`}
          >
            {s ? STATUS_LABELS[s] : "Semua"}
          </button>
        ))}
      </div>

      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5">
          <div className="col-span-3">Lagu</div>
          <div className="col-span-2">Label</div>
          <div className="col-span-2">ISRC</div>
          <div className="col-span-2">Biaya</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-1 text-right">Aksi</div>
        </div>
        {items.length === 0 ? (
          <div className="p-10 text-center text-zinc-500 text-sm">
            <Music className="w-8 h-8 mx-auto mb-3 text-zinc-700" />
            Tidak ada pendaftaran WAMI.
          </div>
        ) : items.map((o) => {
          const s = STATUS_STYLES[o.status] || STATUS_STYLES.pending;
          return (
            <div key={o.id} className="px-5 py-4 grid grid-cols-12 gap-3 items-center border-b border-white/5 last:border-0" data-testid={`admin-wami-row-${o.id}`}>
              <div className="col-span-12 md:col-span-3">
                <div className="font-semibold text-sm">{o.track_title}</div>
                <div className="text-xs text-zinc-500">{o.release_title}</div>
              </div>
              <div className="col-span-6 md:col-span-2 text-sm truncate">{o.label_name}</div>
              <div className="col-span-6 md:col-span-2 text-xs font-mono text-zinc-400">{o.isrc || "—"}</div>
              <div className="col-span-6 md:col-span-2 text-sm">
                {o.is_free_vip ? (
                  <span className="rm-gradient-text font-bold flex items-center gap-1"><Star className="w-3 h-3" /> VIP</span>
                ) : <span>{fmtIDR(o.amount_idr)}</span>}
              </div>
              <div className="col-span-12 md:col-span-2">
                <span className="rm-badge" style={{ background: s.bg, color: s.color }}>
                  <span className="rm-badge-dot" style={{ background: s.dot }} />
                  {STATUS_LABELS[o.status] || o.status}
                </span>
                {o.wami_reference && <div className="text-xs text-zinc-500 mt-1">Ref: {o.wami_reference}</div>}
              </div>
              <div className="col-span-12 md:col-span-1 flex justify-end">
                {o.status !== "registered" && o.status !== "cancelled" && (
                  <button
                    className="rm-btn-primary text-xs px-3 py-1.5"
                    onClick={() => openUpdate(o)}
                    data-testid={`admin-wami-update-${o.id}`}
                  >
                    Proses
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {modal && (
        <div className="fixed inset-0 z-50 bg-black/60 grid place-items-center p-4" onClick={() => setModal(null)}>
          <div onClick={(e) => e.stopPropagation()} className="w-full max-w-md rm-glass-strong rounded-[24px] p-6 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-display font-extrabold text-xl tracking-tighter">Update WAMI</h3>
              <button onClick={() => setModal(null)} className="p-2 text-zinc-400 hover:text-white"><X className="w-5 h-5" /></button>
            </div>
            <div className="text-sm">
              <div className="font-semibold">{modal.track_title}</div>
              <div className="text-xs text-zinc-500">{modal.label_name} • {modal.release_title}</div>
            </div>

            {err && <div className="rounded-xl bg-red-500/15 text-red-300 px-3 py-2 text-sm flex items-center gap-2"><AlertTriangle className="w-4 h-4" /> {err}</div>}

            <div>
              <label className="rm-label">Status Baru</label>
              <select className="rm-input" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} data-testid="admin-wami-status-select">
                {NEXT_STATUS_OPTIONS.map((s) => <option key={s} value={s}>{STATUS_LABELS[s]}</option>)}
              </select>
            </div>

            <div>
              <label className="rm-label">No. Referensi WAMI / LMKN (opsional)</label>
              <input
                className="rm-input"
                value={form.wami_reference}
                onChange={(e) => setForm({ ...form, wami_reference: e.target.value })}
                placeholder="Contoh: WAMI-2025-001234"
                data-testid="admin-wami-reference"
              />
            </div>

            <div>
              <label className="rm-label">Catatan (opsional, akan dilihat label)</label>
              <textarea
                className="rm-input min-h-[70px]"
                value={form.note}
                onChange={(e) => setForm({ ...form, note: e.target.value })}
                data-testid="admin-wami-note"
              />
            </div>

            <div className="flex justify-end gap-2">
              <button className="rm-btn-ghost" onClick={() => setModal(null)}>Batal</button>
              <button
                className="rm-btn-primary"
                disabled={busy}
                onClick={submit}
                data-testid="admin-wami-submit"
              >
                {busy ? "Menyimpan…" : "Simpan"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
