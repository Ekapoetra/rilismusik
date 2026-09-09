import React, { createContext, useCallback, useContext, useEffect, useLayoutEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { createPortal } from "react-dom";
import { Play, Pause, SkipBack, SkipForward, Download, Volume2, VolumeX, X, Music2 } from "lucide-react";
import { fileUrl } from "@/api/client";
import { useAppPreferences } from "./AppPreferencesContext";
import "@/styles/audio-player.css";

const Context = createContext(null);
const timeLabel = (seconds) => Number.isFinite(seconds) ? `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}` : "0:00";
export const trackDownloadUrl = (track) => {
  const url = new URL(fileUrl(track.audio_url), window.location.origin);
  url.searchParams.set("download", track.audio_filename || `${track.track_title || "audio"}.wav`);
  return url.toString();
};

export const AudioPreviewProvider = ({ children }) => {
  const { t } = useAppPreferences();
  const { pathname } = useLocation();
  const audio = useRef(null); const dock = useRef(null);
  const [selection, setSelection] = useState(null);
  const [playing, setPlaying] = useState(false); const [time, setTime] = useState(0); const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0.8); const [error, setError] = useState("");
  const track = selection?.tracks[selection.index];
  const hasTrack = Boolean(track);
  const close = useCallback(() => { audio.current?.pause(); setSelection(null); setPlaying(false); setError(""); }, []);
  useEffect(() => { if (!/^\/(admin|label)(\/|$)/.test(pathname)) close(); }, [pathname, close]);
  const play = async () => { if (!audio.current) return; try { await audio.current.play(); setError(""); } catch { setError(t("Klik Putar untuk memulai audio.")); } };
  const toggle = () => audio.current?.paused ? play() : audio.current?.pause();
  const openTrack = (release, selectedTrack) => {
    if (track?.id === selectedTrack.id && track?.audio_url === selectedTrack.audio_url) { toggle(); return; }
    const available = (release.tracks?.length ? release.tracks : [selectedTrack]).filter((item) => item.audio_url);
    let index = available.findIndex((item) => item.id === selectedTrack.id);
    if (index < 0) { available.push(selectedTrack); index = available.length - 1; }
    setSelection({ release, tracks: available, index });
  };
  useEffect(() => {
    if (!track) return;
    setTime(0); setDuration(0); setError(""); setPlaying(false);
    if (audio.current) { audio.current.volume = volume; play(); }
    // Playback is keyed by the media source, not UI language/theme changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [track?.id, track?.audio_url]);
  useEffect(() => { if (audio.current) audio.current.volume = volume; }, [volume]);
  useEffect(() => { if (!hasTrack) return; const key = (event) => { if (event.key === "Escape") close(); }; window.addEventListener("keydown", key); return () => window.removeEventListener("keydown", key); }, [hasTrack, close]);
  useLayoutEffect(() => {
    if (!hasTrack || !dock.current) { document.documentElement.style.removeProperty("--audio-player-height"); return; }
    const update = () => document.documentElement.style.setProperty("--audio-player-height", `${dock.current?.getBoundingClientRect().height || 0}px`);
    const observer = new ResizeObserver(update); observer.observe(dock.current); update();
    return () => { observer.disconnect(); document.documentElement.style.removeProperty("--audio-player-height"); };
  }, [hasTrack]);
  const changeTrack = (offset) => setSelection((current) => ({ ...current, index: current.index + offset }));
  return <Context.Provider value={{ openTrack, close, track, playing }}>{children}{track && createPortal(
    <section ref={dock} className="audio-preview-dock" role="dialog" aria-label={t("Preview Audio")} aria-modal="false" data-testid="audio-preview-player">
      <audio ref={audio} src={fileUrl(track.audio_url)} preload="metadata" onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onTimeUpdate={() => setTime(audio.current?.currentTime || 0)} onLoadedMetadata={() => setDuration(Number.isFinite(audio.current?.duration) ? audio.current.duration : 0)} onDurationChange={() => setDuration(Number.isFinite(audio.current?.duration) ? audio.current.duration : 0)} onEnded={() => setPlaying(false)} onError={() => { setError(t("Audio tidak dapat dimuat. File tetap dapat diunduh.")); setPlaying(false); }} data-testid="audio-preview-media" />
      <div className="audio-preview-inner">
        <div className="audio-preview-track"><div className="audio-preview-art">{selection.release.cover_url ? <img src={fileUrl(selection.release.cover_url)} alt="" /> : <Music2 className="h-7 w-7 text-[var(--ui-muted)]" />}</div><div className="min-w-0" translate="no"><div className="truncate text-sm font-bold sm:text-base" data-testid="audio-preview-title">{track.track_title}</div><div className="mt-1 truncate text-xs text-[var(--ui-muted)]" data-testid="audio-preview-artist">{selection.release.artist_name}</div><div className="mt-1 text-[10px] font-mono text-[var(--ui-muted)]" data-testid="audio-preview-format">WAV{track.audio_sample_rate ? ` · ${track.audio_sample_rate / 1000} kHz` : ""}</div></div><button type="button" onClick={close} className="ui-icon-button ml-auto md:hidden" aria-label={t("Tutup")} data-testid="audio-preview-close-mobile"><X className="h-4 w-4" /></button></div>
        <div className="audio-preview-transport"><div className="flex items-center justify-center gap-4"><button type="button" disabled={selection.index === 0} onClick={() => changeTrack(-1)} className="audio-plain-button" aria-label={t("Sebelumnya")} data-testid="audio-preview-previous"><SkipBack className="h-4 w-4" /></button><button type="button" onClick={toggle} className="audio-play-button" aria-label={t(playing ? "Jeda" : "Putar")} data-testid="audio-preview-play-pause">{playing ? <Pause className="h-5 w-5 fill-current" /> : <Play className="ml-0.5 h-5 w-5 fill-current" />}</button><button type="button" disabled={selection.index >= selection.tracks.length - 1} onClick={() => changeTrack(1)} className="audio-plain-button" aria-label={t("Berikutnya")} data-testid="audio-preview-next"><SkipForward className="h-4 w-4" /></button></div><div className="mt-3 flex items-center gap-3"><span className="w-9 text-right font-mono text-[11px] text-[var(--ui-muted)]" data-testid="audio-preview-elapsed">{timeLabel(time)}</span><input type="range" min="0" max={duration || 1} step="0.1" value={Math.min(time, duration || 1)} disabled={!duration} onChange={(event) => { const next = Number(event.target.value); if (audio.current && duration) { audio.current.currentTime = next; setTime(next); } }} aria-label={t("Posisi pemutaran")} aria-valuetext={`${timeLabel(time)} / ${timeLabel(duration)}`} style={{ "--play-progress": `${duration ? time / duration * 100 : 0}%` }} className="audio-progress" data-testid="audio-preview-seek" /><span className="w-9 font-mono text-[11px] text-[var(--ui-muted)]" data-testid="audio-preview-duration">{timeLabel(duration)}</span></div>{error && <p className="mt-2 text-center text-xs text-red-400" role="alert" data-testid="audio-preview-error">{error}</p>}</div>
        <div className="audio-preview-actions"><button type="button" className="audio-plain-button" onClick={() => setVolume((current) => current ? 0 : 0.8)} aria-label={t(volume ? "Bisukan" : "Aktifkan suara")} data-testid="audio-preview-mute">{volume ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}</button><input type="range" min="0" max="1" step="0.05" value={volume} onChange={(event) => setVolume(Number(event.target.value))} className="w-20 accent-pink-600" aria-label={t("Volume")} data-testid="audio-preview-volume" /><a href={trackDownloadUrl(track)} className="audio-download-button" data-testid="audio-preview-download" download={track.audio_filename || `${track.track_title}.wav`}><Download className="h-4 w-4" /><span>{t("Unduh WAV")}</span></a><button type="button" onClick={close} className="ui-icon-button hidden md:inline-flex" aria-label={t("Tutup")} data-testid="audio-preview-close"><X className="h-4 w-4" /></button></div>
      </div>
    </section>, document.body)}</Context.Provider>;
};
export const useAudioPreview = () => { const value = useContext(Context); if (!value) throw new Error("Audio preview provider missing"); return value; };