import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, formatApiError, fileUrl } from "@/api/client";
import TicketStatusBadge, { TICKET_CATEGORY_LABELS, TICKET_STATUS_LABELS } from "@/components/shared/TicketStatusBadge";
import { ADMIN_TICKET } from "@/constants/testIds";
import { ArrowLeft, Paperclip, Send, X, AlertTriangle, Info } from "lucide-react";

const STATUSES = Object.keys(TICKET_STATUS_LABELS);

export default function AdminTicketDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [body, setBody] = useState("");
  const [attachments, setAttachments] = useState([]);
  const [newStatus, setNewStatus] = useState("");
  const [internalNote, setInternalNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const scrollRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const { data: r } = await api.get(`/tickets/${id}`);
      setData(r);
      setNewStatus(r.ticket.status);
      setInternalNote(r.ticket.internal_note || "");
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

  const applyStatus = async () => {
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
      await load();
    } catch (e2) {
      setErr(formatApiError(e2.response?.data?.detail));
    } finally { setBusy(false); }
  };

  if (!data) return <div className="text-zinc-500">Memuat…</div>;
  const t = data.ticket;
  const isClosed = ["done", "rejected", "cancelled"].includes(t.status);

  return (
    <div className="space-y-5 max-w-7xl">
      <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-sm text-zinc-400 hover:text-white">
        <ArrowLeft className="w-4 h-4" /> Kembali ke daftar
      </button>

      <div className="grid lg:grid-cols-3 gap-5">
        {/* LEFT: Conversation */}
        <div className="lg:col-span-2 space-y-4">
          <div className="rm-card p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="font-display font-extrabold text-2xl tracking-tighter">{t.ticket_no}</span>
                  <TicketStatusBadge status={t.status} />
                </div>
                <div className="text-sm text-zinc-400 mt-1">{TICKET_CATEGORY_LABELS[t.category] || t.category} • {new Date(t.created_at).toLocaleString("id-ID")}</div>
                <div className="font-semibold text-lg mt-2">{t.subject}</div>
              </div>
            </div>
          </div>

          <div className="rm-card overflow-hidden">
            <div className="px-5 py-3 text-xs font-bold uppercase tracking-widest text-zinc-500 border-b border-white/5">Percakapan</div>
            <div ref={scrollRef} className="max-h-[55vh] overflow-y-auto p-5 space-y-4">
              {data.comments.map((c) => <CommentBubble key={c.id} c={c} />)}
            </div>
            {isClosed ? (
              <div className="border-t border-white/5 p-4 text-sm text-zinc-500 text-center">Tiket sudah ditutup.</div>
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
        <div className="space-y-4">
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
                <a href={`/admin/releases/${t.release_id}`} className="text-xs rm-gradient-text">Lihat detail rilisan →</a>
              </div>
            </div>
          </div>

          {(t.reason || t.new_metadata || t.new_audio_url || t.new_cover_url || t.originality_declared || t.youtube_url) && (
            <div className="rm-card p-5 space-y-3 text-sm">
              <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Detail Permintaan</div>
              {t.reason && (
                <div>
                  <div className="text-xs text-zinc-500">Alasan</div>
                  <div className="text-zinc-200 whitespace-pre-wrap">{t.reason}</div>
                </div>
              )}
              {t.youtube_url && (
                <div>
                  <div className="text-xs text-zinc-500">Link YouTube Content ID</div>
                  <a href={t.youtube_url} target="_blank" rel="noreferrer" className="block rm-gradient-text font-semibold break-all" data-testid="admin-ticket-youtube-link">{t.youtube_url} →</a>
                </div>
              )}
              {t.new_audio_url && (
                <a href={fileUrl(t.new_audio_url)} target="_blank" rel="noreferrer" className="block rm-gradient-text font-semibold">Buka WAV Baru →</a>
              )}
              {t.new_cover_url && (
                <div>
                  <div className="text-xs text-zinc-500 mb-1">Cover Baru</div>
                  <img src={fileUrl(t.new_cover_url)} alt="" className="w-32 h-32 rounded-lg object-cover" />
                </div>
              )}
              {t.new_metadata && (
                <div>
                  <div className="text-xs text-zinc-500">Metadata Baru</div>
                  <pre className="text-xs text-zinc-300 whitespace-pre-wrap break-words bg-white/[0.03] p-3 rounded-lg">{JSON.stringify(t.new_metadata, null, 2)}</pre>
                </div>
              )}
              {t.originality_declared && (
                <div className="text-emerald-300 text-xs flex items-center gap-2"><Info className="w-3 h-3" /> Originalitas dinyatakan ✓</div>
              )}
            </div>
          )}

          <div className="rm-card p-5 space-y-3">
            <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Atur Status</div>
            <select className="rm-input" value={newStatus} onChange={(e) => setNewStatus(e.target.value)} data-testid={ADMIN_TICKET.setStatusSelect}>
              {STATUSES.map((s) => <option key={s} value={s}>{TICKET_STATUS_LABELS[s]}</option>)}
            </select>
            <textarea
              className="rm-input min-h-[60px]"
              value={internalNote}
              onChange={(e) => setInternalNote(e.target.value)}
              placeholder="Catatan internal (tidak dilihat label)…"
              data-testid={ADMIN_TICKET.internalNoteInput}
            />
            <button onClick={applyStatus} disabled={busy} className="rm-btn-primary w-full" data-testid={ADMIN_TICKET.setStatusButton}>
              {busy ? "Menyimpan…" : "Simpan Perubahan"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function CommentBubble({ c }) {
  const isAdmin = (c.role && c.role.startsWith("admin")) || c.role === "super_admin";
  if (c.is_system) {
    return (
      <div className="text-center text-xs text-zinc-500 italic py-1">
        {c.body} • {new Date(c.created_at).toLocaleString("id-ID")}
      </div>
    );
  }
  return (
    <div className={`flex ${isAdmin ? "justify-end" : "justify-start"}`}>
      <div className="max-w-[80%] space-y-2">
        <div className={`text-[10px] uppercase tracking-widest font-bold ${isAdmin ? "text-pink-300" : "text-zinc-500"}`}>
          {isAdmin ? "Admin" : "Label"} • {c.user_name || ""} • {new Date(c.created_at).toLocaleString("id-ID")}
        </div>
        <div className={`rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap ${isAdmin ? "bg-gradient-to-br from-[#FF1F8E] to-[#A24EFF] text-white" : "rm-glass text-zinc-100"}`}>
          {c.body}
        </div>
        {c.attachments?.length > 0 && (
          <div className="space-y-1">
            {c.attachments.map((url, i) => (
              <a key={url} href={fileUrl(url)} target="_blank" rel="noreferrer" className="block text-xs text-zinc-300 hover:text-white flex items-center gap-2">
                <Paperclip className="w-3 h-3" /> Lampiran {i + 1}
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
