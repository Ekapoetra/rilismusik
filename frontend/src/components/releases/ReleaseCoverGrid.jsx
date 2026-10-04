import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Disc3 } from "lucide-react";
import { fileUrl } from "@/api/client";
import StatusBadge from "@/components/shared/StatusBadge";
import { ReleaseArtistCredits } from "@/components/releases/ReleaseArtistCredits";
import { WamiBadge } from "@/components/shared/WamiBadge";
import { formatReleaseDate } from "@/utils/releaseDate";

const coverSrc = (r) => (r.imported_legacy && r.internal_cover_url) || r.display_cover_url || r.cover_url || "";

function CoverImage({ src, release, prefix }) {
  const [failed, setFailed] = useState(false);
  return src && !failed
    ? <img src={fileUrl(src)} alt={release.release_title} width="600" height="600" loading="lazy" decoding="async" onError={() => setFailed(true)} className="h-full w-full object-cover transition-transform duration-300 motion-safe:group-hover:scale-[1.03]" data-testid={`${prefix}-cover-img-${release.id}`} />
    : <div className="grid h-full w-full place-items-center bg-gradient-to-br from-zinc-800 to-zinc-950" role="img" aria-label="Cover belum tersedia" data-testid={`${prefix}-cover-placeholder-${release.id}`}><Disc3 className="h-12 w-12 text-zinc-600" /></div>;
}

// Spotify-style grid: large cover with title + artist + status below.
export const ReleaseCoverGrid = ({ items, basePath, prefix = "release", renderMeta, renderActions, loading = false }) => {
  if (!items?.length && loading) return <div role="status" className="rm-card p-10 text-center text-sm text-zinc-400">Memuat rilisan…</div>;
  if (!items?.length) return <div className="rm-card p-10 text-center text-sm text-zinc-500">Belum ada rilisan.</div>;
  return (
    <div className="grid grid-cols-2 items-start gap-x-4 gap-y-6 sm:grid-cols-3 sm:gap-5 xl:grid-cols-4 2xl:grid-cols-5" data-testid={`${prefix}-cover-grid`}>
      {items.map((r) => {
        const src = coverSrc(r);
        return (
          <article
            key={r.id}
            className="group min-w-0 rounded-xl bg-white/[0.02] p-2.5 transition-colors hover:bg-white/[0.06] sm:p-3"
            data-testid={`${prefix}-cover-card-${r.id}`}
          >
            <Link to={`${basePath}/${r.id}`} className="block min-w-0 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pink-400" data-testid={`${prefix}-cover-open-${r.id}`}>
              <div className="aspect-square w-full overflow-hidden rounded-lg bg-white/5 shadow-xl">
                <CoverImage key={`${r.id}:${src}`} src={src} release={r} prefix={prefix} />
              </div>
              <div className="mt-3 truncate text-sm font-semibold" translate="no" title={r.release_title} data-testid={`${prefix}-cover-title-${r.id}`}>{r.release_title}</div>
              <ReleaseArtistCredits release={r} prefix={`${prefix}-cover`} compact />
            </Link>
            <div className="mt-1 min-w-0 text-[11px] leading-relaxed text-zinc-500">
              <div className="capitalize">{r.release_type}{r.release_date ? ` · ${formatReleaseDate(r.release_date)}` : ""}</div>
              {r.imported_legacy && r.internal_cover_url && <div className="text-amber-400">Cover internal</div>}
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              <StatusBadge status={r.status} />
              {r.wami_registered && <WamiBadge testid={`${prefix}-cover-wami-${r.id}`} />}
            </div>
            {renderMeta && <div className="mt-2 min-w-0 text-xs text-zinc-400">{renderMeta(r)}</div>}
            {renderActions && <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-white/5 pt-2">{renderActions(r)}</div>}
          </article>
        );
      })}
    </div>
  );
};

export default ReleaseCoverGrid;
