import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError, fileUrl } from "@/api/client";
import TicketStatusBadge, { TICKET_CATEGORY_LABELS } from "@/components/shared/TicketStatusBadge";
import { SUPPORT } from "@/constants/testIds";
import { LifeBuoy, Plus, X, Paperclip, AlertTriangle, CheckCircle2 } from "lucide-react";

const CATEGORY_OPTIONS = Object.entries(TICKET_CATEGORY_LABELS).map(([value, label]) => ({ value, label }));

function initialForm() {
  return {
    category: "takedown",
    release_id: "",
    subject: "",
    description: "",
    reason: "",
    new_audio_track_id: "",
    new_audio_url: "",
    new_audio_filename: "",
    new_cover_url: "",
    new_cover_filename: "",
    new_metadata: {
      release_title: "",
      artist_name: "",
      genre: "",
      language: "",
      copyright_line: "",
      p_line: "",
    },
    originality_declared: false,
    attachments: [],
  };
}

export default function LabelSupportTickets() {
  const [items, setItems] = useState([]);
  const [releases, setReleases] = useState([]);
  const [releaseTracks, setReleaseTracks] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(initialForm());
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    const { data } = await api.get("/tickets/label");
    setItems(data);
  };

  const loadReleases = async () => {
    const { data } = await api.get("/releases/");
    setReleases(data);
  };

  useEffect(() => {
    load();
    loadReleases();
  }, []);

  // Fetch tracks when release selected
  useEffect(() => {
    if (!form.release_id) { setReleaseTracks([]); return; }
    let cancelled = false;
    api.get(`/releases/${form.release_id}`).then(({ data }) => {
      if (!cancelled) setReleaseTracks(data.tracks || []);
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [form.release_id]);

  const reset = () => {
    setForm(initialForm());
    setErr("");
    setMsg("");
  };

  const uploadFile = async (file, purpose) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("purpose", purpose);
    const { data } = await api.post("/tickets/upload-attachment", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  };

  const handleAudioUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setErr("");
    try {
      const r = await uploadFile(file, "audio");
      setForm((f) => ({ ...f, new_audio_url: r.url, new_audio_filename: r.filename }));
    } catch (e2) {
      setErr(formatApiError(e2.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  };

  const handleCoverUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setErr("");
    try {
      const r = await uploadFile(file, "cover");
      setForm((f) => ({ ...f, new_cover_url: r.url, new_cover_filename: r.filename }));
    } catch (e2) {
      setErr(formatApiError(e2.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  };

  const handleAttachment = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setErr("");
    try {
      const r = await uploadFile(file, "general");
      setForm((f) => ({ ...f, attachments: [...f.attachments, { url: r.url, filename: r.filename }] }));
    } catch (e2) {
      setErr(formatApiError(e2.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setMsg("");
    if (!form.release_id) {
      setErr("Pilih rilisan terlebih dahulu");
      return;
    }
    setBusy(true);
    try {
      const payload = {
        release_id: form.release_id,
        category: form.category,
        subject: form.subject,
        description: form.description,
        attachments: form.attachments.map((a) => a.url),
      };
      if (form.category === "edit_metadata") {
        payload.new_metadata = form.new_metadata;
        payload.reason = form.reason;
      }
      if (form.category === "edit_audio") {
        payload.new_audio_url = form.new_audio_url;
        payload.new_audio_track_id = form.new_audio_track_id;
      }
      if (form.category === "edit_cover") {
        payload.new_cover_url = form.new_cover_url;
      }
      if (form.category === "takedown") {
        payload.reason = form.reason;
      }
      if (form.category === "content_id_claim") {
        payload.originality_declared = form.originality_declared;
      }
      await api.post("/tickets/label/create", payload);
      setMsg("Tiket berhasil dibuat.");
      setOpen(false);
      reset();
      load();
    } catch (e2) {
      setErr(formatApiError(e2.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-5 max-w-6xl">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Support</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter">Tiket Support</h1>
          <p className="text-sm text-zinc-400 mt-1">Takedown, edit metadata/audio/cover, Content ID, atau pertanyaan royalti.</p>
        </div>
        <button
          className="rm-btn-primary flex items-center gap-2"
          onClick={() => { reset(); setOpen(true); }}
          data-testid={SUPPORT.newTicketButton}
        >
          <Plus className="w-4 h-4" /> Tiket Baru
        </button>
      </div>

      {msg && (
        <div className="rounded-2xl bg-emerald-500/15 text-emerald-300 px-4 py-3 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" /> {msg}
        </div>
      )}

      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5">
          <div className="col-span-3">No. Tiket</div>
          <div className="col-span-3">Kategori</div>
          <div className="col-span-3">Rilisan</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-1 text-right">Aksi</div>
        </div>
        {items.length === 0 ? (
          <div className="p-10 text-center text-zinc-500 text-sm">
            <LifeBuoy className="w-8 h-8 mx-auto mb-3 text-zinc-700" />
            Belum ada tiket. Klik &quot;Tiket Baru&quot; untuk membuat permintaan.
          </div>
        ) : items.map((t) => (
          <Link
            key={t.id}
            to={`/label/support/${t.id}`}
            className="px-5 py-4 grid grid-cols-12 gap-3 items-center border-b border-white/5 last:border-0 hover:bg-white/[0.02]"
            data-testid={`label-ticket-row-${t.id}`}
          >
            <div className="col-span-12 md:col-span-3">
              <div className="font-display font-bold text-sm">{t.ticket_no}</div>
              <div className="text-xs text-zinc-500 truncate">{t.subject}</div>
            </div>
            <div className="col-span-6 md:col-span-3 text-sm">{TICKET_CATEGORY_LABELS[t.category] || t.category}</div>
            <div className="col-span-6 md:col-span-3 text-sm flex items-center gap-2">
              {t.release_cover_url && (
                <img src={fileUrl(t.release_cover_url)} alt="" className="w-8 h-8 rounded object-cover" />
              )}
              <span className="truncate">{t.release_title}</span>
            </div>
            <div className="col-span-6 md:col-span-2"><TicketStatusBadge status={t.status} /></div>
            <div className="col-span-6 md:col-span-1 text-right text-sm font-semibold rm-gradient-text">Detail →</div>
          </Link>
        ))}
      </div>

      {open && (
        <div className="fixed inset-0 z-50 bg-black/60 grid place-items-center p-4 overflow-y-auto" onClick={() => setOpen(false)}>
          <form
            onSubmit={submit}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-2xl rm-glass-strong rounded-[24px] p-6 space-y-4 my-8 max-h-[90vh] overflow-y-auto"
          >
            <div className="flex justify-between items-center">
              <h3 className="font-display font-extrabold text-xl tracking-tighter">Buat Tiket Support</h3>
              <button type="button" onClick={() => setOpen(false)} className="p-2 text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {err && (
              <div className="rounded-xl bg-red-500/15 text-red-300 px-3 py-2 text-sm flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" /> {err}
              </div>
            )}

            <div className="grid md:grid-cols-2 gap-3">
              <div>
                <label className="rm-label">Kategori</label>
                <select
                  className="rm-input"
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                  data-testid={SUPPORT.categorySelect}
                >
                  {CATEGORY_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="rm-label">Rilisan</label>
                <select
                  className="rm-input"
                  value={form.release_id}
                  onChange={(e) => setForm({ ...form, release_id: e.target.value, new_audio_track_id: "" })}
                  data-testid={SUPPORT.releaseSelect}
                  required
                >
                  <option value="">— Pilih rilisan —</option>
                  {releases.map((r) => (
                    <option key={r.id} value={r.id}>{r.release_title} — {r.artist_name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="rm-label">Subjek</label>
              <input
                className="rm-input"
                value={form.subject}
                onChange={(e) => setForm({ ...form, subject: e.target.value })}
                placeholder="Contoh: Takedown lagu karena masalah hak cipta"
                data-testid={SUPPORT.subjectInput}
                required
                minLength={3}
                maxLength={200}
              />
            </div>

            <div>
              <label className="rm-label">Deskripsi</label>
              <textarea
                className="rm-input min-h-[100px]"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Jelaskan kebutuhan Anda dengan detail…"
                data-testid={SUPPORT.descriptionInput}
                required
                minLength={3}
                maxLength={4000}
              />
            </div>

            {(form.category === "takedown" || form.category === "edit_metadata") && (
              <div>
                <label className="rm-label">{form.category === "takedown" ? "Alasan Takedown" : "Alasan Perubahan"}</label>
                <textarea
                  className="rm-input min-h-[70px]"
                  value={form.reason}
                  onChange={(e) => setForm({ ...form, reason: e.target.value })}
                  data-testid={SUPPORT.reasonInput}
                  required
                />
              </div>
            )}

            {form.category === "edit_metadata" && (
              <div className="rm-glass rounded-2xl p-4 space-y-3">
                <div className="text-xs font-bold uppercase tracking-widest text-zinc-400">Metadata Baru</div>
                <div className="grid md:grid-cols-2 gap-3">
                  <div>
                    <label className="rm-label">Judul Rilisan</label>
                    <input className="rm-input" value={form.new_metadata.release_title} onChange={(e) => setForm({ ...form, new_metadata: { ...form.new_metadata, release_title: e.target.value } })} />
                  </div>
                  <div>
                    <label className="rm-label">Artist</label>
                    <input className="rm-input" value={form.new_metadata.artist_name} onChange={(e) => setForm({ ...form, new_metadata: { ...form.new_metadata, artist_name: e.target.value } })} />
                  </div>
                  <div>
                    <label className="rm-label">Genre</label>
                    <input className="rm-input" value={form.new_metadata.genre} onChange={(e) => setForm({ ...form, new_metadata: { ...form.new_metadata, genre: e.target.value } })} />
                  </div>
                  <div>
                    <label className="rm-label">Bahasa</label>
                    <input className="rm-input" value={form.new_metadata.language} onChange={(e) => setForm({ ...form, new_metadata: { ...form.new_metadata, language: e.target.value } })} />
                  </div>
                  <div>
                    <label className="rm-label">© Line</label>
                    <input className="rm-input" value={form.new_metadata.copyright_line} onChange={(e) => setForm({ ...form, new_metadata: { ...form.new_metadata, copyright_line: e.target.value } })} />
                  </div>
                  <div>
                    <label className="rm-label">℗ Line</label>
                    <input className="rm-input" value={form.new_metadata.p_line} onChange={(e) => setForm({ ...form, new_metadata: { ...form.new_metadata, p_line: e.target.value } })} />
                  </div>
                </div>
              </div>
            )}

            {form.category === "edit_audio" && (
              <div className="rm-glass rounded-2xl p-4 space-y-3">
                <div className="text-xs font-bold uppercase tracking-widest text-zinc-400">File Audio Baru (WAV)</div>
                {releaseTracks.length > 0 ? (
                  <div>
                    <label className="rm-label">Track yang Diganti</label>
                    <select
                      className="rm-input"
                      value={form.new_audio_track_id}
                      onChange={(e) => setForm({ ...form, new_audio_track_id: e.target.value })}
                      data-testid={SUPPORT.trackSelect}
                      required
                    >
                      <option value="">— Pilih track —</option>
                      {releaseTracks.map((t) => (
                        <option key={t.id} value={t.id}>{t.track_number}. {t.track_title}</option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <div className="text-xs text-amber-300">{form.release_id ? "Memuat track…" : "Pilih rilisan terlebih dahulu"}</div>
                )}
                <div>
                  <label className="rm-label">Upload WAV Baru</label>
                  <input type="file" accept=".wav" className="rm-input" onChange={handleAudioUpload} data-testid={SUPPORT.audioUpload} required={!form.new_audio_url} />
                  {form.new_audio_url && (
                    <div className="text-xs text-emerald-300 mt-2 flex items-center gap-2">
                      <CheckCircle2 className="w-3 h-3" /> {form.new_audio_filename || "WAV terupload"}
                    </div>
                  )}
                </div>
              </div>
            )}

            {form.category === "edit_cover" && (
              <div className="rm-glass rounded-2xl p-4 space-y-3">
                <div className="text-xs font-bold uppercase tracking-widest text-zinc-400">Cover Baru (3000×3000)</div>
                <input type="file" accept=".jpg,.jpeg,.png" className="rm-input" onChange={handleCoverUpload} data-testid={SUPPORT.coverUpload} required={!form.new_cover_url} />
                {form.new_cover_url && (
                  <div className="flex items-center gap-3">
                    <img src={fileUrl(form.new_cover_url)} alt="cover baru" className="w-20 h-20 rounded-lg object-cover" />
                    <div className="text-xs text-emerald-300 flex items-center gap-2"><CheckCircle2 className="w-3 h-3" /> Cover 3000×3000 terupload</div>
                  </div>
                )}
              </div>
            )}

            {form.category === "content_id_claim" && (
              <label className="flex items-start gap-3 rm-glass rounded-2xl p-4 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.originality_declared}
                  onChange={(e) => setForm({ ...form, originality_declared: e.target.checked })}
                  data-testid={SUPPORT.originalityCheckbox}
                  className="mt-1"
                  required
                />
                <span className="text-sm text-zinc-300">
                  Saya menyatakan bahwa lagu ini original 100% milik saya / label saya, dan tidak mengandung
                  sample / copyright pihak lain yang dapat memicu konflik klaim Content ID. Saya bertanggung
                  jawab penuh atas pernyataan ini.
                </span>
              </label>
            )}

            <div>
              <label className="rm-label">Lampiran Tambahan (opsional)</label>
              <input type="file" className="rm-input" onChange={handleAttachment} accept=".jpg,.jpeg,.png,.pdf,.txt,.docx,.doc" />
              {form.attachments.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {form.attachments.map((a, idx) => (
                    <li key={idx} className="text-xs text-zinc-300 flex items-center gap-2">
                      <Paperclip className="w-3 h-3" /> {a.filename}
                      <button
                        type="button"
                        className="text-red-300 hover:text-red-200"
                        onClick={() => setForm({ ...form, attachments: form.attachments.filter((_, i) => i !== idx) })}
                      >Hapus</button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button type="button" className="rm-btn-ghost" onClick={() => setOpen(false)}>Batal</button>
              <button className="rm-btn-primary" disabled={busy} data-testid={SUPPORT.submitButton}>
                {busy ? "Mengirim…" : "Kirim Tiket"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
