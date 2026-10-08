import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, ChevronLeft, ChevronRight, Filter, Search, Trash2 } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import StatusBadge, { STATUS_LABELS } from "@/components/shared/StatusBadge";
import { ReleaseArtwork } from "@/components/releases/ReleaseArtwork";
import { ReleaseArtistCredits } from "@/components/releases/ReleaseArtistCredits";
import { WamiBadge } from "@/components/shared/WamiBadge";
import { ReleaseCoverGrid } from "@/components/releases/ReleaseCoverGrid";
import { ReleaseViewToggle, useReleaseView } from "@/components/releases/ReleaseViewToggle";

const IN_PROCESS = ["submitted", "awaiting_payment", "paid", "under_review", "approved", "delivered", "takedown_requested"];
const TABS = [
  ["all", "Semua", () => true],
  ["draft", "Draft", (r) => r.status === "draft"],
  ["process", "Dalam Proses", (r) => IN_PROCESS.includes(r.status)],
  ["revision", "Perlu Perbaikan", (r) => r.status === "need_revision" || r.status === "rejected"],
  ["live", "Tayang", (r) => r.status === "live"],
];
const MODE = { standard: "Rilis Musik Standar", express: "Rilis Musik Express", max: "Rilis Musik MAX" };
const PAGE = 10;
const day = (value) => (value ? new Date(`${String(value).slice(0, 10)}T00:00:00+07:00`).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Jakarta" }) : "—");

// V13 list105: catalogue with status tabs, search across title/artist/UPC/ISRC and filters.
export default function LabelReleases() {
  const { t } = useAppPreferences();
  const [items, setItems] = useState(null);
  const [tab, setTab] = useState("all");
  const [q, setQ] = useState("");
  const [showFilter, setShowFilter] = useState(false);
  const [filter, setFilter] = useState({ type: "", status: "", wami: "", from: "", to: "" });
  const [page, setPage] = useState(0);
  const [deletingId, setDeletingId] = useState(null);
  const [viewMode, setViewMode] = useReleaseView("rm-label-release-view");

  const load = useCallback(async () => {
    const { data } = await api.get("/releases/", { params: { limit: 500 } });
    setItems(Array.isArray(data) ? data : []);
  }, []);
  useEffect(() => { load().catch((e) => { toast.error(formatApiError(e.response?.data?.detail)); setItems([]); }); }, [load]);
  useEffect(() => { setPage(0); }, [tab, q, filter]);

  const rows = useMemo(() => {
    const match = TABS.find(([key]) => key === tab)[2];
    const term = q.trim().toLowerCase();
    return (items || []).filter((release) => {
      if (!match(release)) return false;
      if (filter.type && release.release_type !== filter.type) return false;
      if (filter.status && release.status !== filter.status) return false;
      if (filter.wami && Boolean(release.wami_registered) !== (filter.wami === "yes")) return false;
      if (filter.from && String(release.release_date || "") < filter.from) return false;
      if (filter.to && String(release.release_date || "") > filter.to) return false;
      if (!term) return true;
      const text = [release.release_title, release.artist_name, ...(release.display_primary_artists || []), release.upc, ...(release.track_identifiers || []).map((track) => track.isrc)].filter(Boolean).join(" ").toLowerCase();
      return text.includes(term);
    });
  }, [items, tab, q, filter]);
  const counts = useMemo(() => Object.fromEntries(TABS.map(([key, , match]) => [key, (items || []).filter(match).length])), [items]);
  const pages = Math.max(1, Math.ceil(rows.length / PAGE));
  const view = rows.slice(page * PAGE, page * PAGE + PAGE);

  const deleteRelease = async (release) => {
    if (!window.confirm(`${t("Hapus rilisan")} “${release.release_title}”? ${t("Tindakan ini tidak dapat dibatalkan.")}`)) return;
    setDeletingId(release.id);
    try { await api.delete(`/releases/${release.id}`); toast.success(t("Rilisan dihapus.")); await load(); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setDeletingId(null); }
  };

  return <div className="space-y-5" data-testid="label-releases">
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div><div className="v13-section-label">Catalogue · Rilis Musik</div><h1 className="mt-1 text-3xl">{t("Rilisan")}</h1><p className="mt-1 text-sm text-[var(--ui-muted)]">{t("Dari ide pertama hingga terdengar di mana saja.")}</p></div>
      <Link to="/label/releases/upload" className="v13-plan-cta gap-2 px-5" style={{ width: "auto" }} data-testid="label-releases-upload-button">{t("Buat Rilisan")} <ArrowUpRight className="h-4 w-4" /></Link>
    </header>
    <nav className="v13-tabs" style={{ display: "inline-flex" }}>{TABS.map(([key, name]) => <a key={key} href={`#${key}`} onClick={(event) => { event.preventDefault(); setTab(key); }} className={tab === key ? "is-active" : ""} data-testid={`label-releases-tab-${key}`}>{t(name)}<span className="ml-1 opacity-60">{counts[key] ?? ""}</span></a>)}</nav>
    <section className="v13-card overflow-hidden">
      <div className="flex flex-wrap items-center gap-2 px-5 pt-5">
        <div className="relative min-w-[240px] flex-1"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--ui-muted)]" /><input value={q} onChange={(event) => setQ(event.target.value)} placeholder={t("Cari judul, artis, UPC atau ISRC")} className="v13-select w-full" style={{ height: 38, paddingLeft: 36 }} data-testid="label-releases-search" /></div>
        <button type="button" onClick={() => setShowFilter(!showFilter)} aria-expanded={showFilter} className="inline-flex items-center gap-2 rounded-full border border-[var(--ui-border)] px-4 py-2 text-sm"><Filter className="h-4 w-4" />{t("Filter")}</button>
        <div className="ml-auto"><ReleaseViewToggle view={viewMode} onChange={setViewMode} prefix="label-releases" /></div>
      </div>
      {showFilter && <div className="flex flex-wrap items-end gap-2 px-5 pt-3" data-testid="label-releases-filters">
        <select value={filter.type} onChange={(event) => setFilter({ ...filter, type: event.target.value })} className="v13-select"><option value="">{t("Semua jenis")}</option><option value="single">Single</option><option value="ep">EP</option><option value="album">Album</option></select>
        <select value={filter.status} onChange={(event) => setFilter({ ...filter, status: event.target.value })} className="v13-select"><option value="">{t("Semua status")}</option>{Object.entries(STATUS_LABELS).map(([key, name]) => <option key={key} value={key}>{t(name)}</option>)}</select>
        <select value={filter.wami} onChange={(event) => setFilter({ ...filter, wami: event.target.value })} className="v13-select" data-testid="label-releases-wami-filter"><option value="">WAMI</option><option value="no">{t("Belum terdaftar")}</option><option value="yes">{t("Terdaftar")}</option></select>
        <label className="text-xs text-[var(--ui-muted)]">{t("Tanggal mulai")}<input type="date" value={filter.from} onChange={(event) => setFilter({ ...filter, from: event.target.value })} className="v13-select ml-1" /></label>
        <label className="text-xs text-[var(--ui-muted)]">{t("Tanggal akhir")}<input type="date" value={filter.to} onChange={(event) => setFilter({ ...filter, to: event.target.value })} className="v13-select ml-1" /></label>
        <button type="button" className="text-sm text-[var(--ui-muted)] underline" onClick={() => setFilter({ type: "", status: "", wami: "", from: "", to: "" })}>{t("Reset filter")}</button>
      </div>}
      {viewMode === "cover" ? <div className="p-5"><ReleaseCoverGrid items={rows} basePath="/label/releases" prefix="label-release" renderActions={(r) => <>
        <Link to={`/label/releases/${r.id}`} className="text-xs" data-testid={`label-release-detail-${r.id}`}>{t("Detail")} →</Link>
        {["draft", "rejected"].includes(r.status) && <button type="button" onClick={() => deleteRelease(r)} disabled={deletingId === r.id} className="ml-auto rounded p-2 text-[var(--ui-muted)] hover:text-[var(--v13-urgent)] disabled:opacity-40" aria-label={`${t("Hapus")} ${r.release_title}`} data-testid={`label-release-delete-${r.id}`}><Trash2 className="h-4 w-4" /></button>}
      </>} /></div> : <div className="overflow-x-auto"><table className="mt-3 w-full min-w-[760px] text-sm">
        <thead><tr className="text-left text-xs uppercase tracking-wide text-[var(--ui-muted)]">{["Rilisan / Artis", "Tanggal rilis", "Perkembangan", ""].map((head) => <th key={head} className="px-5 py-3 font-normal">{t(head)}</th>)}</tr></thead>
        <tbody>{items === null ? <tr><td colSpan={4} className="px-5 py-8 text-center text-[var(--ui-muted)]">{t("Memuat rilisan…")}</td></tr> : view.length === 0 ? <tr><td colSpan={4} className="px-5 py-8 text-center text-[var(--ui-muted)]" data-testid="label-releases-empty">{t("Belum ada rilisan pada tampilan ini.")}</td></tr> : view.map((release) => {
          const edit = release.status === "draft" || release.status === "need_revision";
          return <tr key={release.id} className="border-t border-[var(--ui-border)] align-middle" data-testid={`label-release-row-${release.id}`}>
            <td className="px-5 py-3"><div className="flex items-center gap-3"><ReleaseArtwork release={release} prefix="label-list" onUpdated={(patch) => setItems((current) => current.map((item) => item.id === release.id ? { ...item, ...patch } : item))} /><div className="min-w-0"><Link to={`/label/releases/${release.id}`} className="font-medium hover:underline">{release.release_title || t("Tanpa judul")}</Link><ReleaseArtistCredits release={release} prefix="label-release" compact />{release.wami_registered && <WamiBadge testid={`label-release-wami-${release.id}`} />}</div></div></td>
            <td className="px-5 py-3"><div>{day(release.release_date)}</div><div className="text-xs text-[var(--ui-muted)]">{t(MODE[release.service_mode] || MODE.standard)}</div></td>
            <td className="px-5 py-3"><StatusBadge status={release.status} />{release.status === "need_revision" && release.admin_note && <div className="mt-1 max-w-[260px] truncate text-xs text-[var(--ui-muted)]">{release.admin_note}</div>}</td>
            <td className="px-5 py-3 text-right"><div className="flex items-center justify-end gap-2">
              {["draft", "rejected"].includes(release.status) && <button type="button" onClick={() => deleteRelease(release)} disabled={deletingId === release.id} className="rounded-full p-2 text-[var(--ui-muted)] hover:text-[var(--v13-urgent)]" aria-label={t("Hapus")} data-testid={`label-release-delete-${release.id}`}><Trash2 className="h-4 w-4" /></button>}
              {edit ? <Link to={`/label/releases/${release.id}/edit`} className="v13-plan-cta px-4 py-1.5 text-xs" style={{ width: "auto" }}>{t(release.status === "draft" ? "Lanjutkan" : "Perbaiki")}</Link> : <Link to={`/label/releases/${release.id}`} className="v13-chevron" aria-label={t("Buka")}><ArrowUpRight /></Link>}
            </div></td>
          </tr>;
        })}</tbody>
      </table></div>}
      {viewMode !== "cover" && pages > 1 && <div className="flex items-center justify-center gap-3 py-4 text-sm"><button type="button" className="v13-chevron" disabled={page === 0} onClick={() => setPage(page - 1)} aria-label={t("Sebelumnya")}><ChevronLeft /></button><span className="tabular-nums text-[var(--ui-muted)]">{page + 1} / {pages}</span><button type="button" className="v13-chevron" disabled={page >= pages - 1} onClick={() => setPage(page + 1)} aria-label={t("Berikutnya")}><ChevronRight /></button></div>}
    </section>
  </div>;
}
