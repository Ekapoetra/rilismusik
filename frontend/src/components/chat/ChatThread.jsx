import React, { useEffect, useRef, useState } from "react";
import { Send, ArrowLeft } from "lucide-react";
import { timeLabel } from "./chatUtils";

export const OnlineDot = ({ online }) => (
  <span className={`inline-block h-2.5 w-2.5 rounded-full ${online ? "bg-emerald-400" : "bg-zinc-600"}`} title={online ? "Online" : "Offline"} />
);

export const ChatThread = ({ title, subtitle, online, messages, myId, onSend, busy, onBack, disabled, disabledText }) => {
  const [text, setText] = useState("");
  const scrollRef = useRef(null);
  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [messages?.length]);
  const submit = (e) => { e.preventDefault(); if (!text.trim() || busy) return; onSend(text.trim()); setText(""); };
  return (
    <div className="flex h-full flex-col" data-testid="chat-thread">
      <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3">
        {onBack && <button type="button" onClick={onBack} className="text-zinc-400 hover:text-white" data-testid="chat-thread-back"><ArrowLeft className="h-4 w-4" /></button>}
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-sm font-bold text-white"><span className="truncate">{title}</span>{online !== null && online !== undefined && <OnlineDot online={online} />}</div>
          {subtitle && <div className="truncate text-[11px] text-zinc-500">{subtitle}</div>}
        </div>
      </div>
      <div ref={scrollRef} className="flex-1 space-y-2 overflow-y-auto p-3" data-testid="chat-thread-messages">
        {(messages || []).length === 0 && <div className="grid h-full place-items-center text-xs text-zinc-600">Belum ada pesan. Mulai percakapan.</div>}
        {(messages || []).map((m) => {
          const mine = m.sender_id === myId;
          return (
            <div key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
              <div className="max-w-[80%]">
                {!mine && <div className="mb-0.5 text-[10px] font-bold uppercase tracking-wide text-zinc-500">{m.sender_name}</div>}
                <div className={`rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap break-words ${mine ? "bg-gradient-to-br from-[#FF1F8E] to-[#A24EFF] text-white" : "bg-white/[0.06] text-zinc-100"}`}>{m.body}</div>
                <div className={`mt-0.5 text-[10px] text-zinc-600 ${mine ? "text-right" : ""}`}>{timeLabel(m.created_at)}</div>
              </div>
            </div>
          );
        })}
      </div>
      {disabled ? (
        <div className="border-t border-white/10 p-3 text-center text-xs text-zinc-500">{disabledText}</div>
      ) : (
        <form onSubmit={submit} className="flex items-center gap-2 border-t border-white/10 p-3">
          <input className="rm-input flex-1" value={text} onChange={(e) => setText(e.target.value)} placeholder="Tulis pesan…" data-testid="chat-thread-input" maxLength={4000} />
          <button type="submit" disabled={busy || !text.trim()} className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-gradient-to-br from-[#FF1F8E] to-[#A24EFF] text-white disabled:opacity-40" data-testid="chat-thread-send"><Send className="h-4 w-4" /></button>
        </form>
      )}
    </div>
  );
};
