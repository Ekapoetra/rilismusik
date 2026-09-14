import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Rocket, Loader2, Disc3, ListChecks, RefreshCw } from "lucide-react";
import { api, fileUrl, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";

const isComplete = (rel, draft) => {
  const d = draft || {};
  if (!(d.upc || "").trim()) return false;
  return (rel.tracks || []).every((t) => ((d.isrcs || {})[t.id] || "").trim());
};

export default function MassGoLiveModal({ open, onClose, onDone }) {
  const [loading, setLoading] = useState(false);
  const [releases, setReleases] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [busyId, setBusyId] = useState(null);
  const [busyAll, setBusyAll] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const { data } = await api.get("/admin/releases/ready-to-live");
      const list = data.releases || [];
      setReleases(list);
      setDrafts(Object.fromEntries(list.map((r) => [r.id, {
        upc: r.upc || "",
        isrcs: Object.fromEntries((r.tracks || []).map((t) => [t.id, t.isrc || ""])),
      }])));
    } catch (e) {
      setError(formatApiError(e.response?.data?.detail) || "Gagal memuat daftar siap tayang.");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { if (open) load(); }, [open, load]);

  const setUpc = (id, v) => setDrafts((c) => ({ ...c, [id]: { ...c[id], upc: v } }));
  const setIsrc = (id, tid, v) => setDrafts((c) => ({ ...c, [id]: { ...c[id], isrcs: { ...c[id].isrcs, [tid]: v } } }));

  const completeCount = useMemo(
    () => releases.filter((r) => isComplete(r, drafts[r.id])).length,
    [releases, drafts],
  );

  const goLive = async (ids) => {
    const items = ids.map((id) => ({ release_id: id, upc: (drafts[id]?.upc || "").trim(), track_isrcs: drafts[id]?.isrcs || {} }));
    const { data } = await api.post("/admin/releases/bulk-go-live", { items });
    const okIds = new Set(data.results.filter((r) => r.ok).map((r) => r.release_id));
    const failed = data.results.filter((r) => !r.ok);
    if (okIds.size) {
      setReleases((cur) => cur.filter((r) => !okIds.has(r.id)));
      toast.success(`${okIds.size} rilisan tayang. Email dikirim ke label.`);
      onDone?.();
    }
    failed.forEach((f) => toast.error(`Gagal: ${f.error}`));
    return data;
  };

  const onRow = async (id) => {
    if (busyId || busyAll) return; setBusyId(id); setError("");
    try { await goLive([id]); }
    catch (e) { const m = formatApiError(e.response?.data?.detail) || "Gagal menayangkan."; setError(m); toast.error(m); }
    finally { setBusyId(null); }
  };

  const onAll = async () => {
    const ids = releases.filter((r) => isComplete(r, drafts[r.id])).map((r) => r.id);
    if (!ids.length || busyAll || busyId) return; setBusyAll(true); setError("");
    try { await goLive(ids); }
    catch (e) { const m = formatApiError(e.response?.data?.detail) || "Gagal menayangkan massal."; setError(m); toast.error(m); }
    finally { setBusyAll(false); }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && !busyAll && !busyId && onClose?.()}>
      <DialogContent className="ui-menu max-h-[90dvh] w-[calc(100%-2rem)] max-w-4xl overflow-y-auto rounded-lg" data-testid="mass-golive-modal" closeTestId="mass-golive-close">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><ListChecks className="h-5 w-5 text-pink-400" /> Entry Massal UPC/ISRC</DialogTitle>
          <DialogDescription>Rilisan yang sudah dikirim ke Believe dan tanggal rilisnya hari ini atau lampau. Isi UPC &amp; ISRC lalu tayangkan tanpa membuka satu per satu.</DialogDescription>
        </DialogHeader>

        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-3">
          <div className="text-sm text-zinc-400" data-testid="mass-golive-summary">
            {releases.length} siap tayang · <span className="font-bold text-emerald-300">{completeCount}</span> lengkap
          </div>
          <div className="flex items-center gap-2">
            <button type="button" onClick={load} disabled={loading || busyAll} className="rm-btn-ghost inline-flex items-center gap-2 text-sm" data-testid="mass-golive-refresh"><RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Muat ulang</button>
            <button type="button" onClick={onAll} disabled={completeCount === 0 || busyAll || busyId} className="rm-btn-primary inline-flex items-center gap-2 text-sm disabled:opacity-40" data-testid="mass-golive-all-btn">{busyAll ? <Loader2 className="h-4 w-4 animate-spin" /> : <Rocket className="h-4 w-4" />} Tayangkan Semua yang Lengkap ({completeCount})</button>
          </div>
        </div>

        {error && <div role="alert" className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-300" data-testid="mass-golive-error">{error}</div>}

        {loading ? (
          <div className="flex items-center justify-center py-16 text-sm text-zinc-500" data-testid="mass-golive-loading"><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Memuat…</div>
        ) : releases.length === 0 ? (
          <div className="rounded-md border border-white/10 py-16 text-center text-sm text-zinc-500" data-testid="mass-golive-empty">Tidak ada rilisan siap tayang untuk hari ini.</div>
        ) : (
          <div className="space-y-4 pt-2">
            {releases.map((r) => {
              const d = drafts[r.id] || { upc: "", isrcs: {} };
              const complete = isComplete(r, d);
              return (
                <div key={r.id} className={`rounded-lg border p-4 transition-colors ${complete ? "border-emerald-400/30 bg-emerald-500/[0.04]" : "border-white/10 bg-white/[0.02]"}`} data-testid={`mass-golive-row-${r.id}`}>
                  <div className="flex flex-wrap items-start gap-3">
                    <div className="grid aspect-square w-12 shrink-0 place-items-center overflow-hidden rounded-md border border-white/10 bg-white/5">
                      {r.cover_url ? <img src={fileUrl(r.cover_url)} alt={r.release_title} className="h-full w-full object-cover" data-testid={`mass-golive-cover-${r.id}`} /> : <Disc3 className="h-5 w-5 text-zinc-500" />}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="break-words font-semibold" translate="no" data-testid={`mass-golive-title-${r.id}`}>{r.release_title}</div>
                      <div className="truncate text-xs text-zinc-500" translate="no">{r.artist} · {r.label_name || "—"} · Rilis {String(r.release_date).slice(0, 10)}</div>
                    </div>
                    <button type="button" onClick={() => onRow(r.id)} disabled={!complete || busyId === r.id || busyAll} className="rm-btn-primary inline-flex items-center gap-1.5 text-xs disabled:opacity-40" data-testid={`mass-golive-row-btn-${r.id}`}>{busyId === r.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Rocket className="h-3.5 w-3.5" />} Simpan &amp; Tayangkan</button>
                  </div>
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <label className="block">
                      <span className="rm-label">UPC Rilisan</span>
                      <input className="rm-input font-mono uppercase" placeholder="Isi UPC" value={d.upc} onChange={(e) => setUpc(r.id, e.target.value)} data-testid={`mass-golive-upc-${r.id}`} />
                    </label>
                    <div />
                    {(r.tracks || []).map((t) => (
                      <label key={t.id} className="block">
                        <span className="rm-label truncate">ISRC — {t.track_title}</span>
                        <input className="rm-input font-mono uppercase" placeholder="Isi ISRC" value={d.isrcs[t.id] || ""} onChange={(e) => setIsrc(r.id, t.id, e.target.value)} data-testid={`mass-golive-isrc-${r.id}-${t.id}`} />
                      </label>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
