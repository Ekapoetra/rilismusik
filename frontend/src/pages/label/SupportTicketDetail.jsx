import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, formatApiError, fileUrl } from "@/api/client";
import TicketStatusBadge, { TICKET_CATEGORY_LABELS } from "@/components/shared/TicketStatusBadge";
import { SUPPORT } from "@/constants/testIds";
import { ArrowLeft, Paperclip, Send, X, AlertTriangle, Ban } from "lucide-react";
import { TicketReleaseIdentifiers } from "@/components/shared/TicketReleaseIdentifiers";
import { TicketRequestSummary } from "@/components/shared/TicketRequestSummary";
import { ContentIdDocuments } from "@/components/shared/ContentIdDocuments";

const NON_CANCELLABLE = ["done", "submitted_to_believe", "rejected", "cancelled"];

export default function LabelSupportTicketDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [body, setBody] = useState("");
  const [attachments, setAttachments] = useState([]);
  const [draftForm, setDraftForm] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const scrollRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const { data: r } = await api.get(`/tickets/${id}`);
      setData(r);
      if (r.ticket?.status === "draft") setDraftForm({ subject: r.ticket.subject || "", description: r.ticket.description || "" });
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail));
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [data?.comments?.length]);

  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true); setErr("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("purpose", "general");
      const { data: r } = await api.post("/tickets/upload-attachment", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setAttachments((a) => [...a, { url: r.url, filename: r.filename }]);
    } catch (e2) {
      setErr(formatApiError(e2.response?.data?.detail));
    } finally { setBusy(false); }
  };

  const sendComment = async (e) => {
    e.preventDefault();
    if (!body.trim()) return;
    setBusy(true); setErr("");
    try {
      await api.post(`/tickets/${id}/comment`, { body, attachments: attachments.map((a) => a.url) });
      setBody(""); setAttachments([]);
      await load();
    } catch (e2) {
      setErr(formatApiError(e2.response?.data?.detail));
    } finally { setBusy(false); }
  };

  const saveDraft = async () => {
    setBusy(true); setErr("");
    try {
      await api.patch(`/tickets/label/${id}`, draftForm);
      await load();
    } catch (e2) {
      setErr(formatApiError(e2.response?.data?.detail));
    } finally { setBusy(false); }
  };

  const submitDraft = async () => {
    setBusy(true); setErr("");
    try {
      await api.patch(`/tickets/label/${id}`, draftForm);
      await api.post(`/tickets/label/${id}/submit`);
      await load();
    } catch (e2) {
      setErr(formatApiError(e2.response?.data?.detail));
    } finally { setBusy(false); }
  };

  const cancelTicket = async () => {
    if (!window.confirm(t?.status === "draft" ? "Yakin ingin menghapus draf ini?" : "Yakin ingin membatalkan tiket ini?")) return;
    setBusy(true); setErr("");
    try {
      await api.post(`/tickets/${id}/cancel`);
      await load();
    } catch (e2) {
      setErr(formatApiError(e2.response?.data?.detail));
    } finally { setBusy(false); }
  };

  if (!data) {
    return <div className="text-zinc-500" data-testid="label-ticket-loading-error">{err || "Memuat…"}</div>;
  }

  const t = data.ticket;
  const isDraft = t.status === "draft";
  const canCancel = !NON_CANCELLABLE.includes(t.status);
  const isClosed = ["done", "rejected", "cancelled"].includes(t.status);

  return (
    <div className="min-w-0 space-y-5 max-w-5xl" data-testid="label-ticket-detail-page">
      <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-sm text-zinc-400 hover:text-white" data-testid="label-ticket-back">
        <ArrowLeft className="w-4 h-4" /> Kembali
      </button>

      <div className="rm-card p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="font-display font-extrabold text-2xl tracking-tighter">{t.ticket_no}</span>
              <TicketStatusBadge status={t.status} />
            </div>
            <div className="text-sm text-zinc-400 mt-1">{TICKET_CATEGORY_LABELS[t.category] || t.category} • {new Date(t.created_at).toLocaleString("id-ID")}</div>
            <div className="break-words font-semibold text-lg mt-2" data-testid="label-ticket-subject">{t.subject}</div>
          </div>
          {canCancel && (
            <button
              type="button"
              onClick={cancelTicket}
              disabled={busy}
              className="rm-btn-ghost flex items-center gap-2 text-red-300 hover:text-red-200"
              data-testid={SUPPORT.cancelTicketButton}
            >
              <Ban className="w-4 h-4" /> {isDraft ? "Hapus Draf" : "Batalkan"}
            </button>
          )}
        </div>

        <div className="mt-5 grid md:grid-cols-3 gap-4">
          {t.release_id ? (
            <div className="col-span-1 min-w-0"><Link
              to={`/label/releases/${t.release_id}`}
              data-testid="label-ticket-release-link"
              className="col-span-1 rm-glass rounded-2xl p-4 flex items-center gap-3 hover:bg-white/[0.04]"
            >
              {t.release_cover_url && (
                <img src={fileUrl(t.release_cover_url)} alt="" className="w-14 h-14 rounded-lg object-cover" />
              )}
              <div className="min-w-0">
                <div className="text-xs text-zinc-500">Rilisan</div>
                <div className="font-semibold truncate">{t.release_title}</div>
                <div className="text-xs rm-gradient-text">Lihat detail →</div>
              </div>
            </Link>
            <TicketReleaseIdentifiers upc={t.upc} tracks={t.release_tracks} isrcs={t.isrcs} prefix="label-ticket" /></div>
          ) : null}

          {(t.reason || t.new_metadata || t.new_audio_url || t.new_cover_url || t.originality_declared || t.youtube_url || t.youtube_urls?.length) && (
            <div className="min-w-0 col-span-1 md:col-span-2 rm-glass rounded-2xl p-4 text-sm space-y-2">
              <TicketRequestSummary ticket={t} prefix="label-ticket" />
            </div>
          )}
        </div>
      </div>

      {/* Comments */}
      {t.linked_release_status === "taken_down" && <p className="border-l-2 border-amber-400 px-4 py-3 text-sm text-amber-300" data-testid="label-ticket-takedown-synced">Status rilisan telah berubah menjadi Takedown.</p>}
      {t.category === "content_id_claim" && <ContentIdDocuments ticket={t} prefix="label-ticket" />}
      <div className="rm-card overflow-hidden">
        <div className="px-5 py-3 text-xs font-bold uppercase tracking-widest text-zinc-500 border-b border-white/5">{isDraft ? "Draf" : "Percakapan"}</div>
        {isDraft && draftForm ? (
          <div className="p-5 space-y-3">
            <p className="text-xs text-zinc-500" data-testid="label-ticket-draft-note">Draf belum dikirim — belum terlihat oleh admin.</p>
            {err && (
              <div className="rounded-xl bg-red-500/15 text-red-300 px-3 py-2 text-sm flex items-center gap-2" role="alert">
                <AlertTriangle className="w-4 h-4" /> {err}
              </div>
            )}
            <input
              className="rm-input w-full"
              value={draftForm.subject}
              onChange={(e) => setDraftForm((f) => ({ ...f, subject: e.target.value }))}
              placeholder="Subjek"
              data-testid="label-ticket-draft-subject"
              maxLength={200}
            />
            <textarea
              className="rm-input min-h-28 w-full"
              value={draftForm.description}
              onChange={(e) => setDraftForm((f) => ({ ...f, description: e.target.value }))}
              placeholder="Jelaskan masalah atau permintaan Anda…"
              data-testid="label-ticket-draft-description"
              maxLength={4000}
            />
            <div className="flex justify-end gap-2">
              <button type="button" onClick={saveDraft} disabled={busy} className="rm-btn-ghost" data-testid="label-ticket-draft-save">
                {busy ? "Menyimpan…" : "Simpan Perubahan"}
              </button>
              <button type="button" onClick={submitDraft} disabled={busy || draftForm.subject.trim().length < 3 || draftForm.description.trim().length < 3} className="rm-btn-primary flex items-center gap-2" data-testid="label-ticket-draft-submit">
                <Send className="w-4 h-4" /> {busy ? "Mengirim…" : "Kirim Tiket"}
              </button>
            </div>
          </div>
        ) : (
          <>
        <div ref={scrollRef} className="max-h-[55vh] overflow-y-auto p-5 space-y-4">
          {data.comments.map((c) => (
            <CommentBubble key={c.id} c={c} />
          ))}
        </div>

        {isClosed ? (
          <div className="border-t border-white/5 p-4 text-sm text-zinc-500 text-center">Tiket sudah ditutup. Tidak bisa menambah komentar.</div>
        ) : (
          <form onSubmit={sendComment} className="border-t border-white/5 p-4 space-y-3">
            {err && (
              <div className="rounded-xl bg-red-500/15 text-red-300 px-3 py-2 text-sm flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" /> {err}
              </div>
            )}
            <textarea
              className="rm-input min-h-[70px]"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Tulis pesan…"
              data-testid={SUPPORT.commentInput}
              maxLength={4000}
            />
            {attachments.length > 0 && (
              <ul className="space-y-1">
                {attachments.map((a, idx) => (
                  <li key={a.url || a.filename} className="text-xs text-zinc-300 flex items-center gap-2">
                    <Paperclip className="w-3 h-3" /> {a.filename}
                    <button type="button" onClick={() => setAttachments(attachments.filter((_, i) => i !== idx))} className="text-red-300 hover:text-red-200"><X className="w-3 h-3" /></button>
                  </li>
                ))}
              </ul>
            )}
            <div className="flex justify-between items-center">
              <label className="rm-btn-ghost cursor-pointer text-sm flex items-center gap-2">
                <Paperclip className="w-4 h-4" /> Lampiran
                <input type="file" className="hidden" onChange={upload} data-testid={SUPPORT.commentAttachment} accept=".jpg,.jpeg,.png,.pdf,.txt,.docx,.doc" />
              </label>
              <button type="submit" disabled={busy || !body.trim()} className="rm-btn-primary flex items-center gap-2" data-testid={SUPPORT.commentSubmit}>
                <Send className="w-4 h-4" /> {busy ? "Mengirim…" : "Kirim"}
              </button>
            </div>
          </form>
        )}
          </>
        )}
      </div>
    </div>
  );
}

