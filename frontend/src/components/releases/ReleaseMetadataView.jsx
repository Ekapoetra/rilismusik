import React from "react";
import { ExternalLink, FileAudio, Mic2, Copy } from "lucide-react";
import { toast } from "sonner";
import { fileUrl } from "@/api/client";
import { formatReleaseDate } from "@/utils/releaseDate";
import { SocialLinksList } from "@/components/artists/SocialLinksList";
import { AudioPreviewButton } from "./AudioPreviewButton";

const Row = ({ label, value, mono = false, testId }) => <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)] gap-4 border-b border-white/5 py-2.5 last:border-0"><dt className="text-xs text-zinc-500">{label}</dt><dd className={`break-words text-right text-sm text-zinc-200 ${mono ? "font-mono" : "font-semibold"}`} data-testid={testId} translate="no">{value || "—"}</dd></div>;
const LinkValue = ({ href, children, testId }) => href ? <a href={href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sky-300 hover:text-sky-200" data-testid={testId}>{children}<ExternalLink className="h-3 w-3" /></a> : "—";
const ArtistCredits = ({ title, artists, prefix }) => <section><h3 className="mb-3 text-xs font-bold uppercase text-zinc-500">{title}</h3><div className="space-y-3">{artists?.length ? artists.map((artist, index) => { const links = artist.social_links?.length ? artist.social_links : artist.spotify_url ? [{ platform: "spotify", url: artist.spotify_url }] : []; return <div className="border-l-2 border-white/10 pl-4 text-sm" key={`${artist.name}-${index}`} data-testid={`${prefix}-${index}`}><strong translate="no">{artist.name}</strong><div className="mt-2"><SocialLinksList links={links} prefix={`${prefix}-social-${index}`} /></div></div>; }) : <span className="text-sm text-zinc-500">Tidak ada</span>}</div></section>;

const copyText = async (text, label) => {
  if (!text || !text.trim()) { toast.error("Tidak ada lirik untuk disalin"); return; }
  try { await navigator.clipboard.writeText(text); toast.success(`${label} disalin ke clipboard`); }
  catch { toast.error("Gagal menyalin. Coba lagi."); }
};

export const ReleaseMetadataView = ({ release, allowCopyLyrics = false }) => {
  const copyAllLyrics = () => {
    const blocks = (release.tracks || []).filter((t) => (t.lyrics || "").trim()).map((t) => `# ${t.track_number || ""} ${t.track_title}\n${t.lyrics.trim()}`);
    copyText(blocks.join("\n\n" + "-".repeat(30) + "\n\n"), "Semua lirik");
  };
  return <div className="space-y-8" data-testid="release-metadata-view">
  <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
    <section className="min-w-0"><h2 className="mb-3 font-display text-lg font-bold">Informasi Rilisan</h2><dl className="border-y border-white/10">
      <Row label="Judul" value={release.release_title} testId="release-metadata-title" />
      <Row label="Nama Label" value={release.label_name_snapshot} testId="release-metadata-label" />
      <Row label="Tipe" value={String(release.release_type || "").toUpperCase()} testId="release-metadata-type" />
      <Row label="Genre / Sub Genre" value={[release.genre, release.subgenre].filter(Boolean).join(" / ")} testId="release-metadata-genre" />
      <Row label="Tanggal Rilis Digital" value={formatReleaseDate(release.release_date)} testId="release-metadata-release-date" />
      <Row label="Tahun Produksi" value={release.year} testId="release-metadata-year" />
      <Row label="C Line" value={release.copyright_line} mono testId="release-metadata-c-line" />
      <Row label="P Line" value={release.p_line} mono testId="release-metadata-p-line" />
      <Row label="UPC" value={release.upc} mono testId="release-metadata-upc" />
      <Row label="Penanggung Jawab" value={release.responsible_name} testId="release-metadata-responsible" />
      <Row label="Web Artis / YouTube" value={<LinkValue href={release.artist_web_url} testId="release-metadata-artist-web">{release.artist_web_url}</LinkValue>} testId="release-metadata-artist-web-value" />
    </dl></section>
    <div className="min-w-0 space-y-7"><ArtistCredits title="Artis Utama" artists={release.primary_artists?.length ? release.primary_artists : [{ name: release.artist_name }]} prefix="release-primary-artist" /><ArtistCredits title="Artis Featuring" artists={release.featured_artists} prefix="release-featured-artist" />{release.cover_url && <section><h3 className="mb-3 text-xs font-bold uppercase text-zinc-500">Sampul 3000×3000</h3><img src={fileUrl(release.cover_url)} alt={`Sampul ${release.release_title}`} className="aspect-square w-full max-w-sm border border-white/10 object-contain" data-testid="release-metadata-cover" /></section>}</div>
  </div>
  <section><div className="mb-4 flex flex-wrap items-center justify-between gap-2"><div className="flex items-center gap-2"><Mic2 className="h-5 w-5 text-zinc-500" /><h2 className="font-display text-lg font-bold">Track dan Kredit</h2></div>{allowCopyLyrics && <button type="button" onClick={copyAllLyrics} className="inline-flex items-center gap-1.5 rounded-md border border-white/15 bg-white/[0.03] px-3 py-1.5 text-xs font-semibold text-zinc-200 transition-colors hover:bg-white/10" data-testid="release-copy-all-lyrics"><Copy className="h-3.5 w-3.5" /> Salin Semua Lirik</button>}</div><div className="divide-y divide-white/10 border-y border-white/10">{release.tracks?.map((track, index) => <article className="py-7" key={track.id} data-testid={`release-track-detail-${track.id}`}>
    <div className="mb-5 flex flex-wrap items-start justify-between gap-3"><div className="min-w-0"><div className="text-xs font-bold uppercase text-zinc-500">Track {track.track_number || index + 1}</div><h3 className="break-words font-display text-xl font-bold" data-testid={`release-track-title-${track.id}`} translate="no">{track.track_title}</h3><div className="mt-1 break-words text-xs text-zinc-500" translate="no" data-testid={`release-track-artist-credits-${track.id}`}>{track.artist_name || release.artist_name}{track.featured_artists?.length ? ` feat. ${track.featured_artists.map((artist) => artist.name).join(", ")}` : track.featuring_artist_name ? ` feat. ${track.featuring_artist_name}` : ""}</div></div>{track.audio_url ? <AudioPreviewButton release={release} track={track} /> : <span className="inline-flex items-center gap-2 text-xs text-zinc-500"><FileAudio className="h-4 w-4" />Audio belum tersedia</span>}</div>
    {!!track.featured_artists?.length && <div className="mb-5"><ArtistCredits title="Featuring Track" artists={track.featured_artists} prefix={`release-track-featured-${track.id}`} /></div>}
    <div className="grid gap-x-8 lg:grid-cols-2"><dl><Row label="ISRC" value={track.isrc} mono testId={`release-track-isrc-${track.id}`} /><Row label="Vokal / Instrumental" value={track.vocal_type === "instrumental" ? "Instrumental" : "Ada Vokal"} testId={`release-track-vocal-type-${track.id}`} /><Row label="Writer" value={track.lyricist} testId={`release-track-writer-${track.id}`} /><Row label="Komposer" value={track.composer} testId={`release-track-composer-${track.id}`} /><Row label="Arranger" value={track.arranger} testId={`release-track-arranger-${track.id}`} /><Row label="Produser" value={track.producer} testId={`release-track-producer-${track.id}`} /></dl><dl><Row label="Explicit" value={track.explicit ? "YA" : "TIDAK"} testId={`release-track-explicit-${track.id}`} /><Row label="Preview" value={`${track.preview_start_seconds || 0} detik`} testId={`release-track-preview-${track.id}`} /><Row label="Bahasa Judul" value={track.title_language} testId={`release-track-title-language-${track.id}`} /><Row label="Bahasa Lirik" value={track.lyric_language} testId={`release-track-lyric-language-${track.id}`} /><Row label="Audio" value={track.audio_sample_rate ? `WAV ${(track.audio_sample_rate / 1000).toLocaleString("id-ID")} kHz` : "—"} testId={`release-track-audio-format-${track.id}`} /></dl></div>
    <div className="mt-5"><div className="mb-2 flex items-center justify-between gap-2"><div className="text-xs font-bold uppercase text-zinc-500">Lirik</div>{allowCopyLyrics && (track.lyrics || "").trim() && <button type="button" onClick={() => copyText(track.lyrics, `Lirik "${track.track_title}"`)} className="inline-flex items-center gap-1.5 rounded-md border border-white/15 bg-white/[0.03] px-2.5 py-1 text-[11px] font-semibold text-zinc-200 transition-colors hover:bg-white/10" data-testid={`release-copy-lyrics-${track.id}`}><Copy className="h-3 w-3" /> Salin Lirik</button>}</div><pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words border-l-2 border-white/10 pl-4 font-sans text-sm leading-7 text-zinc-300" data-testid={`release-track-lyrics-${track.id}`} translate="no">{track.lyrics || "—"}</pre></div>
  </article>)}</div></section>
  </div>;
};