import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { UPLOAD_RELEASE } from "@/constants/testIds";
import { Trash2, Plus, UploadCloud, Music, ImageIcon } from "lucide-react";

const RELEASE_TYPES = ["single", "ep", "album", "compilation"];
const newTrack = (artistName = "") => ({
  client_id: crypto.randomUUID(), track_title: "", artist_name: artistName,
  composer: "", lyricist: "", producer: "", explicit: false, track_number: 1,
});

function todayPlus(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

export default function UploadRelease() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1: metadata, 2: tracks, 3: assets+submit
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const [release, setRelease] = useState(null); // after create-draft
  const [form, setForm] = useState({
    release_title: "",
    release_type: "single",
    artist_name: "",
    release_date: todayPlus(10),
    genre: "Pop",
    subgenre: "",
    language: "Indonesian",
    explicit: false,
    copyright_line: "",
    p_line: "",
    platforms: ["Spotify", "Apple Music", "YouTube Music", "TikTok"],
    notes: "",
    tracks: [newTrack()],
  });
  const [declaration, setDeclaration] = useState(false);
  const [coverFile, setCoverFile] = useState(null);
  const [coverPreview, setCoverPreview] = useState(null);
  const [trackFiles, setTrackFiles] = useState({}); // {trackId: File}

  const onCh = (k) => (e) => setForm({ ...form, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  const onTrackCh = (i, k) => (e) => {
    const next = [...form.tracks];
    next[i] = { ...next[i], [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value };
    setForm({ ...form, tracks: next });
  };

  const addTrack = () => setForm({
    ...form,
    tracks: [...form.tracks, { ...newTrack(form.artist_name), track_number: form.tracks.length + 1 }]
  });

  const removeTrack = (i) => setForm({ ...form, tracks: form.tracks.filter((_, idx) => idx !== i) });

  const saveDraft = async () => {
    setErr("");
    if (!form.release_title || !form.artist_name) { setErr("Judul rilisan dan nama artis wajib"); return; }
    if (!form.tracks.length || form.tracks.some(t => !t.track_title)) { setErr("Semua track wajib punya judul"); return; }
    setSaving(true);
    try {
      const tracks = form.tracks.map(({ client_id, ...track }, i) => ({ ...track, track_number: i + 1, artist_name: track.artist_name || form.artist_name }));
      const payload = { ...form, tracks };
      let r;
      if (release?.id) {
        r = await api.patch(`/releases/${release.id}`, payload);
      } else {
        r = await api.post("/releases/draft", payload);
      }
      setRelease(r.data);
      // also need to refetch tracks for IDs
      const detail = await api.get(`/releases/${r.data.id}`);
      setRelease(detail.data);
      setStep(3);
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail) || "Gagal menyimpan draft");
    } finally { setSaving(false); }
  };

  const uploadCover = async (file) => {
    if (!release?.id) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data } = await api.post(`/releases/${release.id}/upload-cover`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      setRelease({ ...release, cover_url: data.cover_url });
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail) || "Upload cover gagal");
    }
  };

  const uploadAudio = async (trackId, file) => {
    if (!release?.id) return;
    const fd = new FormData();
    fd.append("track_id", trackId);
    fd.append("file", file);
    try {
      const { data } = await api.post(`/releases/${release.id}/upload-audio`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      setRelease((r) => ({ ...r, tracks: r.tracks.map((t) => t.id === trackId ? { ...t, audio_url: data.audio_url } : t) }));
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail) || "Upload audio gagal");
    }
  };

  const onCoverChange = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    setCoverFile(f);
    setCoverPreview(URL.createObjectURL(f));
    uploadCover(f);
  };

  const onAudioChange = (trackId) => (e) => {
    const f = e.target.files[0];
    if (!f) return;
    setTrackFiles((p) => ({ ...p, [trackId]: f }));
    uploadAudio(trackId, f);
  };

  const submitRelease = async () => {
    setErr("");
    if (!declaration) { setErr("Wajib menyetujui deklarasi hak cipta"); return; }
    setSaving(true);
    try {
      const { data } = await api.post(`/releases/${release.id}/submit`, { contract_declaration_checked: true });
      // success — navigate to detail
      navigate(`/label/releases/${data.id}`);
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail) || "Submit gagal");
    } finally { setSaving(false); }
  };

  return (
    <div className="space-y-5 max-w-4xl">
      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Submit Rilisan</div>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">Upload Rilisan Baru</h1>
        <p className="text-sm text-zinc-400 mt-2">Audio WAV, cover square 3000×3000, tanggal rilis minimal 7 hari setelah hari ini.</p>
      </div>

      <Stepper step={step} />

      {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm border border-red-100">{err}</div>}

      {step === 1 && (
        <div className="rm-card p-6 space-y-5">
          <h3 className="font-display font-bold text-xl tracking-tight">1. Metadata Rilisan</h3>
          <div className="grid md:grid-cols-2 gap-4">
            <Field label="Judul Rilisan">
              <input data-testid={UPLOAD_RELEASE.releaseTitle} className="rm-input" value={form.release_title} onChange={onCh("release_title")} />
            </Field>
            <Field label="Tipe Rilisan">
              <select data-testid={UPLOAD_RELEASE.releaseType} className="rm-input capitalize" value={form.release_type} onChange={onCh("release_type")}>
                {RELEASE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </Field>
            <Field label="Nama Artist Utama">
              <input data-testid={UPLOAD_RELEASE.artistName} className="rm-input" value={form.artist_name} onChange={onCh("artist_name")} />
            </Field>
            <Field label="Tanggal Rilis (min. 7 hari)">
              <input data-testid={UPLOAD_RELEASE.releaseDate} type="date" className="rm-input" value={form.release_date} onChange={onCh("release_date")} min={todayPlus(7)} />
            </Field>
            <Field label="Genre">
              <input data-testid={UPLOAD_RELEASE.genre} className="rm-input" value={form.genre} onChange={onCh("genre")} />
            </Field>
            <Field label="Subgenre (opsional)">
              <input className="rm-input" value={form.subgenre} onChange={onCh("subgenre")} />
            </Field>
            <Field label="Bahasa">
              <input data-testid={UPLOAD_RELEASE.language} className="rm-input" value={form.language} onChange={onCh("language")} />
            </Field>
            <Field label="Explicit Content">
              <label className="flex items-center gap-2 mt-2"><input type="checkbox" data-testid={UPLOAD_RELEASE.explicit} checked={form.explicit} onChange={onCh("explicit")} /> Ya, mengandung konten eksplisit</label>
            </Field>
            <Field label="© Copyright Line">
              <input data-testid={UPLOAD_RELEASE.copyrightLine} className="rm-input" placeholder={`${new Date().getFullYear()} ${form.artist_name || "Label"}`} value={form.copyright_line} onChange={onCh("copyright_line")} />
            </Field>
            <Field label="℗ Phonographic Line">
              <input data-testid={UPLOAD_RELEASE.pLine} className="rm-input" placeholder={`${new Date().getFullYear()} ${form.artist_name || "Label"}`} value={form.p_line} onChange={onCh("p_line")} />
            </Field>
          </div>
          <div className="flex justify-end gap-2 pt-3">
            <button className="rm-btn-primary" onClick={() => setStep(2)} data-testid="upload-release-next-to-tracks">Lanjut: Tracks →</button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="rm-card p-6 space-y-5">
          <div className="flex justify-between items-center">
            <h3 className="font-display font-bold text-xl tracking-tight">2. Tracklist</h3>
            <button className="rm-btn-ghost flex items-center gap-1.5 text-sm" onClick={addTrack} data-testid={UPLOAD_RELEASE.addTrackButton}><Plus className="w-4 h-4" /> Tambah Track</button>
          </div>
          <div className="space-y-4">
            {form.tracks.map((t, i) => (
              <div key={t.client_id} className="border border-white/5 rounded-2xl p-4 bg-white/[0.02]">
                <div className="flex justify-between items-center mb-3">
                  <div className="text-sm font-bold text-zinc-200">Track #{i + 1}</div>
                  {form.tracks.length > 1 && <button className="text-red-500 hover:text-red-700" onClick={() => removeTrack(i)} data-testid={`upload-release-remove-track-${i}`}><Trash2 className="w-4 h-4" /></button>}
                </div>
                <div className="grid md:grid-cols-2 gap-3">
                  <Field label="Judul Track"><input data-testid={`${UPLOAD_RELEASE.trackTitle}-${i}`} className="rm-input" value={t.track_title} onChange={onTrackCh(i, "track_title")} /></Field>
                  <Field label="Artist Track"><input data-testid={`${UPLOAD_RELEASE.trackArtist}-${i}`} className="rm-input" value={t.artist_name} onChange={onTrackCh(i, "artist_name")} placeholder={form.artist_name} /></Field>
                  <Field label="Composer / Pencipta"><input data-testid={`${UPLOAD_RELEASE.trackComposer}-${i}`} className="rm-input" value={t.composer} onChange={onTrackCh(i, "composer")} /></Field>
                  <Field label="Lyricist / Penulis Lirik"><input className="rm-input" value={t.lyricist} onChange={onTrackCh(i, "lyricist")} /></Field>
                  <Field label="Producer"><input className="rm-input" value={t.producer} onChange={onTrackCh(i, "producer")} /></Field>
                  <Field label="Explicit"><label className="flex items-center gap-2 mt-2"><input type="checkbox" checked={t.explicit} onChange={onTrackCh(i, "explicit")} /> Eksplisit</label></Field>
                </div>
              </div>
            ))}
          </div>
          <div className="flex justify-between gap-2 pt-3">
            <button className="rm-btn-ghost" onClick={() => setStep(1)}>← Kembali</button>
            <button className="rm-btn-primary" onClick={saveDraft} disabled={saving} data-testid={UPLOAD_RELEASE.saveDraftButton}>
              {saving ? "Menyimpan…" : "Lanjut: Upload Audio & Cover →"}
            </button>
          </div>
        </div>
      )}

      {step === 3 && release && (
        <div className="space-y-5">
          <div className="rm-card p-6 space-y-5">
            <h3 className="font-display font-bold text-xl tracking-tight">3. Cover & Audio</h3>

            {/* Cover */}
            <div>
              <label className="rm-label flex items-center gap-2"><ImageIcon className="w-4 h-4" /> Cover Art (square 3000×3000, JPG/PNG)</label>
              <label htmlFor="cover-up" className={`flex items-center justify-center border-2 border-dashed rounded-2xl p-6 cursor-pointer transition ${release.cover_url ? "border-emerald-300 bg-emerald-50/40" : "border-white/10 bg-white/[0.02] hover:bg-white/5"}`}>
                {release.cover_url ? (
                  <div className="flex items-center gap-4">
                    <img src={`${process.env.REACT_APP_BACKEND_URL}${release.cover_url}`} alt="cover" className="w-24 h-24 rounded-xl object-cover" />
                    <div>
                      <div className="font-semibold text-sm text-emerald-300">Cover terupload</div>
                      <div className="text-xs text-zinc-500">Klik untuk ganti</div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center text-zinc-500">
                    <UploadCloud className="w-7 h-7 mx-auto mb-2" />
                    <div className="text-sm font-semibold">Klik untuk upload cover</div>
                    <div className="text-xs">JPG / PNG, minimal 3000×3000 square</div>
                  </div>
                )}
                <input id="cover-up" type="file" accept="image/*" hidden onChange={onCoverChange} data-testid={UPLOAD_RELEASE.coverUpload} />
              </label>
            </div>

            {/* Audio per track */}
            <div>
              <label className="rm-label flex items-center gap-2"><Music className="w-4 h-4" /> Audio per Track (WAV)</label>
              <div className="space-y-2">
                {release.tracks.map((t) => (
                  <div key={t.id} className="flex items-center justify-between gap-3 border border-white/5 rounded-xl p-3">
                    <div className="min-w-0">
                      <div className="font-semibold text-sm">#{t.track_number} — {t.track_title}</div>
                      <div className="text-xs text-zinc-500">{t.artist_name}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      {t.audio_url ? (
                        <span className="text-xs font-semibold text-emerald-300">✓ Terupload</span>
                      ) : (
                        <span className="text-xs text-zinc-600">Belum ada audio</span>
                      )}
                      <label className="rm-btn-ghost cursor-pointer text-xs" data-testid={`${UPLOAD_RELEASE.audioUpload}-${t.id}`}>
                        Upload WAV
                        <input type="file" accept=".wav,audio/wav" hidden onChange={onAudioChange(t.id)} />
                      </label>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Declaration & Submit */}
          <div className="rm-card p-6 space-y-4">
            <h3 className="font-display font-bold text-xl tracking-tight">Deklarasi Hak Cipta</h3>
            <label className="flex items-start gap-3 text-sm text-zinc-200 leading-relaxed cursor-pointer">
              <input type="checkbox" checked={declaration} onChange={(e) => setDeclaration(e.target.checked)} className="mt-1" data-testid={UPLOAD_RELEASE.declarationCheckbox} />
              <span>
                Saya menyatakan memiliki <b>hak distribusi atas audio dan cover</b>, metadata yang saya isi benar,
                tidak ada pelanggaran hak cipta, dan saya bertanggung jawab atas sengketa yang muncul dari rilisan ini.
              </span>
            </label>
            <div className="flex justify-between gap-2 pt-2">
              <button className="rm-btn-ghost" onClick={() => setStep(2)}>← Edit Metadata</button>
              <button className="rm-btn-primary" disabled={saving || !declaration} onClick={submitRelease} data-testid={UPLOAD_RELEASE.submitButton}>
                {saving ? "Memproses…" : "Submit Rilisan"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Stepper({ step }) {
  const items = ["Metadata", "Tracks", "Cover & Audio"];
  return (
    <div className="flex items-center gap-2">
      {items.map((label, i) => {
        const idx = i + 1;
        const active = step === idx;
        const done = step > idx;
        return (
          <React.Fragment key={label}>
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold ${active ? "bg-[#FF1F8E] text-white" : done ? "bg-emerald-500/15 text-emerald-300" : "bg-white/[0.06] text-zinc-500"}`}>
              <span className="w-5 h-5 rounded-full grid place-items-center bg-white/30">{done ? "✓" : idx}</span>
              {label}
            </div>
            {i < items.length - 1 && <div className="w-6 h-px bg-slate-300" />}
          </React.Fragment>
        );
      })}
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <label className="rm-label">{label}</label>
      {children}
    </div>
  );
}
