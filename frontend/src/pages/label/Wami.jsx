import React, { useCallback, useEffect, useState } from "react";
import { api, formatApiError } from "@/api/client";
import { openXenditCheckout, pollPaymentUntilTerminal } from "@/api/payments";
import { useSearchParams } from "react-router-dom";
import { Music, CheckCircle2, Clock, AlertTriangle, Star, Plus, X } from "lucide-react";

const STATUS_LABELS = {
  unpaid: "Belum Bayar",
  pending: "Menunggu Admin",
  in_progress: "Sedang Diproses",
  registered: "Terdaftar ✓",
  rejected: "Ditolak",
  cancelled: "Dibatalkan",
};

const STATUS_STYLES = {
  unpaid: { bg: "rgba(239,68,68,0.15)", color: "#FCA5A5", dot: "#EF4444", Icon: AlertTriangle },
  pending: { bg: "rgba(245,158,11,0.18)", color: "#FCD34D", dot: "#F59E0B", Icon: Clock },
  in_progress: { bg: "rgba(255,31,142,0.18)", color: "#FF8AC0", dot: "#FF1F8E", Icon: Clock },
  registered: { bg: "rgba(16,185,129,0.18)", color: "#6EE7B7", dot: "#10B981", Icon: CheckCircle2 },
  rejected: { bg: "rgba(239,68,68,0.18)", color: "#FCA5A5", dot: "#EF4444", Icon: AlertTriangle },
  cancelled: { bg: "rgba(255,255,255,0.06)", color: "#A1A1B5", dot: "#71717A", Icon: AlertTriangle },
};

function fmtIDR(n) {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
}

