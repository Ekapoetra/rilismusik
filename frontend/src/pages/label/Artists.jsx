import React, { useCallback, useEffect, useState } from "react";
import { Pencil, Plus, UserSquare2 } from "lucide-react";
import { api } from "@/api/client";
import { ArtistFormModal } from "@/components/artists/ArtistFormModal";
import { SocialLinksList } from "@/components/artists/SocialLinksList";
import { ARTIST_MGMT } from "@/constants/testIds";

export default function LabelArtists() {
  const [items, setItems] = useState([]);
  const [modalArtist, setModalArtist] = useState(undefined);
  const load = useCallback(async () => { const { data } = await api.get("/artists/"); setItems(data || []); }, []);
  useEffect(() => { load(); }, [load]);
  return <div className="max-w-6xl space-y-6" data-testid="label-artists-page">
    <header className="flex flex-wrap items-end justify-between gap-4"><div><div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Artis</div><h1 className="font-display text-3xl font-extrabold">Manajemen Artis</h1><p className="mt-1 text-sm text-zinc-400">Profil dan tautan sosial ini dapat dipanggil kembali saat membuat rilisan.</p></div><button className="rm-btn-primary inline-flex items-center gap-2" onClick={() => setModalArtist(null)} data-testid={ARTIST_MGMT.addButton}><Plus className="h-4 w-4" /> Tambah Artis</button></header>
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{items.length === 0 ? <div className="col-span-full border-y border-white/10 py-14 text-center text-sm text-zinc-500" data-testid="label-artists-empty">Belum ada artis tersimpan.</div> : items.map((artist) => <article key={artist.id} className="rm-card p-5" data-testid={`label-artist-card-${artist.id}`}><div className="flex items-start gap-3"><div className="grid h-12 w-12 shrink-0 place-items-center rounded-lg bg-white/[0.06] text-zinc-300"><UserSquare2 className="h-5 w-5" /></div><div className="min-w-0 flex-1"><h2 className="truncate font-display font-bold" data-testid={`label-artist-name-${artist.id}`}>{artist.artist_name}</h2><p className="truncate text-xs text-zinc-500">{artist.email || "Profil artis rilisan"}</p></div><button type="button" title="Edit artis" onClick={() => setModalArtist(artist)} className="rounded-md p-2 text-zinc-400 transition-colors hover:bg-white/5 hover:text-white" data-testid={`label-artist-edit-${artist.id}`}><Pencil className="h-4 w-4" /></button></div><div className="mt-5"><div className="mb-2 text-[10px] font-bold uppercase tracking-widest text-zinc-500">Media Sosial</div><SocialLinksList links={artist.social_links} prefix={`label-artist-social-${artist.id}`} emptyText="Wajib dilengkapi sebelum artis dipakai pada rilisan" /></div><div className="mt-5 grid grid-cols-2 border-t border-white/10 pt-4 text-xs"><div><div className="text-zinc-500">Status</div><strong className="capitalize text-zinc-200">{artist.status || "aktif"}</strong></div><div><div className="text-zinc-500">Royalti belum ditarik</div><strong className="font-mono text-emerald-300">Rp {Number(artist.revenue_idr || 0).toLocaleString("id-ID")}</strong></div></div></article>)}</div>
    {modalArtist !== undefined && <ArtistFormModal artist={modalArtist} onClose={() => setModalArtist(undefined)} onSaved={load} />}
  </div>;
}