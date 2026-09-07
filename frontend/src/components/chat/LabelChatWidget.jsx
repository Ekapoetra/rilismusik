import React, { useCallback, useEffect, useRef, useState } from "react";
import { MessageCircle, X } from "lucide-react";
import { api } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { toast } from "@/components/ui/sonner";
import { ChatThread, OnlineDot } from "./ChatThread";
import { playChatSound, uploadChatAttachment } from "./chatUtils";

export default function LabelChatWidget() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [supportOnline, setSupportOnline] = useState(false);
  const [typing, setTyping] = useState([]);
  const [unread, setUnread] = useState(0);
  const [busy, setBusy] = useState(false);
  const prevUnread = useRef(0);
  const openRef = useRef(false);
  const convRef = useRef(null);
  useEffect(() => { openRef.current = open; }, [open]);

  const loadThread = useCallback(async () => {
    try {
      const { data } = await api.get("/chat/label/thread");
      setMessages(data.messages || []);
      setSupportOnline(!!data.support_online);
      setTyping(data.typing || []);
      convRef.current = data.conversation_id;
    } catch { /* label may not be ready */ }
  }, []);

  useEffect(() => {
    const beat = () => api.post("/chat/heartbeat").catch(() => {});
    beat();
    const hb = setInterval(beat, 20000);
    const poll = setInterval(async () => {
      try {
        const { data } = await api.get("/chat/unread");
        const n = data.unread || 0;
        if (n > prevUnread.current && !openRef.current) { playChatSound(); toast.message("Pesan baru dari Support"); }
        prevUnread.current = n;
        setUnread(openRef.current ? 0 : n);
      } catch { /* noop */ }
    }, 4000);
    return () => { clearInterval(hb); clearInterval(poll); };
  }, []);

  useEffect(() => {
    if (!open) return;
    loadThread();
    setUnread(0); prevUnread.current = 0;
    const t = setInterval(loadThread, 3000);
    return () => clearInterval(t);
  }, [open, loadThread]);

  const send = async (body, attachment) => {
    setBusy(true);
    try { await api.post("/chat/label/thread", { body, attachment }); await loadThread(); }
    catch { toast.error("Gagal mengirim pesan"); }
    finally { setBusy(false); }
  };
  const onType = () => { api.post("/chat/typing/" + (convRef.current || "x")).catch(() => {}); };
  const onUpload = async (file) => {
    try { return await uploadChatAttachment(file); }
    catch (e) { toast.error(e.response?.data?.detail || "Gagal mengunggah berkas"); return null; }
  };

  return (
    <>
      {open && (
        <div className="fixed bottom-24 right-4 z-[60] flex h-[70vh] max-h-[560px] w-[92vw] max-w-sm flex-col overflow-hidden rounded-2xl border border-white/10 bg-[#101010] shadow-2xl md:bottom-6 md:right-24" data-testid="label-chat-panel">
          <div className="flex items-center justify-between border-b border-white/10 bg-white/[0.03] px-4 py-3">
            <div className="flex items-center gap-2 text-sm font-bold text-white">Chat Support <OnlineDot online={supportOnline} /></div>
            <button onClick={() => setOpen(false)} className="text-zinc-400 hover:text-white" data-testid="label-chat-close"><X className="h-4 w-4" /></button>
          </div>
          <div className="min-h-0 flex-1">
            <ChatThread title="Tim Support" subtitle={supportOnline ? "Online" : "Akan membalas segera"} online={supportOnline} messages={messages} myId={user?.id} onSend={send} busy={busy} typing={typing} onType={onType} onUpload={onUpload} />
          </div>
        </div>
      )}
      <button onClick={() => setOpen((v) => !v)} className="fixed bottom-20 right-4 z-[60] grid h-14 w-14 place-items-center rounded-full bg-gradient-to-br from-[#FF1F8E] to-[#A24EFF] text-white shadow-2xl transition-transform hover:scale-105 md:bottom-6 md:right-6" data-testid="label-chat-toggle">
        {open ? <X className="h-6 w-6" /> : <MessageCircle className="h-6 w-6" />}
        {!open && unread > 0 && <span className="absolute -right-1 -top-1 grid h-6 min-w-6 place-items-center rounded-full bg-red-500 px-1.5 text-xs font-bold text-white" data-testid="label-chat-unread">{unread > 99 ? "99+" : unread}</span>}
      </button>
    </>
  );
}
