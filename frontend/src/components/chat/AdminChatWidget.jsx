import React, { useCallback, useEffect, useRef, useState } from "react";
import { MessageCircle, X, Users, LifeBuoy } from "lucide-react";
import { api } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { toast } from "@/components/ui/sonner";
import { ChatThread, OnlineDot } from "./ChatThread";
import { playChatSound } from "./chatUtils";

export default function AdminChatWidget() {
  const { user, hasPermission } = useAuth();
  const isSupport = user?.role === "super_admin" || hasPermission?.("support.manage");
  const isSuperAdmin = user?.role === "super_admin";
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState(isSupport ? "label" : "internal");
  const [labelInbox, setLabelInbox] = useState([]);
  const [adminDir, setAdminDir] = useState([]);
  const [active, setActive] = useState(null);
  const [messages, setMessages] = useState([]);
  const [unread, setUnread] = useState(0);
  const [busy, setBusy] = useState(false);
  const prevUnread = useRef(0);
  const openRef = useRef(false);
  const activeRef = useRef(null);
  useEffect(() => { openRef.current = open; }, [open]);
  useEffect(() => { activeRef.current = active; }, [active]);

  const loadLists = useCallback(async () => {
    if (isSupport) { try { const { data } = await api.get("/chat/admin/labels"); setLabelInbox(data.items || []); } catch { /* */ } }
    try { const { data } = await api.get("/chat/admin/admins"); setAdminDir(data.items || []); } catch { /* */ }
  }, [isSupport]);

  const loadThread = useCallback(async () => {
    const cur = activeRef.current;
    if (!cur) return;
    try {
      const { data } = await api.get(`/chat/admin/thread/${cur.conversation_id}`);
      setMessages(data.messages || []);
      setActive((a) => a && a.conversation_id === cur.conversation_id ? { ...a, online: data.online, title: data.label_name || a.title } : a);
    } catch { /* */ }
  }, []);

  useEffect(() => {
    const beat = () => api.post("/chat/heartbeat").catch(() => {});
    beat();
    const hb = setInterval(beat, 20000);
    const poll = setInterval(async () => {
      try {
        const { data } = await api.get("/chat/unread");
        const n = data.unread || 0;
        if (n > prevUnread.current && !openRef.current) { playChatSound(); toast.message("Pesan chat baru"); }
        prevUnread.current = n;
        setUnread(n);
      } catch { /* */ }
    }, 4000);
    return () => { clearInterval(hb); clearInterval(poll); };
  }, []);

  useEffect(() => {
    if (!open) return;
    loadLists();
    const t = setInterval(loadLists, 4000);
    return () => clearInterval(t);
  }, [open, loadLists]);

  useEffect(() => {
    if (!open || !active) return;
    loadThread();
    const t = setInterval(loadThread, 3000);
    return () => clearInterval(t);
  }, [open, active, loadThread]);

  const openLabel = (item) => setActive({ conversation_id: item.conversation_id, title: item.label_name, kind: "support", online: item.online });
  const openInternal = async (a) => {
    try { const { data } = await api.post(`/chat/admin/internal/${a.user_id}`); setActive({ conversation_id: data.conversation_id, title: data.title || a.name, kind: "internal", online: a.online }); setMessages(data.messages || []); }
    catch { toast.error("Gagal membuka chat"); }
  };
  const send = async (body) => {
    setBusy(true);
    try { await api.post(`/chat/admin/thread/${active.conversation_id}`, { body }); await loadThread(); }
    catch (e) { toast.error(e.response?.data?.detail || "Gagal mengirim pesan"); }
    finally { setBusy(false); }
  };

  const supportReadOnly = active?.kind === "support" && isSuperAdmin && !hasPermission?.("support.manage");

  return (
    <>
      {open && (
        <div className="fixed bottom-20 right-4 z-[60] flex h-[74vh] max-h-[600px] w-[92vw] max-w-sm flex-col overflow-hidden rounded-2xl border border-white/10 bg-[#101010] shadow-2xl md:bottom-6 md:right-24" data-testid="admin-chat-panel">
          <div className="flex items-center justify-between border-b border-white/10 bg-white/[0.03] px-4 py-3">
            <div className="text-sm font-bold text-white">Pusat Chat</div>
            <button onClick={() => setOpen(false)} className="text-zinc-400 hover:text-white" data-testid="admin-chat-close"><X className="h-4 w-4" /></button>
          </div>
          {active ? (
            <div className="min-h-0 flex-1">
              <ChatThread
                title={active.title} subtitle={active.kind === "support" ? "Inbox Support Label" : "Chat internal admin"}
                online={active.online} messages={messages} myId={user?.id} onSend={send} busy={busy}
                onBack={() => { setActive(null); setMessages([]); }}
                disabled={supportReadOnly} disabledText="Super Admin memantau. Balasan wajib oleh staff Support."
              />
            </div>
          ) : (
            <>
              <div className="flex border-b border-white/10">
                {isSupport && <button onClick={() => setTab("label")} className={`flex-1 py-2.5 text-xs font-bold uppercase tracking-wide ${tab === "label" ? "bg-white/[0.06] text-white" : "text-zinc-500"}`} data-testid="admin-chat-tab-label"><LifeBuoy className="mr-1 inline h-3.5 w-3.5" /> Label</button>}
                <button onClick={() => setTab("internal")} className={`flex-1 py-2.5 text-xs font-bold uppercase tracking-wide ${tab === "internal" ? "bg-white/[0.06] text-white" : "text-zinc-500"}`} data-testid="admin-chat-tab-internal"><Users className="mr-1 inline h-3.5 w-3.5" /> Internal</button>
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto">
                {tab === "label" && isSupport && (labelInbox.length === 0
                  ? <div className="p-6 text-center text-xs text-zinc-600">Belum ada percakapan label.</div>
                  : labelInbox.map((it) => (
                    <button key={it.conversation_id} onClick={() => openLabel(it)} className="flex w-full items-center gap-3 border-b border-white/5 px-4 py-3 text-left hover:bg-white/[0.04]" data-testid={`admin-chat-label-item-${it.label_id}`}>
                      <OnlineDot online={it.online} />
                      <div className="min-w-0 flex-1"><div className="truncate text-sm font-semibold text-white">{it.label_name || "Label"}</div><div className="truncate text-[11px] text-zinc-500">{it.last_message_preview || "Belum ada pesan"}</div></div>
                      {it.unread > 0 && <span className="grid h-5 min-w-5 place-items-center rounded-full bg-red-500 px-1.5 text-[11px] font-bold text-white">{it.unread}</span>}
                    </button>
                  )))}
                {tab === "internal" && (adminDir.length === 0
                  ? <div className="p-6 text-center text-xs text-zinc-600">Tidak ada admin lain.</div>
                  : adminDir.map((a) => (
                    <button key={a.user_id} onClick={() => openInternal(a)} className="flex w-full items-center gap-3 border-b border-white/5 px-4 py-3 text-left hover:bg-white/[0.04]" data-testid={`admin-chat-admin-item-${a.user_id}`}>
                      <OnlineDot online={a.online} />
                      <div className="min-w-0 flex-1"><div className="truncate text-sm font-semibold text-white">{a.name}</div><div className="truncate text-[11px] text-zinc-500">{a.role}</div></div>
                      {a.unread > 0 && <span className="grid h-5 min-w-5 place-items-center rounded-full bg-red-500 px-1.5 text-[11px] font-bold text-white">{a.unread}</span>}
                    </button>
                  )))}
              </div>
            </>
          )}
        </div>
      )}
      <button onClick={() => setOpen((v) => !v)} className="fixed bottom-6 right-6 z-[60] grid h-14 w-14 place-items-center rounded-full bg-gradient-to-br from-[#FF1F8E] to-[#A24EFF] text-white shadow-2xl transition-transform hover:scale-105" data-testid="admin-chat-toggle">
        {open ? <X className="h-6 w-6" /> : <MessageCircle className="h-6 w-6" />}
        {!open && unread > 0 && <span className="absolute -right-1 -top-1 grid h-6 min-w-6 place-items-center rounded-full bg-red-500 px-1.5 text-xs font-bold text-white" data-testid="admin-chat-unread">{unread > 99 ? "99+" : unread}</span>}
      </button>
    </>
  );
}
