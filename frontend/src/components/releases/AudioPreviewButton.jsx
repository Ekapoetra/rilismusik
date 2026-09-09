import React from "react";
import { Play, Pause, Download } from "lucide-react";
import { useAudioPreview, trackDownloadUrl } from "@/contexts/AudioPreviewContext";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

export const AudioPreviewButton = ({ release, track, prefix = "release-track-audio", download = true }) => {
  const { openTrack, track: active, playing } = useAudioPreview();
  const { t } = useAppPreferences();
  const isPlaying = active?.id === track.id && playing;
  return <div className="flex flex-wrap items-center gap-3"><button type="button" onClick={() => openTrack(release, track)} className="inline-flex items-center gap-2 rounded-md border border-pink-500/30 bg-pink-500/10 px-3 py-2 text-xs font-bold text-pink-400 transition-colors hover:bg-pink-500/20" data-testid={`${prefix}-${track.id}`} aria-label={`${t(isPlaying ? "Jeda" : "Putar")} ${track.track_title}`}>{isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}{t("Preview Audio")}</button>{download && <a href={trackDownloadUrl(track)} className="inline-flex items-center gap-1.5 whitespace-nowrap text-xs font-semibold text-sky-300" data-testid={`release-track-audio-download-${track.id}`} download={track.audio_filename}><Download className="h-3.5 w-3.5" />{t("Unduh WAV")}</a>}</div>;
};