import React, { useCallback, useEffect, useState } from "react";
import { useParams, Link, useSearchParams } from "react-router-dom";
import { api, formatApiError, fileUrl } from "@/api/client";
import { openXenditCheckout, pollPaymentUntilTerminal } from "@/api/payments";
import StatusBadge from "@/components/shared/StatusBadge";
import { CreditCard, Disc3, Music } from "lucide-react";

export default function ReleaseDetail() {
  const { id } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState(null);
  const [invoice, setInvoice] = useState(null);
  const [paying, setPaying] = useState(false);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/releases/${id}`);
      setData(data);
      if (data.payment_id && data.payment_status === "pending") {
        const inv = await api.get(`/label/invoices`);
        setInvoice(inv.data.find((i) => i.id === data.payment_id) || null);
      } else { setInvoice(null); }
    } catch (e) { setErr(formatApiError(e.response?.data?.detail) || "Gagal memuat"); }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const paymentId = searchParams.get("payment_id");
    if (!paymentId) return;
    let active = true;
    setPaying(true);
    pollPaymentUntilTerminal(paymentId, null, 75)
      .then(async () => { if (active) { setSearchParams({}); await load(); } })
      .catch((e) => active && setErr(formatApiError(e.response?.data?.detail || e.message)))
      .finally(() => active && setPaying(false));
    return () => { active = false; };
  }, [searchParams, setSearchParams, load]);

  const pay = async () => {
    if (!invoice) return;
    setPaying(true);
    try {
      await openXenditCheckout(invoice.id);
    } catch (e) { setErr(formatApiError(e.response?.data?.detail || e.message)); }
    finally { setPaying(false); }
  };

  if (!data) return <div className="text-zinc-500">Memuat…</div>;

  return (
    <div className="space-y-5 max-w-5xl">
      <Link to="/label/releases" className="text-sm text-zinc-400 hover:rm-gradient-text">← Daftar Rilisan</Link>

      <div className="flex items-start justify-between gap-5 flex-wrap">
        <div className="flex gap-4 items-start">
          {data.cover_url ? (
            <img src={fileUrl(data.cover_url)} alt="cover" className="w-28 h-28 rounded-2xl object-cover" />
          ) : (
            <div className="w-28 h-28 rounded-2xl bg-gradient-to-br from-[#FF4FA8] to-[#A24EFF] grid place-items-center text-white"><Disc3 className="w-8 h-8" /></div>
          )}
          <div>
            <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">{data.release_type}</div>
            <h1 className="font-display text-3xl font-extrabold tracking-tighter">{data.release_title}</h1>
            <div className="text-zinc-400 mt-1">{data.artist_name} • Rilis {data.release_date}</div>
            <div className="mt-2"><StatusBadge status={data.status} /></div>
          </div>
        </div>
        {(data.status === "draft" || data.status === "need_revision") && (
          <Link to={`/label/releases/${data.id}/edit`} className="rm-btn-ghost" data-testid="release-detail-edit-button">Edit</Link>
        )}
      </div>

      {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm border border-red-100">{err}</div>}

      {/* Awaiting payment block */}
      {data.payment_status === "pending" && invoice && (
        <div className="rm-glass-strong rounded-3xl p-6 border border-amber-200/60">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/100/20 text-amber-300 grid place-items-center"><CreditCard className="w-5 h-5" /></div>
            <div>
              <div className="font-display font-bold text-lg">Menunggu Pembayaran</div>
              <div className="text-sm text-zinc-400">Pay-per-release Rp {(invoice.amount).toLocaleString("id-ID")} via checkout Xendit.</div>
            </div>
          </div>
          <div className="text-xs text-zinc-500 mb-3">Invoice: {invoice.xendit_invoice_id}</div>
          <button className="rm-btn-primary" onClick={pay} disabled={paying} data-testid="release-detail-xendit-pay">
            {paying ? "Mengonfirmasi…" : "Bayar via Xendit"}
          </button>
          <div className="text-[11px] text-zinc-600 mt-2">Status pembayaran dikonfirmasi langsung ke Xendit setelah Anda kembali.</div>
        </div>
      )}

      {data.admin_note && (
        <div className="rounded-2xl bg-yellow-500/15 text-yellow-200 px-4 py-3 text-sm border border-yellow-100">
          <b>Catatan Admin:</b> {data.admin_note}
        </div>
      )}

      {/* Tracks */}
      <div className="rm-card p-5">
        <h3 className="font-display font-bold text-lg tracking-tight mb-3">Tracklist</h3>
        <div className="divide-y divide-white/5">
          {data.tracks?.map((t) => (
            <div key={t.id} className="py-3 flex items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-xl bg-white/[0.06] text-zinc-400 grid place-items-center text-sm font-bold">{t.track_number}</div>
                <div className="min-w-0">
                  <div className="font-semibold text-sm truncate">{t.track_title}</div>
                  <div className="text-xs text-zinc-500 truncate">{t.artist_name} {t.isrc && <span> • ISRC: {t.isrc}</span>}</div>
                </div>
              </div>
              {t.audio_url ? (
                <audio controls src={fileUrl(t.audio_url)} className="h-9 max-w-[260px]" />
              ) : (
                <span className="text-xs text-zinc-600 flex items-center gap-1"><Music className="w-3.5 h-3.5" /> Belum ada audio</span>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <InfoCard title="Metadata">
          <Row k="Genre" v={data.genre} />
          <Row k="Subgenre" v={data.subgenre} />
          <Row k="Bahasa" v={data.language} />
          <Row k="Explicit" v={data.explicit ? "Ya" : "Tidak"} />
          <Row k="© Copyright" v={data.copyright_line} />
          <Row k="℗ Phonographic" v={data.p_line} />
          <Row k="UPC" v={data.upc} />
        </InfoCard>
        <InfoCard title="Distribusi">
          <Row k="Platforms" v={(data.platforms || []).join(", ")} />
          <Row k="Submitted at" v={data.updated_at?.slice(0, 19).replace("T", " ")} />
          <Row k="Status pembayaran" v={data.payment_status} />
        </InfoCard>
      </div>
    </div>
  );
}

function InfoCard({ title, children }) {
  return (
    <div className="rm-card p-5">
      <h3 className="font-display font-bold text-lg tracking-tight mb-2">{title}</h3>
      <div className="divide-y divide-white/5">{children}</div>
    </div>
  );
}
function Row({ k, v }) { return <div className="py-2 flex justify-between gap-3 text-sm"><span className="text-zinc-500">{k}</span><span className="font-semibold text-right truncate max-w-[60%]">{v || "—"}</span></div>; }