export default function LabelWami() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [orders, setOrders] = useState([]);
  const [tracks, setTracks] = useState([]);
  const [me, setMe] = useState(null);
  const [open, setOpen] = useState(false);
  const [selectedTrackId, setSelectedTrackId] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    const { data } = await api.get("/wami/label");
    setOrders(data);
  }, []);

  const loadTracks = useCallback(async () => {
    // Fetch live releases & flatten tracks
    const { data: releases } = await api.get("/releases/");
    const liveReleases = releases.filter((r) => r.status === "live");
    const out = [];
    const failedReleases = [];
    for (const r of liveReleases) {
      try {
        const { data: detail } = await api.get(`/releases/${r.id}`);
        for (const t of detail.tracks || []) {
          out.push({ ...t, release_title: r.release_title, release_id: r.id });
        }
      } catch (error) {
        failedReleases.push(r.release_title || r.id);
      }
    }
    setTracks(out);
    if (failedReleases.length) {
      setErr(`Sebagian detail rilisan gagal dimuat: ${failedReleases.join(", ")}`);
    }
  }, []);

  const loadMe = useCallback(async () => {
    const { data } = await api.get("/auth/me");
    setMe(data);
  }, []);

  useEffect(() => {
    load();
    loadTracks();
    loadMe();
  }, [load, loadTracks, loadMe]);

  useEffect(() => {
    const paymentId = searchParams.get("payment_id");
    if (!paymentId) return;
    let active = true;
    setBusy(true); setMsg("Mengonfirmasi pembayaran WAMI ke Xendit…");
    pollPaymentUntilTerminal(paymentId, null, 75)
      .then(async (result) => {
        if (!active) return;
        setMsg(result.status === "paid" ? "Pembayaran WAMI berhasil dikonfirmasi." : `Status pembayaran: ${result.status}`);
        setSearchParams({}); await load();
      })
      .catch((e) => active && setErr(formatApiError(e.response?.data?.detail || e.message)))
      .finally(() => active && setBusy(false));
    return () => { active = false; };
  }, [searchParams, setSearchParams, load]);

  const submit = async () => {
    if (!selectedTrackId) return;
    setBusy(true); setErr(""); setMsg("");
    try {
      const { data } = await api.post("/payments/wami", { track_id: selectedTrackId });
      if (data.free_vip) {
        setMsg("Pendaftaran WAMI dibuat (GRATIS untuk VIP). Admin akan memproses.");
        setOpen(false);
        setSelectedTrackId("");
        load();
      } else {
        setMsg(`Membuka checkout WAMI ${fmtIDR(data.invoice.amount)}…`);
        await openXenditCheckout(data.invoice.id);
      }
    } catch (e2) { setErr(formatApiError(e2.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const isVip = me?.label?.payment_type === "annual_subscription" && me?.label?.subscription_tier === "annual_vip";
  // Tracks without active WAMI order
  const activeTrackIds = new Set(orders.filter((o) => !["cancelled", "rejected"].includes(o.status)).map((o) => o.track_id));
  const availableTracks = tracks.filter((t) => !activeTrackIds.has(t.id));

  return (
    <div className="space-y-5 max-w-5xl">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Pendaftaran</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter">WAMI / LMKN</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Daftarkan lagu Anda ke LMKN — Wahana Musik Indonesia.
            {isVip ? (
              <span className="text-pink-300 font-semibold"> Anda VIP — pendaftaran GRATIS untuk semua lagu.</span>
            ) : (
              <> Biaya pendaftaran <b>{fmtIDR(100000)}</b> per lagu via Xendit.</>
            )}
          </p>
        </div>
        <button
          className="rm-btn-primary flex items-center gap-2"
          onClick={() => setOpen(true)}
          disabled={tracks.length === 0}
          data-testid="label-wami-new-button"
        >
          <Plus className="w-4 h-4" /> Daftarkan Lagu
        </button>
      </div>

      {isVip && (
        <div className="rm-card p-4 border border-pink-500/20 flex items-start gap-3">
          <Star className="w-5 h-5 text-pink-300 mt-0.5" />
          <div className="text-sm">
            <div className="font-bold text-pink-200">Anda Member VIP</div>
            <div className="text-zinc-400 text-xs">Semua pendaftaran WAMI gratis tanpa biaya tambahan. Anda juga akan menerima konten promosi setelah rilis disetujui.</div>
          </div>
        </div>
      )}

      {msg && <div className="rounded-2xl bg-emerald-500/15 text-emerald-300 px-4 py-3 text-sm" data-testid="wami-payment-message">{msg}</div>}
      {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm" data-testid="wami-payment-error">{err}</div>}

      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5">
          <div className="col-span-4">Lagu</div>
          <div className="col-span-3">ISRC</div>
          <div className="col-span-2">Biaya</div>
          <div className="col-span-3">Status</div>
        </div>
        {orders.length === 0 ? (
          <div className="p-10 text-center text-zinc-500 text-sm">
            <Music className="w-8 h-8 mx-auto mb-3 text-zinc-700" />
            Belum ada pendaftaran WAMI. Klik &quot;Daftarkan Lagu&quot; untuk mulai.
          </div>
        ) : orders.map((o) => {
          const s = STATUS_STYLES[o.status] || STATUS_STYLES.pending;
          const Icon = s.Icon;
          return (
            <div key={o.id} className="px-5 py-4 grid grid-cols-12 gap-3 items-center border-b border-white/5 last:border-0" data-testid={`label-wami-row-${o.id}`}>
              <div className="col-span-12 md:col-span-4">
                <div className="font-semibold text-sm">{o.track_title}</div>
                <div className="text-xs text-zinc-500">{o.release_title}</div>
              </div>
              <div className="col-span-6 md:col-span-3 text-sm text-zinc-300 font-mono text-xs">{o.isrc || "—"}</div>
              <div className="col-span-6 md:col-span-2 text-sm">
                {o.is_free_vip ? (
                  <span className="rm-gradient-text font-bold">VIP — Gratis</span>
                ) : (
                  <span>{fmtIDR(o.amount_idr)}</span>
                )}
              </div>
              <div className="col-span-12 md:col-span-3">
                <span className="rm-badge" style={{ background: s.bg, color: s.color }}>
                  <Icon className="w-3 h-3" />
                  {STATUS_LABELS[o.status] || o.status}
                </span>
                {o.wami_reference && <div className="text-xs text-zinc-500 mt-1">Ref: {o.wami_reference}</div>}
              </div>
            </div>
          );
        })}
      </div>

      {open && (
        <div className="fixed inset-0 z-50 bg-black/60 grid place-items-center p-4" onClick={() => setOpen(false)}>
          <div onClick={(e) => e.stopPropagation()} className="w-full max-w-md rm-glass-strong rounded-[24px] p-6 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-display font-extrabold text-xl tracking-tighter">Daftarkan Lagu ke WAMI</h3>
              <button onClick={() => setOpen(false)} className="p-2 text-zinc-400 hover:text-white"><X className="w-5 h-5" /></button>
            </div>
            <div className="text-sm text-zinc-400">
              Pilih lagu dari rilisan yang sudah LIVE.
              {!isVip && <> Biaya <b>{fmtIDR(100000)}/lagu</b> dibayar via Xendit.</>}
            </div>
            <div>
              <label className="rm-label">Pilih Lagu</label>
              <select
                className="rm-input"
                value={selectedTrackId}
                onChange={(e) => setSelectedTrackId(e.target.value)}
                data-testid="label-wami-track-select"
              >
                <option value="">— Pilih lagu —</option>
                {availableTracks.map((t) => (
                  <option key={t.id} value={t.id}>{t.track_title} — {t.release_title}</option>
                ))}
              </select>
              {availableTracks.length === 0 && (
                <div className="text-xs text-amber-300 mt-2">
                  Tidak ada lagu tersedia. Pastikan ada rilisan yang sudah berstatus LIVE dan belum pernah didaftarkan WAMI.
                </div>
              )}
            </div>
            <div className="flex justify-end gap-2">
              <button className="rm-btn-ghost" onClick={() => setOpen(false)}>Batal</button>
              <button
                className="rm-btn-primary"
                disabled={busy || !selectedTrackId}
                onClick={submit}
                data-testid="label-wami-submit"
              >
                {busy ? "Memproses…" : isVip ? "Daftarkan (GRATIS VIP)" : `Bayar ${fmtIDR(100000)}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
