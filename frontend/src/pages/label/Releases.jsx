import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import StatusBadge, { STATUS_LABELS } from "@/components/shared/StatusBadge";
import { toast } from "@/components/ui/sonner";
import { Search, Filter, Trash2 } from "lucide-react";
import { ReleaseArtistCredits } from "@/components/releases/ReleaseArtistCredits";
import { ReleaseArtwork } from "@/components/releases/ReleaseArtwork";
import { SubmissionQuota } from "@/components/label/SubmissionQuota";

const STATUSES = ["draft", "submitted", "awaiting_payment", "paid", "under_review", "need_revision", "approved", "delivered", "live", "rejected", "taken_down"];

export default function LabelReleases() {
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [deletingId, setDeletingId] = useState(null);

  const load = useCallback(async () => {
    const { data } = await api.get("/releases/", { params: { status: status || undefined, q: q || undefined } });
    setItems(data);
  }, [status, q]);
  useEffect(() => { load(); }, [load]);

  const deleteRelease = async (release) => {
    if (!window.confirm(`Hapus rilisan “${release.release_title}”? Tindakan ini tidak dapat dibatalkan.`)) return;
    setDeletingId(release.id);
    try {
      await api.delete(`/releases/${release.id}`);
      toast.success("Rilisan dihapus.");
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setDeletingId(null); }
  };

  return (
    <div className="space-y-5 max-w-6xl">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Rilisan</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter">Daftar Rilisan</h1>
        </div>
        <Link to="/label/releases/upload" className="rm-btn-primary" data-testid="label-releases-upload-button">+ Ajukan Rilisan</Link>
      </div>

      {/* Filters */}
      <div className="rm-card p-4 flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="rm-label">Cari Judul</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600" />
            <input className="rm-input pl-10" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()} placeholder="Cari rilisan…" data-testid="label-releases-search" />
          </div>
        </div>
        <div className="min-w-[180px]">
          <label className="rm-label">Status</label>
          <select className="rm-input" value={status} onChange={(e) => setStatus(e.target.value)} data-testid="label-releases-status-filter">
            <option value="">Semua</option>
            {STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABELS[s] || s}</option>)}
          </select>
        </div>
        <button className="rm-btn-ghost flex items-center gap-2" onClick={load} data-testid="label-releases-apply-filter"><Filter className="w-4 h-4" /> Filter</button>
      </div>

      {/* Table */}
      <SubmissionQuota />
      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5">
          <div className="col-span-5">Judul / Artist</div>
          <div className="col-span-2">Tipe</div>
          <div className="col-span-2">Tanggal Rilis</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-1 text-right">Aksi</div>
        </div>
        {items.length === 0 ? (
          <div className="p-10 text-center text-zinc-500 text-sm">Belum ada rilisan.</div>
        ) : items.map((r) => (
          <div key={r.id} className="px-5 py-4 border-b border-white/5 last:border-0 grid grid-cols-12 gap-3 items-center hover:bg-white/[0.02]" data-testid={`label-release-row-${r.id}`}>
            <div className="min-w-0 col-span-12 md:col-span-5 flex items-start gap-3">
              <ReleaseArtwork release={r} prefix="label-list" onUpdated={(patch) => setItems((current) => current.map((item) => item.id === r.id ? { ...item, ...patch } : item))} />
              <div className="min-w-0">
                <Link to={`/label/releases/${r.id}`} className="font-semibold break-words [overflow-wrap:anywhere]" translate="no" data-testid={`label-release-title-${r.id}`}>{r.release_title}</Link>
                <ReleaseArtistCredits release={r} prefix="label-release" />
              </div>
            </div>
            <div className="col-span-6 md:col-span-2 text-sm capitalize">{r.release_type}</div>
            <div className="col-span-6 md:col-span-2 text-sm">{r.release_date}</div>
            <div className="col-span-6 md:col-span-2 flex items-center gap-2"><StatusBadge status={r.status} />{r.status === "draft" && <button type="button" onClick={() => deleteRelease(r)} disabled={deletingId === r.id} className="text-red-300 hover:text-red-200 disabled:opacity-40" title="Hapus draft" data-testid={`label-release-delete-status-${r.id}`}><Trash2 className="w-3.5 h-3.5" /></button>}</div>
            <div className="col-span-6 md:col-span-1 text-right flex items-center justify-end gap-3"><Link to={`/label/releases/${r.id}`} className="text-sm font-semibold rm-gradient-text" data-testid={`label-release-detail-${r.id}`}>Detail →</Link>{r.status === "rejected" && <button type="button" onClick={() => deleteRelease(r)} disabled={deletingId === r.id} className="text-red-300 hover:text-red-200 disabled:opacity-40" title="Hapus rilisan" data-testid={`label-release-delete-${r.id}`}><Trash2 className="w-4 h-4" /></button>}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
