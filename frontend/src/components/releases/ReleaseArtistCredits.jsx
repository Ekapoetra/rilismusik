import React from "react";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

export const ReleaseArtistCredits = ({ release, prefix = "release" }) => {
  const { t } = useAppPreferences();
  const main = release.display_primary_artists?.length ? release.display_primary_artists : release.artist_name ? [release.artist_name] : [];
  const featured = release.display_featured_artists || [];
  return <div className="mt-1 min-w-0 space-y-1 text-xs leading-relaxed [overflow-wrap:anywhere]" data-testid={`${prefix}-artists-${release.id}`}>
    <div data-testid={`${prefix}-primary-artists-${release.id}`}><span className="text-zinc-500">{t("Artis utama")}: </span>{main.length ? <span translate="no" className="text-zinc-300">{main.join(", ")}</span> : <span className="text-zinc-500">{t("Belum tercatat")}</span>}</div>
    {featured.length > 0 && <div data-testid={`${prefix}-featured-artists-${release.id}`}><span className="text-zinc-500">Featuring: </span><span translate="no" className="text-zinc-300">{featured.join(", ")}</span></div>}
  </div>;
};