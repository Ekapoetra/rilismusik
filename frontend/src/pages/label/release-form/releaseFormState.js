export const todayPlus = (days) => {
  const value = new Date(); value.setDate(value.getDate() + days);
  return value.toISOString().slice(0, 10);
};

import { newSocialLink, socialLinksAreValid } from "@/constants/socialPlatforms";

export const newArtist = () => ({ client_id: crypto.randomUUID(), artist_id: null, name: "", spotify_url: "", social_links: [newSocialLink()] });
export const newTrack = () => ({
  client_id: crypto.randomUUID(), id: null, track_title: "", isrc: "",
  vocal_type: "vocal", lyricist: "", composer: "", arranger: "", producer: "",
  explicit: false, preview_start_seconds: 0, title_language: "Indonesian",
  lyric_language: "Indonesian", lyrics: "", audio_url: null, audio_sample_rate: null,
  featured_artists: [],
});

export const defaultReleaseForm = () => ({
  release_title: "", release_type: "single", release_date: todayPlus(7),
  genre: "", subgenre: "", copyright_line: "", p_line: "",
  year: new Date().getFullYear(), artist_web_url: "",
  primary_artists: [newArtist()], featured_artists: [], tracks: [newTrack()],
  platforms: ["Spotify", "Apple Music", "YouTube Music", "TikTok"], notes: "",
});

const withClientId = (item) => ({ ...item, client_id: item.client_id || crypto.randomUUID() });
const mapArtistCredit = (item) => {
  const socialLinks = item.social_links?.length ? item.social_links : item.spotify_url ? [{ platform: "spotify", url: item.spotify_url }] : [];
  return withClientId({ ...item, artist_id: item.artist_id || null, social_links: socialLinks.map(withClientId) });
};
export const mapReleaseToForm = (release) => ({
  ...defaultReleaseForm(), ...release,
  artist_web_url: release.artist_web_url || "",
  primary_artists: (release.primary_artists?.length ? release.primary_artists : [{ name: release.artist_name || "", spotify_url: "" }]).map(mapArtistCredit),
  featured_artists: (release.featured_artists || []).map(mapArtistCredit),
  tracks: (release.tracks?.length ? release.tracks : [newTrack()]).map((track) => withClientId({ ...newTrack(), ...track,
    featured_artists: (track.featured_artists?.length ? track.featured_artists : track.featuring_artist_name ? [{ name: track.featuring_artist_name, artist_id: track.featuring_artist_id }] : []).map(mapArtistCredit) })),
});

export const serializeReleaseForm = (form) => {
  const serializeArtist = ({ client_id, social_links, ...item }) => {
    const links = (social_links || []).map(({ client_id: linkClientId, ...link }) => link);
    return { ...item, social_links: links, spotify_url: links.find((link) => link.platform === "spotify")?.url || null };
  };
  const primary = form.primary_artists.map(serializeArtist);
  const featured = form.featured_artists.map(serializeArtist).filter((item) => item.name.trim());
  const artistName = primary.map((item) => item.name.trim()).filter(Boolean).join(", ");
  return {
    ...form, artist_name: artistName, language: form.tracks[0]?.title_language || "Indonesian",
    explicit: form.tracks.some((track) => track.explicit), primary_artists: primary,
    featured_artists: featured,
    tracks: form.tracks.map(({ client_id, audio_sample_rate, ...track }, index) => ({
      ...track, track_number: index + 1, artist_name: artistName,
      featured_artists: (track.featured_artists || []).map(serializeArtist),
      featuring_artist_id: track.featured_artists?.length === 1 ? track.featured_artists[0].artist_id : null,
      featuring_artist_name: track.featured_artists?.map((artist) => artist.name).join(", ") || null,
      lyrics: track.vocal_type === "instrumental" ? "Instrumental" : track.lyrics,
      lyric_language: track.vocal_type === "instrumental" ? "Instrumental" : track.lyric_language,
    })),
  };
};

export const validateStep = (step, form) => {
  if (step === 1 && [form.release_title, form.genre, form.subgenre, form.copyright_line, form.p_line].some((value) => !String(value || "").trim())) return "Lengkapi seluruh informasi rilisan yang wajib.";
  if (step === 1 && form.artist_web_url?.trim()) { try { const url = new URL(form.artist_web_url.trim()); if (!["http:", "https:"].includes(url.protocol)) return "URL web artist atau YouTube tidak valid"; } catch { return "URL web artist atau YouTube tidak valid"; } }
  if (step === 1 && form.release_date < todayPlus(7)) return "Tanggal rilis digital minimal 7 hari setelah submit.";
  if (step === 2 && (!form.primary_artists.length || form.primary_artists.some((item) => !item.name.trim()))) return "Minimal satu nama artist utama wajib diisi.";
  if (step === 2 && [...form.primary_artists, ...form.featured_artists].some((item) => item.name.trim() && !socialLinksAreValid(item.social_links))) return "Setiap artis wajib memiliki minimal satu tautan media sosial yang valid.";
  if (step === 3 && form.release_type === "single" && form.tracks.length !== 1) return "SINGLE harus memiliki tepat satu track.";
  if (step === 3) {
    if (form.tracks.some((track) => (track.featured_artists || []).some((artist) => !artist.name.trim() || !socialLinksAreValid(artist.social_links)))) return "Lengkapi nama dan tautan sosial setiap artis featuring pada track.";
    const invalid = form.tracks.find((track) => !track.track_title.trim() || !track.lyricist.trim() || !track.composer.trim() || !track.title_language.trim() || (track.vocal_type === "vocal" && (!track.lyric_language.trim() || !track.lyrics.trim())));
    if (invalid) return "Lengkapi judul, writer, komposer, bahasa, dan lirik pada setiap track.";
  }
  return "";
};