import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, formatApiError, fileUrl } from "@/api/client";
import TicketStatusBadge, { TICKET_CATEGORY_LABELS, TICKET_STATUS_LABELS } from "@/components/shared/TicketStatusBadge";
import { ADMIN_TICKET } from "@/constants/testIds";
import { ArrowLeft, Paperclip, Send, X, AlertTriangle } from "lucide-react";
import { useAuth } from "@/api/AuthContext";
import { TicketReleaseIdentifiers } from "@/components/shared/TicketReleaseIdentifiers";
import { TicketRequestSummary } from "@/components/shared/TicketRequestSummary";
import { ContentIdDocuments } from "@/components/shared/ContentIdDocuments";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

const STATUSES = Object.keys(TICKET_STATUS_LABELS);

export default function AdminTicketDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const { t: ui } = useAppPreferences();
  const canManage = hasPermission("support.manage");
  const [data, setData] = useState(null);
  const [body, setBody] = useState("");
  const [attachments, setAttachments] = useState([]);
  const [newStatus, setNewStatus] = useState("");
  const [internalNote, setInternalNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const scrollRef = useRef(null);
  const loadSequence = useRef(0);
  const editorTicket = useRef(null);
  const dirty = useRef({ status: false, note: false });

  const load = useCallback(async (resetEditor = false) => {
    const sequence = ++loadSequence.current;
    if (editorTicket.current !== id) {
      editorTicket.current = id;
      dirty.current = { status: false, note: false };
      setData(null);
    }
    try {
      const { data: r } = await api.get(`/tickets/${id}`);
      if (sequence !== loadSequence.current) return;
      setData(r);
      if (resetEditor === true) dirty.current = { status: false, note: false };
      if (!dirty.current.status) setNewStatus(r.ticket.status);
      if (!dirty.current.note) setInternalNote(r.ticket.internal_note || "");
    } catch (e) {
      if (sequence !== loadSequence.current) return;
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

  const applyStatus = async () => {
    if (data.ticket.category === "takedown" && newStatus === "done" && data.ticket.status !== "done" && !window.confirm("Selesaikan tiket takedown? Status rilisan Live akan berubah menjadi Takedown.")) return;
    setBusy(true); setErr("");
    try {
      const payload = {};
      if (newStatus && newStatus !== data.ticket.status) payload.status = newStatus;
      if (internalNote !== (data.ticket.internal_note || "")) payload.internal_note = internalNote;
      if (!payload.status && payload.internal_note === undefined) {
        setBusy(false);
        return;
      }
      await api.post(`/tickets/admin/${id}/status`, payload);
      await load(true);
    } catch (e2) {
      setErr(formatApiError(e2.response?.data?.detail));
    } finally { setBusy(false); }
  };

  if (!data) return <div className="text-zinc-500" data-testid="admin-ticket-loading-error">{err || "Memuat…"}</div>;
  const t = data.ticket;
  const isClosed = ["done", "rejected", "cancelled"].includes(t.status);

  return (
    <div className="min-w-0 space-y-5 max-w-7xl" data-testid="admin-ticket-detail-page">
      <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-sm text-zinc-400 hover:text-white" data-testid="admin-ticket-back">
        <ArrowLeft className="w-4 h-4" /> Kembali ke daftar
      </button>

      <div className="grid lg:grid-cols-3 gap-5">
        {/* LEFT: Conversation */}
        <div className="min-w-0 lg:col-span-2 space-y-4">
          <div className="rm-card p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="font-display font-extrabold text-2xl tracking-tighter">{t.ticket_no}</span>
                  <TicketStatusBadge status={t.status} />
                </div>
                <div className="text-sm text-zinc-400 mt-1">{TICKET_CATEGORY_LABELS[t.category] || t.category} • {new Date(t.created_at).toLocaleString("id-ID")}</div>
                <div className="break-words font-semibold text-lg mt-2" data-testid="admin-ticket-subject">{t.subject}</div>
              </div>
            </div>
          </div>

          {t.category === "content_id_claim" && <ContentIdDocuments ticket={t} prefix="admin-ticket" />}
          {t.linked_release_status === "taken_down" && <p className="border-l-2 border-amber-400 px-4 py-3 text-sm text-amber-300" data-testid="admin-ticket-takedown-synced">Status rilisan telah berubah menjadi Takedown.</p>}
          <div className="rm-card overflow-hidden">
            <div className="px-5 py-3 text-xs font-bold uppercase tracking-widest text-zinc-500 border-b border-white/5">Percakapan</div>
            <div ref={scrollRef} className="max-h-[55vh] overflow-y-auto p-5 space-y-4">
              {data.comments.map((c) => <CommentBubble key={c.id} c={c} />)}
            </div>
            {isClosed || !canManage ? (
              <div className="border-t border-white/5 p-4 text-sm text-zinc-500 text-center" data-testid="admin-ticket-readonly">{isClosed ? "Tiket sudah ditutup." : "Akses baca-saja."}</div>
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
                  placeholder="Balas tiket label…"
                  data-testid={ADMIN_TICKET.commentInput}
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
                    <input type="file" className="hidden" onChange={upload} accept=".jpg,.jpeg,.png,.pdf,.txt,.docx,.doc" />
                  </label>
                  <button type="submit" disabled={busy || !body.trim()} className="rm-btn-primary flex items-center gap-2" data-testid={ADMIN_TICKET.commentSubmit}>
                    <Send className="w-4 h-4" /> {busy ? "Mengirim…" : "Kirim"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>

        {/* RIGHT: Sidebar */}
        <div className="min-w-0 space-y-4">
          <div className="rm-card p-5 space-y-3">
            <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Label</div>
            <div className="text-sm">
              <div className="font-semibold">{t.label?.label_name || "—"}</div>
              <div className="text-zinc-400">{t.label?.pic_name}</div>
              <div className="text-zinc-500 text-xs">{t.label?.email}</div>
            </div>
          </div>

          <div className="rm-card p-5 space-y-3">
            <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Rilisan</div>
            <div className="flex items-center gap-3">
              {t.release_cover_url && <img src={fileUrl(t.release_cover_url)} alt="" className="w-14 h-14 rounded-lg object-cover" />}
              <div className="min-w-0">
                <div className="font-semibold truncate">{t.release_title}</div>
                <a href={`/admin/releases/${t.release_id}`} className="text-xs rm-gradient-text" data-testid="admin-ticket-release-link">Lihat detail rilisan →</a>
              </div>
            </div>
            <TicketReleaseIdentifiers upc={t.upc} tracks={t.release_tracks} isrcs={t.isrcs} prefix="admin-ticket" />
          </div>

          {(t.reason || t.new_metadata || t.new_audio_url || t.new_cover_url || t.originality_declared || t.youtube_url || t.youtube_urls?.length) && (
            <div className="rm-card p-5 space-y-3 text-sm">
              <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Detail Permintaan</div>
              <TicketRequestSummary ticket={t} prefix="admin-ticket" />
            </div>
          )}

          {canManage && <div className="rm-card p-5 space-y-3">
            <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Atur Status</div>
            <select translate="no" className="rm-input" value={newStatus} onChange={(e) => { dirty.current.status = true; setNewStatus(e.target.value); }} data-testid={ADMIN_TICKET.setStatusSelect}>
              {STATUSES.map((status) => React.createElement("option", { key: status, value: status, "data-testid": `admin-ticket-status-option-${status}` }, ui(TICKET_STATUS_LABELS[status])))}
            </select>
            <textarea
              className="rm-input min-h-[60px]"
              value={internalNote}
              onChange={(e) => { dirty.current.note = true; setInternalNote(e.target.value); }}
              placeholder="Catatan internal (tidak dilihat label)…"
              data-testid={ADMIN_TICKET.internalNoteInput}
            />
            <button onClick={applyStatus} disabled={busy} className="rm-btn-primary w-full" data-testid={ADMIN_TICKET.setStatusButton}>
              {busy ? "Menyimpan…" : "Simpan Perubahan"}
            </button>
          </div>}
        </div>
      </div>
    </div>
  );
}

function CommentBubble({ c }) {
  const isAdmin = (c.role && c.role.startsWith("admin")) || c.role === "super_admin";
  if (c.is_system) {
    return (
      <div className="break-words text-center text-xs text-zinc-500 italic py-1" data-testid={`admin-ticket-system-comment-${c.id}`}>
        {c.body} • {new Date(c.created_at).toLocaleString("id-ID")}
      </div>
    );
  }
  return (
    <div className={`flex ${isAdmin ? "justify-end" : "justify-start"}`}>
      <div className="min-w-0 max-w-[80%] break-words space-y-2">
        <div className={`text-[10px] uppercase tracking-widest font-bold ${isAdmin ? "text-pink-300" : "text-zinc-500"}`}>
          {isAdmin ? "Admin" : "Label"} • {c.user_name || ""} • {new Date(c.created_at).toLocaleString("id-ID")}
        </div>
        <div data-testid={`admin-ticket-comment-${c.id}`} className={`break-words rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap ${isAdmin ? "bg-gradient-to-br from-[#FF1F8E] to-[#A24EFF] text-white" : "rm-glass text-zinc-100"}`}>
          {c.body}
        </div>
        {c.attachments?.length > 0 && (
          <div className="space-y-1">
            {c.attachments.map((url, i) => (
              <a key={url} data-testid={`admin-ticket-comment-${c.id}-attachment-${i + 1}`} href={fileUrl(url)} target="_blank" rel="noreferrer" className="text-xs text-zinc-300 hover:text-white flex items-center gap-2">
                <Paperclip className="w-3 h-3" /> Lampiran {i + 1}
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
