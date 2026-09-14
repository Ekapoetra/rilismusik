import React, { useState } from "react";
import { ArrowLeft, Plus, Save, Trash2, X } from "lucide-react";
import { newTrack } from "./releaseFormState";
import { ArtistList } from "./ArtistCreditsStep";

const Field = ({ label, children, span = "" }) => <label className={span}><span className="rm-label">{label}</span>{children}</label>;

function MultiNameInput({ value, onChange, testId, placeholder = "Nama lengkap" }) {
  const [rows, setRows] = useState(() => { const parts = (value || "").split(",").map((s) => s.trim()).filter(Boolean); return parts.length ? parts : [""]; });
  const propagate = (next) => { setRows(next); onChange(next.map((s) => s.trim()).filter(Boolean).join(", ")); };
  const setAt = (index, val) => propagate(rows.map((row, i) => (i === index ? val : row)));
  const addRow = () => setRows((cur) => [...cur, ""]);
  const removeRow = (index) => propagate(rows.filter((_, i) => i !== index).length ? rows.filter((_, i) => i !== index) : [""]);
  return <div className="space-y-2" data-testid={`${testId}-multi`}>
    {rows.map((row, index) => <div className="flex items-center gap-2" key={index}>
      <input className="rm-input" value={row} placeholder={placeholder} onChange={(event) => setAt(index, event.target.value)} data-testid={`${testId}-${index}`} />
      {rows.length > 1 && <button type="button" title="Hapus nama" className="shrink-0 rounded-md p-2 text-red-300 transition-colors hover:bg-red-500/10" onClick={() => removeRow(index)} data-testid={`${testId}-remove-${index}`}><X className="h-4 w-4" /></button>}
    </div>)}
    <button type="button" className="inline-flex items-center gap-1.5 text-xs font-semibold text-violet-300 transition-colors hover:text-violet-200" onClick={addRow} data-testid={`${testId}-add`}><Plus className="h-3.5 w-3.5" /> Tambah nama</button>
  </div>;
}