function CommentBubble({ c }) {
  const isAdmin = c.role && c.role.startsWith("admin") || c.role === "super_admin";
  const isLabel = c.role === "label";
  if (c.is_system) {
    return (
      <div className="break-words text-center text-xs text-zinc-500 italic py-1" data-testid={`label-ticket-system-comment-${c.id}`}>
        {c.body} • {new Date(c.created_at).toLocaleString("id-ID")}
      </div>
    );
  }
  return (
    <div className={`flex ${isLabel ? "justify-end" : "justify-start"}`}>
      <div className={`min-w-0 max-w-[80%] break-words space-y-2 ${isLabel ? "items-end" : "items-start"}`}>
        <div className={`text-[10px] uppercase tracking-widest font-bold ${isAdmin ? "text-pink-300" : "text-zinc-500"}`}>
          {isAdmin ? "Admin" : isLabel ? "Label" : c.role} • {c.user_name || ""} • {new Date(c.created_at).toLocaleString("id-ID")}
        </div>
        <div
          data-testid={`label-ticket-comment-${c.id}`} className={`break-words rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap ${isLabel ? "bg-gradient-to-br from-[#FF1F8E] to-[#A24EFF] text-white" : "rm-glass text-zinc-100"}`}
        >
          {c.body}
        </div>
        {c.attachments?.length > 0 && (
          <div className="space-y-1">
            {c.attachments.map((url, i) => (
              <a key={url} data-testid={`label-ticket-comment-${c.id}-attachment-${i + 1}`} href={fileUrl(url)} target="_blank" rel="noreferrer" className="text-xs text-zinc-300 hover:text-white flex items-center gap-2">
                <Paperclip className="w-3 h-3" /> Lampiran {i + 1}
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
