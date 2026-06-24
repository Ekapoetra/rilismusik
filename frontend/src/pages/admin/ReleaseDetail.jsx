import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, formatApiError, fileUrl } from "@/api/client";
import StatusBadge from "@/components/shared/StatusBadge";
import { ADMIN_RELEASE } from "@/constants/testIds";
import { Disc3, Music, AlertCircle } from "lucide-react";

export default function AdminReleaseDetail() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [isrc, setIsrc] = useState("");
  const [upc, setUpc] = useState("");
  const [note, setNote] = useState("");
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    const { data } = await api.get(`/releases/${id}`);
    setData(data);
    setUpc(data.upc || "");
    setIsrc(data.tracks?.[0]?.isrc || "");
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const act = async (action) => {
    setErr(""); setMsg(""); setBusy(true);
    try {
      const { data } = await api.post(`/releases/${id}/admin/action`, { action, isrc: isrc || undefined, upc: upc || undefined, note: note || undefined });
      setData((d) => ({ ...d, ...data }));
      setMsg(`Aksi "${action}" berhasil.`);
      await load();
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  if (!data) return <div className="text-slate-500">Memuat…</div>;

  const blockedByPayment = data.payment_status === "pending";

  return (
    <div className="space-y-5 max-w-5xl">
      <Link to="/admin/releases" className="text-sm text-slate-600 hover:text-[#FF3B30]">← Release Management</Link>

      <div className="flex items-start gap-4 flex-wrap">
        {data.cover_url ? (
          <img src={fileUrl(data.cover_url)} alt="cover" className="w-32 h-32 rounded-2xl object-cover" />
        ) : <div className="w-32 h-32 rounded-2xl bg-slate-100 grid place-items-center text-slate-400"><Disc3 className="w-10 h-10" /></div>}
        <div className="flex-1 min-w-[260px]">
          <div className="text-xs uppercase tracking-widest text-slate-500 font-bold">{data.release_type}</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter">{data.release_title}</h1>
          <div className="text-slate-600">{data.artist_name} • Rilis {data.release_date}</div>
          <div className="mt-2 flex gap-2"><StatusBadge status={data.status} />
            {data.payment_status === "pending" && <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-700">Invoice Pending</span>}
            {data.payment_status === "free_subscription" && <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700">Subscription</span>}
          </div>
        </div>
      </div>

      {err && <div className="rounded-2xl bg-red-50 text-red-700 px-4 py-3 text-sm">{err}</div>}
      {msg && <div className="rounded-2xl bg-emerald-50 text-emerald-700 px-4 py-3 text-sm">{msg}</div>}
      {blockedByPayment && (
        <div className="rounded-2xl bg-amber-50 text-amber-800 px-4 py-3 text-sm flex items-center gap-2"><AlertCircle className="w-4 h-4" /> Invoice belum dibayar — aksi review terkunci.</div>
      )}

      {/* Tracks with audio */}
      <div className="rm-card p-5">
        <h3 className="font-display font-bold text-lg tracking-tight mb-3">Tracklist</h3>
        <div className="divide-y divide-slate-100">
          {data.tracks?.map((t) => (
            <div key={t.id} className="py-3 flex items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-xl bg-slate-100 text-slate-600 grid place-items-center text-sm font-bold">{t.track_number}</div>
                <div className="min-w-0">
                  <div className="font-semibold text-sm truncate">{t.track_title}</div>
                  <div className="text-xs text-slate-500 truncate">{t.artist_name} • Composer: {t.composer || "—"} {t.isrc && <> • ISRC {t.isrc}</>}</div>
                </div>
              </div>
              {t.audio_url ? <audio controls src={fileUrl(t.audio_url)} className="h-9 max-w-[260px]" /> : <span className="text-xs text-slate-400 flex items-center gap-1"><Music className="w-3.5 h-3.5" /> Belum ada audio</span>}
            </div>
          ))}
        </div>
      </div>

      {/* Admin action panel */}
      <div className="rm-card p-5 space-y-4">
        <h3 className="font-display font-bold text-lg tracking-tight">Aksi Review</h3>
        <div className="grid md:grid-cols-3 gap-3">
          <div>
            <label className="rm-label">ISRC (opsional, applies all tracks)</label>
            <input className="rm-input" value={isrc} onChange={(e) => setIsrc(e.target.value)} data-testid={ADMIN_RELEASE.isrcInput} />
          </div>
          <div>
            <label className="rm-label">UPC</label>
            <input className="rm-input" value={upc} onChange={(e) => setUpc(e.target.value)} data-testid={ADMIN_RELEASE.upcInput} />
          </div>
          <div>
            <label className="rm-label">Note (untuk Need Revision/Reject)</label>
            <input className="rm-input" value={note} onChange={(e) => setNote(e.target.value)} data-testid={ADMIN_RELEASE.noteInput} placeholder="Misal: cover blur" />
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="rm-btn-primary text-sm" disabled={busy || blockedByPayment} onClick={() => act("approve")} data-testid={ADMIN_RELEASE.approveButton}>Approve</button>
          <button className="rm-btn-ghost text-sm" disabled={busy} onClick={() => act("need_revision")} data-testid={ADMIN_RELEASE.needRevisionButton}>Need Revision</button>
          <button className="rm-btn-ghost text-sm" disabled={busy} onClick={() => act("reject")} data-testid={ADMIN_RELEASE.rejectButton}>Reject</button>
          <button className="rm-btn-ghost text-sm" disabled={busy || blockedByPayment} onClick={() => act("deliver")} data-testid={ADMIN_RELEASE.deliverButton}>Deliver to Believe</button>
          <button className="rm-btn-ghost text-sm" disabled={busy || blockedByPayment} onClick={() => act("mark_live")} data-testid={ADMIN_RELEASE.liveButton}>Mark Live</button>
          <button className="rm-btn-ghost text-sm" disabled={busy} onClick={() => act("takedown")}>Takedown</button>
        </div>
      </div>
    </div>
  );
}
