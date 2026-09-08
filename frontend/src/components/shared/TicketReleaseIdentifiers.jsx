import React from "react";

export const TicketReleaseIdentifiers = ({ upc, tracks = [], isrcs = [], prefix = "ticket" }) => {
  const rows = tracks.length ? tracks : isrcs.map((isrc, index) => ({ track_title: `Track ${index + 1}`, isrc }));
  return <section className="min-w-0 space-y-3 border-y border-white/10 py-4" data-testid={`${prefix}-identifiers`}>
    <div><div className="text-xs text-zinc-500">UPC</div><div className="mt-1 break-all font-mono text-sm" data-testid={`${prefix}-upc`}>{upc || "Belum tersedia"}</div></div>
    <div><div className="mb-2 text-xs text-zinc-500">ISRC Track</div>{rows.length ? <ul className="space-y-2">{rows.map((track, index) => <li key={`${track.track_id || track.id || index}`} className="flex min-w-0 flex-wrap justify-between gap-x-4 gap-y-1 text-xs"><span className="min-w-0 break-words text-zinc-400" data-testid={`${prefix}-track-title-${index + 1}`}>{track.track_number || index + 1}. {track.track_title || `Track ${index + 1}`}</span><span className="break-all font-mono text-zinc-200" data-testid={`${prefix}-isrc-${index + 1}`}>{track.isrc || "Belum tersedia"}</span></li>)}</ul> : <p className="text-xs text-zinc-500" data-testid={`${prefix}-isrc-empty`}>Belum tersedia</p>}</div>
  </section>;
};