function TrackEditor({ track, index, canRemove, update, remove, savedArtists }) {
  const change = (field) => (event) => update(field, event.target.type === "checkbox" ? event.target.checked : event.target.value);
  const instrumental = track.vocal_type === "instrumental";
  return <article className="border-t border-white/10 py-7 first:border-t-0" data-testid={`upload-release-track-${index}`}><div className="mb-5 flex items-center justify-between"><div><div className="text-xs font-bold uppercase text-zinc-500">Track {index + 1}</div><h3 className="font-display text-xl font-bold">{track.track_title || "Track tanpa judul"}</h3></div>{canRemove && <button type="button" title="Hapus track" className="rounded-md p-2 text-red-300 transition-colors hover:bg-red-500/10" onClick={remove} data-testid={`upload-release-remove-track-${index}`}><Trash2 className="h-4 w-4" /></button>}</div><div className="grid gap-4 md:grid-cols-2">
    <Field label="Judul Track"><input className="rm-input" value={track.track_title} onChange={change("track_title")} data-testid={`upload-release-track-title-${index}`} /></Field>
    <Field label="ISRC (opsional)"><input className="rm-input font-mono uppercase" value={track.isrc || ""} onChange={change("isrc")} data-testid={`upload-release-track-isrc-${index}`} /></Field>
    <Field label="Audio"><div className="grid grid-cols-2 gap-2"><button type="button" onClick={() => update("vocal_type", "vocal")} className={`rounded-md border px-3 py-2 text-sm font-bold ${!instrumental ? "border-white bg-white text-black" : "border-white/10 text-zinc-400"}`} data-testid={`upload-release-track-vocal-${index}`}>Ada Vokal</button><button type="button" onClick={() => update("vocal_type", "instrumental")} className={`rounded-md border px-3 py-2 text-sm font-bold ${instrumental ? "border-white bg-white text-black" : "border-white/10 text-zinc-400"}`} data-testid={`upload-release-track-instrumental-${index}`}>Instrumental</button></div></Field>
    <Field label="Explicit Content"><label className="rm-input flex items-center gap-3"><input type="checkbox" checked={track.explicit} onChange={change("explicit")} data-testid={`upload-release-track-explicit-${index}`} /><span>{track.explicit ? "YA" : "TIDAK"}</span></label></Field>
    <Field label="Nama Pencipta / Writer — nama lengkap KTP (bisa lebih dari satu)"><MultiNameInput value={track.lyricist} onChange={(val) => update("lyricist", val)} testId={`upload-release-track-writer-${index}`} /></Field>
    <Field label="Nama Komposer — nama lengkap KTP (bisa lebih dari satu)"><MultiNameInput value={track.composer} onChange={(val) => update("composer", val)} testId={`upload-release-track-composer-${index}`} /></Field>
    <Field label="Arranger (opsional, bisa lebih dari satu)"><MultiNameInput value={track.arranger || ""} onChange={(val) => update("arranger", val)} testId={`upload-release-track-arranger-${index}`} /></Field>
    <Field label="Nama Produser (opsional, bisa lebih dari satu)"><MultiNameInput value={track.producer || ""} onChange={(val) => update("producer", val)} testId={`upload-release-track-producer-${index}`} /></Field>
    <Field label="Detik Mulai Preview (Khusus iTunes, Tiktok)"><input type="number" min="0" max="3600" className="rm-input" value={track.preview_start_seconds} onChange={change("preview_start_seconds")} data-testid={`upload-release-track-preview-${index}`} /></Field>
    <Field label="Bahasa pada Judul"><input className="rm-input" value={track.title_language} onChange={change("title_language")} data-testid={`upload-release-track-title-language-${index}`} /></Field>
    <Field label="Bahasa pada Lirik"><input disabled={instrumental} className="rm-input disabled:opacity-50" value={instrumental ? "Instrumental" : track.lyric_language} onChange={change("lyric_language")} data-testid={`upload-release-track-lyric-language-${index}`} /></Field>
    <Field label={instrumental ? "Lirik — otomatis untuk instrumental" : "Lirik Lengkap — wajib"} span="md:col-span-2"><textarea disabled={instrumental} className="rm-input min-h-52 resize-y disabled:opacity-60" value={instrumental ? "Instrumental" : track.lyrics} onChange={change("lyrics")} data-testid={`upload-release-track-lyrics-${index}`} /></Field>
  </div><div className="mt-6"><ArtistList title="Featuring pada Track (opsional)" description="" values={track.featured_artists || []} setValues={(artists) => update("featured_artists", artists)} savedArtists={savedArtists} prefix={`upload-release-track-featured-${index}`} /></div></article>;
}

export const TracksStep = ({ form, updateForm, savedArtists = [], saving, onBack, onSave }) => {
  const updateTrack = (index, field, value) => updateForm({ tracks: form.tracks.map((track, itemIndex) => itemIndex === index ? { ...track, [field]: value } : track) });
  const add = () => updateForm({ tracks: [...form.tracks, newTrack()] });
  return <section className="space-y-6" data-testid="upload-release-tracks-step"><div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="font-display text-2xl font-bold">Track dan kredit</h2><p className="mt-1 text-sm text-zinc-400">Semua kolom wajib diisi kecuali yang ditandai (opsional). Untuk SINGLE gunakan tepat satu track.</p></div>{form.release_type !== "single" && <button type="button" className="rm-btn-ghost inline-flex items-center gap-2" onClick={add} data-testid="upload-release-add-track-button"><Plus className="h-4 w-4" /> Tambah Track</button>}</div><div>{form.tracks.map((track, index) => <TrackEditor key={track.client_id} track={track} index={index} savedArtists={savedArtists} canRemove={form.tracks.length > 1} update={(field, value) => updateTrack(index, field, value)} remove={() => updateForm({ tracks: form.tracks.filter((_, itemIndex) => itemIndex !== index) })} />)}</div><div className="flex flex-wrap justify-between gap-3 border-t border-white/10 pt-5"><button type="button" className="rm-btn-ghost inline-flex items-center gap-2" onClick={onBack} data-testid="upload-release-tracks-back-button"><ArrowLeft className="h-4 w-4" /> Kembali</button><button type="button" className="rm-btn-primary inline-flex items-center gap-2" disabled={saving} onClick={onSave} data-testid="upload-release-save-draft-button"><Save className="h-4 w-4" /> {saving ? "Menyimpan…" : "Simpan & Lanjut ke File"}</button></div></section>;
};