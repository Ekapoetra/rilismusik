import React from "react";
import { Link } from "react-router-dom";
import { Disc3 } from "lucide-react";
import { fileUrl } from "@/api/client";
import StatusBadge from "@/components/shared/StatusBadge";
import { ReleaseArtistCredits } from "@/components/releases/ReleaseArtistCredits";
import { WamiBadge } from "@/components/shared/WamiBadge";

const coverSrc = (r) => (r.imported_legacy && r.internal_cover_url) || r.cover_url || "";

// Spotify-style grid: large cover with title + artist + status below.
export const ReleaseCoverGrid = ({ items, basePath, prefix = "release" }) => {
  if (!items?.length) return <div className="rm-card p-10 text-center text-sm text-zinc-500">Belum ada rilisan.</div>;
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5" data-testid={`${prefix}-cover-grid`}>
      {items.map((r) => {
        const src = coverSrc(r);
        return (
          <Link
            key={r.id}
            to={`${basePath}/${r.id}`}
            className="group rounded-xl border border-white/5 bg-white/[0.02] p-3 transition-all hover:-translate-y-1 hover:border-white/15 hover:bg-white/[0.05]"
            data-testid={`${prefix}-cover-card-${r.id}`}
          >
            <div className="relative aspect-square w-full overflow-hidden rounded-lg border border-white/10 bg-white/5 shadow-lg">
              {src
                ? <img src={fileUrl(src)} alt={r.release_title} loading="lazy" className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105" data-testid={`${prefix}-cover-img-${r.id}`} />
                : <div className="grid h-full w-full place-items-center"><Disc3 className="h-10 w-10 text-zinc-600" /></div>}
              <div className="absolute left-2 top-2"><StatusBadge status={r.status} /></div>
              {r.wami_registered && <div className="absolute right-2 top-2"><WamiBadge testid={`${prefix}-cover-wami-${r.id}`} /></div>}
            </div>
            <div className="mt-3 min-w-0">
              <div className="truncate font-semibold" translate="no" title={r.release_title} data-testid={`${prefix}-cover-title-${r.id}`}>{r.release_title}</div>
              <ReleaseArtistCredits release={r} prefix={`${prefix}-cover`} />
              <div className="mt-1 text-[11px] uppercase tracking-wide text-zinc-500">{r.release_type}{r.release_date ? ` · ${r.release_date}` : ""}</div>
            </div>
          </Link>
        );
      })}
    </div>
  );
};

export default ReleaseCoverGrid;
