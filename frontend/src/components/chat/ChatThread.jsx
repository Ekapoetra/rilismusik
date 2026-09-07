import React, { useEffect, useRef, useState } from "react";
import { Send, ArrowLeft, Paperclip, X, FileText, Loader2 } from "lucide-react";
import { timeLabel } from "./chatUtils";

const BACKEND = process.env.REACT_APP_BACKEND_URL;
const fileUrl = (u) => (u?.startsWith("http") ? u : `${BACKEND}${u}`);

export const OnlineDot = ({ online }) => (
  <span className={`inline-block h-2.5 w-2.5 rounded-full ${online ? "bg-emerald-400" : "bg-zinc-600"}`} title={online ? "Online" : "Offline"} />
);

const Attachment = ({ attachment }) => {
  if (!attachment) return null;
  if (attachment.kind === "image") {
    return <a href={fileUrl(attachment.url)} target="_blank" rel="noreferrer" data-testid="chat-attachment-image"><img src={fileUrl(attachment.url)} alt={attachment.filename} className="mt-1 max-h-52 rounded-lg border border-white/10 object-cover" /></a>;
  }
  return (
    <a href={fileUrl(attachment.url)} target="_blank" rel="noreferrer" className="mt-1 flex items-center gap-2 rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-xs text-zinc-200 hover:bg-black/50" data-testid="chat-attachment-file">
      <FileText className="h-4 w-4 shrink-0" /><span className="truncate">{attachment.filename}</span>
    </a>
  );
};

export const ChatThread = ({ title, subtitle, online, messages, myId, onSend, busy, onBack, disabled, disabledText, typing = [], onType, onUpload, headerActions }) => {
  const [text, setText] = useState("");
  const [pending, setPending] = useState(null);
  const [uploading, setUploading] = useState(false);
  const scrollRef = useRef(null);
  const lastTyped = useRef(0);
  const fileRef = useRef(null);
  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [messages?.length, typing.length]);

  const submit = async (e) => {
    e.preventDefault();
    if ((!text.trim() && !pending) || busy) return;
    await onSend(text.trim(), pending);
    setText(""); setPending(null);
  };
  const handleInput = (e) => {
    setText(e.target.value);
    const now = Date.now();
    if (onType && now - lastTyped.current > 2500) { lastTyped.current = now; onType(); }
  };
  const pickFile = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || !onUpload) return;
    setUploading(true);
    try { const att = await onUpload(file); if (att) setPending(att); }
    finally { setUploading(false); }
  };

  return (
    <div className="flex h-full flex-col" data-testid="chat-thread">
      <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3">
        {onBack && <button type="button" onClick={onBack} className="text-zinc-400 hover:text-white" data-testid="chat-thread-back"><ArrowLeft className="h-4 w-4" /></button>}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-sm font-bold text-white"><span className="truncate">{title}</span>{online !== null && online !== undefined && <OnlineDot online={online} />}</div>
          {subtitle && <div className="truncate text-[11px] text-zinc-500">{subtitle}</div>}
        </div>
        {headerActions}
      </div>
      <div ref={scrollRef} className="flex-1 space-y-2 overflow-y-auto p-3" data-testid="chat-thread-messages">
        {(messages || []).length === 0 && <div className="grid h-full place-items-center text-xs text-zinc-600">Belum ada pesan. Mulai percakapan.</div>}
        {(messages || []).map((m) => {
          const mine = m.sender_id === myId;
          return (
            <div key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
              <div className="max-w-[80%]">
                {!mine && <div className="mb-0.5 text-[10px] font-bold uppercase tracking-wide text-zinc-500">{m.sender_name}</div>}
                {m.body && <div className={`rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap break-words ${mine ? "bg-gradient-to-br from-[#FF1F8E] to-[#A24EFF] text-white" : "bg-white/[0.06] text-zinc-100"}`}>{m.body}</div>}
                <Attachment attachment={m.attachment} />
                <div className={`mt-0.5 text-[10px] text-zinc-600 ${mine ? "text-right" : ""}`}>{timeLabel(m.created_at)}</div>
              </div>
            </div>
          );
        })}
        {typing.length > 0 && <div className="flex items-center gap-1.5 pl-1 text-[11px] italic text-zinc-500" data-testid="chat-typing-indicator"><span className="flex gap-0.5"><span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500" style={{ animationDelay: "0ms" }} /><span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500" style={{ animationDelay: "120ms" }} /><span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500" style={{ animationDelay: "240ms" }} /></span>{typing.join(", ")} sedang mengetik…</div>}
      </div>
      {disabled ? (
        <div className="border-t border-white/10 p-3 text-center text-xs text-zinc-500">{disabledText}</div>
      ) : (
        <form onSubmit={submit} className="border-t border-white/10 p-3">
          {pending && (
            <div className="mb-2 flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-xs text-zinc-300" data-testid="chat-pending-attachment">
              {pending.kind === "image" ? <img src={fileUrl(pending.url)} alt="" className="h-8 w-8 rounded object-cover" /> : <FileText className="h-4 w-4" />}
              <span className="min-w-0 flex-1 truncate">{pending.filename}</span>
              <button type="button" onClick={() => setPending(null)} className="text-zinc-500 hover:text-white"><X className="h-4 w-4" /></button>
            </div>
          )}
          <div className="flex items-center gap-2">
            {onUpload && <>
              <input ref={fileRef} type="file" className="hidden" accept=".jpg,.jpeg,.png,.webp,.gif,.pdf,.txt,.doc,.docx" onChange={pickFile} data-testid="chat-file-input" />
              <button type="button" onClick={() => fileRef.current?.click()} disabled={uploading} className="grid h-10 w-10 shrink-0 place-items-center rounded-full text-zinc-400 hover:bg-white/[0.06] hover:text-white disabled:opacity-40" data-testid="chat-attach-button" title="Lampirkan berkas">{uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Paperclip className="h-4 w-4" />}</button>
            </>}
            <input className="rm-input flex-1" value={text} onChange={handleInput} placeholder="Tulis pesan…" data-testid="chat-thread-input" maxLength={4000} />
            <button type="submit" disabled={busy || (!text.trim() && !pending)} className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-gradient-to-br from-[#FF1F8E] to-[#A24EFF] text-white disabled:opacity-40" data-testid="chat-thread-send"><Send className="h-4 w-4" /></button>
          </div>
        </form>
      )}
    </div>
  );
};
