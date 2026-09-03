export const todayPlus = (days) => {
  const value = new Date(); value.setDate(value.getDate() + days);
  return value.toISOString().slice(0, 10);
};

export const newArtist = () => ({ client_id: crypto.randomUUID(), name: "", spotify_url: "" });
export const newTrack = () => ({
  client_id: crypto.randomUUID(), id: null, track_title: "", isrc: "",
  vocal_type: "vocal", lyricist: "", composer: "", arranger: "", producer: "",
  explicit: false, preview_start_seconds: 0, title_language: "Indonesian",
  lyric_language: "Indonesian", lyrics: "", audio_url: null, audio_sample_rate: null,
});

export const defaultReleaseForm = () => ({
  release_title: "", release_type: "single", release_date: todayPlus(7),
  genre: "", subgenre: "", copyright_line: "", p_line: "",
  year: new Date().getFullYear(), artist_web_url: "",
  primary_artists: [newArtist()], featured_artists: [], tracks: [newTrack()],
  platforms: ["Spotify", "Apple Music", "YouTube Music", "TikTok"], notes: "",
});

const withClientId = (item) => ({ ...item, client_id: item.client_id || crypto.randomUUID() });
export const mapReleaseToForm = (release) => ({
  ...defaultReleaseForm(), ...release,
  primary_artists: (release.primary_artists?.length ? release.primary_artists : [{ name: release.artist_name || "", spotify_url: "" }]).map(withClientId),
  featured_artists: (release.featured_artists || []).map(withClientId),
  tracks: (release.tracks?.length ? release.tracks : [newTrack()]).map((track) => withClientId({ ...newTrack(), ...track })),
});

export const serializeReleaseForm = (form) => {
  const primary = form.primary_artists.map(({ client_id, ...item }) => item);
  const featured = form.featured_artists.map(({ client_id, ...item }) => item).filter((item) => item.name.trim());
  const artistName = primary.map((item) => item.name.trim()).filter(Boolean).join(", ");
  return {
    ...form, artist_name: artistName, language: form.tracks[0]?.title_language || "Indonesian",
    explicit: form.tracks.some((track) => track.explicit), primary_artists: primary,
    featured_artists: featured,
    tracks: form.tracks.map(({ client_id, audio_sample_rate, ...track }, index) => ({
      ...track, track_number: index + 1, artist_name: artistName,
      lyrics: track.vocal_type === "instrumental" ? "Instrumental" : track.lyrics,
      lyric_language: track.vocal_type === "instrumental" ? "Instrumental" : track.lyric_language,
    })),
  };
};

export const validateStep = (step, form) => {
  if (step === 1 && [form.release_title, form.genre, form.subgenre, form.copyright_line, form.p_line, form.artist_web_url].some((value) => !String(value || "").trim())) return "Lengkapi seluruh informasi rilisan dan URL web/channel artist.";
  if (step === 1 && form.release_date < todayPlus(7)) return "Tanggal rilis digital minimal 7 hari setelah submit.";
  if (step === 2 && (!form.primary_artists.length || form.primary_artists.some((item) => !item.name.trim()))) return "Minimal satu nama artist utama wajib diisi.";
  if (step === 3 && form.release_type === "single" && form.tracks.length !== 1) return "SINGLE harus memiliki tepat satu track.";
  if (step === 3) {
    const invalid = form.tracks.find((track) => !track.track_title.trim() || !track.lyricist.trim() || !track.composer.trim() || !track.title_language.trim() || (track.vocal_type === "vocal" && (!track.lyric_language.trim() || !track.lyrics.trim())));
    if (invalid) return "Lengkapi judul, writer, komposer, bahasa, dan lirik pada setiap track.";
  }
  return "";
};