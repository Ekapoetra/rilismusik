import React from "react";
import { ChevronDown, Copy } from "lucide-react";
import { toast } from "@/components/ui/sonner";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

export const ReleaseIsrcToggle = ({ release, open, onToggle }) => {
  const { t } = useAppPreferences();
  const tracks = release.track_identifiers || [];
  const filled = tracks.filter((track) => track.isrc).length;
  return <button type="button" className="relative z-10 inline-flex max-w-full items-center gap-1 rounded-md border border-white/10 px-2 py-1.5 text-left text-xs transition-colors hover:bg-white/10 disabled:opacity-50" disabled={!tracks.length} aria-expanded={open} aria-controls={`release-isrc-panel-${release.id}`} onClick={onToggle} data-testid={`admin-release-isrc-toggle-${release.id}`}>
    <span data-testid={`admin-release-isrc-count-${release.id}`}>{tracks.length ? `${filled}/${tracks.length} ISRC` : t("Belum ada track")}</span><ChevronDown className={`h-3.5 w-3.5 shrink-0 transition-transform ${open ? "rotate-180" : ""}`} />
  </button>;
};

export const ReleaseIsrcPanel = ({ release }) => {
  const { t } = useAppPreferences();
  const copy = async (value) => {
    try { await navigator.clipboard.writeText(value); toast.success(t("ISRC disalin.")); }
    catch { toast.error(t("ISRC gagal disalin.")); }
  };
  return <section id={`release-isrc-panel-${release.id}`} className="relative z-10 col-span-12 min-w-0 border-t border-white/10 pt-4 xl:col-span-full" aria-label={t("ISRC per Track")} data-testid={`admin-release-isrc-panel-${release.id}`}>
    <h2 className="mb-3 text-sm font-semibold">{t("ISRC per Track")}</h2>
    <div className="divide-y divide-white/5">{(release.track_identifiers || []).map((track, index) => <div key={track.id} className="grid min-w-0 grid-cols-[24px_minmax(0,1fr)] items-start gap-2 py-2 sm:grid-cols-[28px_minmax(0,1fr)_180px]" data-testid={`admin-release-track-identifier-${release.id}-${track.id}`}>
      <span className="text-xs text-zinc-500" data-testid={`admin-release-track-number-${release.id}-${track.id}`}>{track.track_number || index + 1}</span>
      <span className="min-w-0 break-words text-sm [overflow-wrap:anywhere]" translate="no" data-testid={`admin-release-track-title-${release.id}-${track.id}`}>{track.track_title || "—"}</span>
      <div className="col-start-2 flex min-w-0 items-center gap-2 sm:col-start-auto"><code translate="no" className="break-all text-xs" data-testid={`admin-release-track-isrc-${release.id}-${track.id}`}>{track.isrc || "—"}</code>{track.isrc && <button type="button" onClick={() => copy(track.isrc)} className="shrink-0 rounded p-1 text-zinc-500 transition-colors hover:text-pink-400" title={t("Salin ISRC")} aria-label={t("Salin ISRC")} data-testid={`admin-release-track-isrc-copy-${release.id}-${track.id}`}><Copy className="h-3.5 w-3.5" /></button>}</div>
    </div>)}</div>
  </section>;
};