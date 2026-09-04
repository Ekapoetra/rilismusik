export const SOCIAL_PLATFORM_OPTIONS = [
  { value: "instagram", label: "Instagram", placeholder: "https://instagram.com/namaartis" },
  { value: "tiktok", label: "TikTok", placeholder: "https://tiktok.com/@namaartis" },
  { value: "facebook", label: "Facebook", placeholder: "https://facebook.com/namaartis" },
  { value: "youtube", label: "YouTube", placeholder: "https://youtube.com/@namaartis" },
  { value: "x", label: "X / Twitter", placeholder: "https://x.com/namaartis" },
  { value: "spotify", label: "Spotify", placeholder: "https://open.spotify.com/artist/…" },
  { value: "website", label: "Situs Web", placeholder: "https://namaartis.com" },
  { value: "other", label: "Lainnya", placeholder: "https://…" },
];

export const socialPlatformLabel = (value) => SOCIAL_PLATFORM_OPTIONS.find((item) => item.value === value)?.label || value;
export const newSocialLink = () => ({ client_id: crypto.randomUUID(), platform: "instagram", url: "" });

export const socialLinksAreValid = (links) => (links || []).length > 0 && links.every((item) => {
  try { return Boolean(item.platform) && ["http:", "https:"].includes(new URL(item.url).protocol); }
  catch { return false; }
});