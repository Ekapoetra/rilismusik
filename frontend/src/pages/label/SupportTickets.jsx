import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError, fileUrl } from "@/api/client";
import TicketStatusBadge, { TICKET_CATEGORY_LABELS } from "@/components/shared/TicketStatusBadge";
import { SUPPORT } from "@/constants/testIds";
import { LifeBuoy, Plus, CheckCircle2 } from "lucide-react";
import { SupportTicketModal } from "@/components/label/SupportTicketModal";
import { AUTO_SUBJECT_CATEGORIES, CONTENT_ID_CATEGORIES, metadataFromRelease, ticketSubject } from "@/components/label/tickets/ticketFormConfig";

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
    youtube_urls: [""],
    attachments: [],
  };
}

export default function LabelSupportTickets() {
  const [items, setItems] = useState([]);
  const [releases, setReleases] = useState([]);
  const [releaseTracks, setReleaseTracks] = useState([]);
  const [releaseInfo, setReleaseInfo] = useState(null);
  const [releaseLoading, setReleaseLoading] = useState(false);
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
    Promise.all([load(), loadReleases()]).catch((e) => setErr(formatApiError(e.response?.data?.detail) || "Gagal memuat tiket dan rilisan."));
  }, []);

  // Fetch tracks when release selected
  useEffect(() => {
    setReleaseTracks([]); setReleaseInfo(null);
    if (!form.release_id) { setReleaseLoading(false); return; }
    let cancelled = false;
    setReleaseLoading(true);
    setErr("");
    api.get(`/releases/${form.release_id}`).then(({ data }) => {
      if (!cancelled) {
        setReleaseTracks(data.tracks || []);
        setReleaseInfo(data);
        setForm((current) => ({ ...current, new_metadata: metadataFromRelease(data), subject: AUTO_SUBJECT_CATEGORIES.includes(current.category) ? ticketSubject(current.category, data) : current.subject }));
      }
    }).catch((error) => {
      if (!cancelled) setErr(formatApiError(error.response?.data?.detail));
    }).finally(() => { if (!cancelled) setReleaseLoading(false); });
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
    if (busy || releaseLoading) return;
    setErr("");
    setMsg("");
    if (!form.release_id || releaseInfo?.id !== form.release_id) {
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
      if (CONTENT_ID_CATEGORIES.includes(form.category)) {
        payload.originality_declared = form.originality_declared;
        payload.youtube_urls = form.youtube_urls;
      }
      await api.post("/tickets/label/create", payload);
      setOpen(false);
      reset();
      setMsg("Tiket berhasil dibuat.");
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
          <p className="text-sm text-zinc-400 mt-1">Takedown, edit metadata/audio/cover, dan YouTube Content ID.</p>
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
        <div role="status" data-testid="support-ticket-success" className="rounded-2xl bg-emerald-500/15 text-emerald-300 px-4 py-3 text-sm flex items-center gap-2">
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

      {!open && err && <p role="alert" data-testid="support-list-error" className="text-sm text-red-300">{err}</p>}
      <SupportTicketModal open={open} close={() => setOpen(false)} submit={submit} form={form} setForm={setForm} releases={releases} releaseTracks={releaseTracks} releaseInfo={releaseInfo} releaseLoading={releaseLoading} busy={busy} err={err} handleAudioUpload={handleAudioUpload} handleCoverUpload={handleCoverUpload} handleAttachment={handleAttachment} />
    </div>
  );
}
