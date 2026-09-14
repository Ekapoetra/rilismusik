import React, { useCallback, useEffect, useRef, useState } from "react";
import { MessageCircle, X } from "lucide-react";
import { api } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { toast } from "@/components/ui/sonner";
import { ChatThread, OnlineDot } from "./ChatThread";
import { uploadChatAttachment } from "./chatUtils";
import { useIncomingChat, NewChatNotice } from "./NewChatNotice";

export default function LabelChatWidget() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [supportOnline, setSupportOnline] = useState(false);
  const [withinHours, setWithinHours] = useState(false);
  const [typing, setTyping] = useState([]);
  const [unread, setUnread] = useState(0);
  const [busy, setBusy] = useState(false);
  const chatNotice = useIncomingChat(() => setOpen(true));
  const receiveChat = chatNotice.receive;
  const openRef = useRef(false);
  const convRef = useRef(null);
  useEffect(() => { openRef.current = open; }, [open]);

  const loadThread = useCallback(async () => {
    try {
      const { data } = await api.get("/chat/label/thread");
      setMessages(data.messages || []);
      setSupportOnline(!!data.support_online);
      setWithinHours(!!data.within_hours);
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
        receiveChat(data);
        setUnread(openRef.current ? 0 : n);
      } catch { /* noop */ }
    }, 4000);
    return () => { clearInterval(hb); clearInterval(poll); };
  }, [receiveChat]);

  useEffect(() => {
    if (!open) return;
    loadThread();
    setUnread(0);
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
        <div className="fixed bottom-14 right-4 z-[60] flex h-[70vh] max-h-[560px] w-[92vw] max-w-sm flex-col overflow-hidden rounded-2xl rounded-br-none border border-white/10 bg-[#101010] shadow-2xl md:right-6" data-testid="label-chat-panel">
          <div className="flex items-center justify-between border-b border-white/10 bg-white/[0.03] px-4 py-3">
            <div className="flex items-center gap-2 text-sm font-bold text-white">Chat Support <OnlineDot online={supportOnline} /></div>
            <button onClick={() => setOpen(false)} className="text-zinc-400 hover:text-white" data-testid="label-chat-close"><X className="h-4 w-4" /></button>
          </div>
          <div className="min-h-0 flex-1">
            <ChatThread title="Tim Support" subtitle={supportOnline ? "Online sekarang" : withinHours ? "Dalam jam operasional" : "Di luar jam operasional — dibalas pada jam kerja"} online={supportOnline} messages={messages} myId={user?.id} onSend={send} busy={busy} typing={typing} onType={onType} onUpload={onUpload} />
          </div>
        </div>
      )}
      {chatNotice.notice && <NewChatNotice onOpen={chatNotice.showChat} onDismiss={chatNotice.dismiss} />}
      {!open && (
        <button onClick={() => setOpen(true)} className="fixed bottom-0 right-4 z-[60] inline-flex items-center gap-2 rounded-t-xl border border-b-0 border-white/10 bg-gradient-to-r from-[#FF1F8E] to-[#A24EFF] px-4 py-2.5 text-sm font-bold text-white shadow-2xl transition-transform hover:-translate-y-0.5 md:right-6" data-testid="label-chat-toggle">
          <MessageCircle className="h-4 w-4" /> Chat Support
          {unread > 0 && <span className="grid h-5 min-w-5 place-items-center rounded-full bg-white px-1.5 text-[11px] font-bold text-[#FF1F8E]" data-testid="label-chat-unread">{unread > 99 ? "99+" : unread}</span>}
        </button>
      )}
    </>
  );
}
