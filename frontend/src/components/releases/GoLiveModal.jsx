import React, { useCallback, useEffect, useState } from "react";
import { Rocket, Clock, Loader2, Disc3, CalendarClock, ArrowLeft } from "lucide-react";
import { api, fileUrl, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { celebrateWork } from "@/lib/completionFeedback";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";

const coverSrc = (r) => (r?.imported_legacy && r?.internal_cover_url) || r?.cover_url || "";

export default function GoLiveModal({ releaseId, open, onClose, onDone }) {
  const [release, setRelease] = useState(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [upc, setUpc] = useState("");
  const [isrcs, setIsrcs] = useState({});
  const [releaseDate, setReleaseDate] = useState("");
  const [postpone, setPostpone] = useState(false);
  const [newDate, setNewDate] = useState("");

  const load = useCallback(async () => {
    if (!releaseId) return;
    setLoading(true); setError("");
    try {
      const { data } = await api.get(`/releases/${releaseId}`);
      setRelease(data);
      setUpc(data.upc || "");
      setReleaseDate((data.release_date || "").slice(0, 10));
      setNewDate((data.release_date || "").slice(0, 10));
      setIsrcs(Object.fromEntries((data.tracks || []).map((t) => [t.id, t.isrc || ""])));
    } catch (e) {
      setError(formatApiError(e.response?.data?.detail) || "Gagal memuat rilisan.");
    } finally { setLoading(false); }
  }, [releaseId]);

  useEffect(() => { if (open) { setPostpone(false); load(); } }, [open, load]);

  const goLive = async () => {
    if (busy) return; setBusy(true); setError("");
    try {
      await api.post(`/releases/${releaseId}/admin/action`, {
        action: "mark_live", upc: upc.trim(), track_isrcs: isrcs,
        release_date: releaseDate || undefined,
      });
      toast.success("Rilisan kini tayang. Email pemberitahuan dikirim ke label.");
      celebrateWork("release_go_live");
      onDone?.(); onClose?.();
    } catch (e) {
      const msg = formatApiError(e.response?.data?.detail) || "Gagal menandai tayang.";
      setError(msg); toast.error(msg);
    } finally { setBusy(false); }
  };

  const reschedule = async () => {
    if (busy) return; setBusy(true); setError("");
    try {
      await api.post(`/releases/${releaseId}/admin/action`, { action: "reschedule", release_date: newDate });
      toast.success("Tanggal rilis diperbarui. Rilisan tetap menunggu tayang.");
      onDone?.(); onClose?.();
    } catch (e) {
      const msg = formatApiError(e.response?.data?.detail) || "Gagal memperbarui tanggal.";
      setError(msg); toast.error(msg);
    } finally { setBusy(false); }
  };

  const src = coverSrc(release);
  const tracks = release?.tracks || [];
  const artistLabel = release?.artist_name || release?.primary_artist_name
    || Array.from(new Set((tracks.map((t) => t.artist_name).filter(Boolean)))).join(", ") || "—";

  return (
    <Dialog open={open} onOpenChange={(o) => !o && !busy && onClose?.()}>
      <DialogContent className="ui-menu max-h-[90dvh] w-[calc(100%-2rem)] max-w-lg overflow-y-auto rounded-lg" data-testid="go-live-modal" closeTestId="go-live-close">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Rocket className="h-5 w-5 text-pink-400" /> Finalisasi Tayang</DialogTitle>
          <DialogDescription>Lengkapi UPC & ISRC lalu tayangkan. Label akan menerima email otomatis saat rilisan tayang.</DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-14 text-sm text-zinc-500" data-testid="go-live-loading"><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Memuat rilisan…</div>
        ) : !release ? (
          <div className="py-10 text-center text-sm text-red-300" data-testid="go-live-load-error">{error || "Rilisan tidak ditemukan."}</div>
        ) : (
          <div className="space-y-5">
            {/* Header: cover + title + artist */}
            <div className="flex items-center gap-4 rounded-lg border border-white/10 bg-white/[0.02] p-3">
              <div className="grid aspect-square w-16 shrink-0 place-items-center overflow-hidden rounded-md border border-white/10 bg-white/5">
                {src ? <img src={fileUrl(src)} alt={release.release_title} className="h-full w-full object-cover" data-testid="go-live-cover" /> : <Disc3 className="h-6 w-6 text-zinc-500" data-testid="go-live-cover-placeholder" />}
              </div>
              <div className="min-w-0">
                <div className="break-words font-display text-lg font-extrabold leading-tight" translate="no" data-testid="go-live-title">{release.release_title}</div>
                <div className="mt-0.5 truncate text-sm text-zinc-400" translate="no" data-testid="go-live-artist">{artistLabel}</div>
                <div className="mt-1 text-[11px] uppercase tracking-wide text-zinc-500">{release.release_type} · {tracks.length} track</div>
              </div>
            </div>

            {error && <div role="alert" className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-300" data-testid="go-live-error">{error}</div>}

            {postpone ? (
              /* Postpone: reschedule the release date */
              <div className="space-y-4" data-testid="go-live-postpone-panel">
                <div className="rounded-md border border-amber-400/30 bg-amber-500/[0.06] px-3 py-2.5 text-sm text-amber-200/90">
                  Tunda tayang bila tanggal rilis berubah. Rilisan tetap berstatus <b>dikirim ke Believe</b> dan akan muncul lagi saat tanggal baru tiba.
                </div>
                <label className="block">
                  <span className="rm-label flex items-center gap-1.5"><CalendarClock className="h-3.5 w-3.5" /> Tanggal Rilis Baru</span>
                  <input type="date" className="rm-input" value={newDate} onChange={(e) => setNewDate(e.target.value)} data-testid="go-live-postpone-date-input" />
                </label>
                <div className="flex flex-wrap justify-end gap-2">
                  <button type="button" className="rm-btn-ghost inline-flex items-center gap-2" disabled={busy} onClick={() => setPostpone(false)} data-testid="go-live-postpone-cancel-btn"><ArrowLeft className="h-4 w-4" /> Kembali</button>
                  <button type="button" className="rm-btn-primary inline-flex items-center gap-2" disabled={busy || !newDate} onClick={reschedule} data-testid="go-live-reschedule-submit-btn">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Clock className="h-4 w-4" />} Simpan Tanggal Baru</button>
                </div>
              </div>
            ) : (
              /* Go-live: UPC + ISRC form */
              <div className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="block">
                    <span className="rm-label">Tanggal Rilis</span>
                    <input type="date" className="rm-input" value={releaseDate} onChange={(e) => setReleaseDate(e.target.value)} data-testid="go-live-date-input" />
                  </label>
                  <label className="block">
                    <span className="rm-label">UPC Rilisan</span>
                    <input className="rm-input font-mono uppercase" placeholder="Isi UPC" value={upc} onChange={(e) => setUpc(e.target.value)} data-testid="go-live-upc-input" />
                  </label>
                </div>
                <div className="space-y-2">
                  <span className="rm-label">ISRC per Track</span>
                  {tracks.map((t) => (
                    <div key={t.id} className="grid grid-cols-[1fr_minmax(0,1.4fr)] items-center gap-3">
                      <div className="min-w-0 truncate text-sm text-zinc-300" translate="no">{t.track_number ? `${t.track_number}. ` : ""}{t.track_title}</div>
                      <input className="rm-input font-mono uppercase" placeholder="Isi ISRC" value={isrcs[t.id] || ""} onChange={(e) => setIsrcs((cur) => ({ ...cur, [t.id]: e.target.value }))} data-testid={`go-live-isrc-input-${t.id}`} />
                    </div>
                  ))}
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2 border-t border-white/10 pt-4">
                  <button type="button" className="rm-btn-ghost inline-flex items-center gap-2 text-amber-300" disabled={busy} onClick={() => setPostpone(true)} data-testid="go-live-postpone-btn"><Clock className="h-4 w-4" /> Tunda</button>
                  <button type="button" className="rm-btn-primary inline-flex items-center gap-2" disabled={busy} onClick={goLive} data-testid="go-live-submit-btn">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Rocket className="h-4 w-4" />} Simpan & Buat Live</button>
                </div>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
