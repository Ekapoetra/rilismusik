import React, { useCallback, useEffect, useRef, useState } from "react";
import { MessageCircle, X, Users, LifeBuoy, CheckCircle2, Settings, Search } from "lucide-react";
import { api } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { toast } from "@/components/ui/sonner";
import { ChatThread, OnlineDot } from "./ChatThread";
import { ChatSettingsPanel } from "./ChatSettingsPanel";
import { uploadChatAttachment } from "./chatUtils";
import { useIncomingChat, NewChatNotice } from "./NewChatNotice";
import { playNotificationSound } from "@/lib/notificationSound";

export default function AdminChatWidget() {
  const { user, hasPermission } = useAuth();
  const isSupport = user?.role === "super_admin" || hasPermission?.("support.manage");
  const isSuperAdmin = user?.role === "super_admin";
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState(isSupport ? "label" : "internal");
  const [labelFilter, setLabelFilter] = useState("online");
  const [labelSearch, setLabelSearch] = useState("");
  const [labelInbox, setLabelInbox] = useState([]);
  const [adminDir, setAdminDir] = useState([]);
  const [active, setActive] = useState(null);
  const activeConversationId = active?.conversation_id;
  const [showSettings, setShowSettings] = useState(false);
  const [messages, setMessages] = useState([]);
  const [typing, setTyping] = useState([]);
  const [unread, setUnread] = useState(0);
  const [busy, setBusy] = useState(false);
  const chatNotice = useIncomingChat(() => setOpen(true));
  const receiveChat = chatNotice.receive;
  const previousOnline = useRef(null);
  const openRef = useRef(false);
  const activeRef = useRef(null);
  const labelFilterRef = useRef("online");
  useEffect(() => { openRef.current = open; }, [open]);
  useEffect(() => { activeRef.current = active; }, [active]);
  useEffect(() => { labelFilterRef.current = labelFilter; }, [labelFilter]);

  const loadLists = useCallback(async () => {
    if (isSupport) { try { const backendStatus = labelFilterRef.current === "resolved" ? "resolved" : "active"; const { data } = await api.get("/chat/admin/labels", { params: { status: backendStatus } }); setLabelInbox(data.items || []); } catch { /* */ } }
    try { const { data } = await api.get("/chat/admin/admins"); const rows = data.items || []; const online = new Set(rows.filter((item) => item.online && item.user_id !== user?.id).map((item) => item.user_id)); if (previousOnline.current) { const arrival = [...online].find((id) => !previousOnline.current.has(id)); if (arrival) playNotificationSound("online", `online:${arrival}:${Date.now()}`); } previousOnline.current = online; setAdminDir(rows); } catch { /* */ }
  }, [isSupport, user?.id]);

  const loadThread = useCallback(async () => {
    const cur = activeRef.current;
    if (!cur) return;
    try {
      const { data } = await api.get(`/chat/admin/thread/${cur.conversation_id}`);
      setMessages(data.messages || []);
      setTyping(data.typing || []);
      setActive((a) => a && a.conversation_id === cur.conversation_id ? { ...a, online: data.online, status: data.status, title: data.label_name || a.title } : a);
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
        receiveChat(data);
        setUnread(n);
      } catch { /* */ }
    }, 4000);
    return () => { clearInterval(hb); clearInterval(poll); };
  }, [receiveChat]);

  useEffect(() => { loadLists(); const timer = setInterval(() => { if (!openRef.current) loadLists(); }, 15000); return () => clearInterval(timer); }, [loadLists]);

  useEffect(() => {
    if (!open) return;
    loadLists();
    const t = setInterval(loadLists, 4000);
    return () => clearInterval(t);
  }, [open, loadLists, labelFilter]);

  useEffect(() => {
    if (!open || !activeConversationId) return;
    loadThread();
    const t = setInterval(loadThread, 3000);
    return () => clearInterval(t);
  }, [open, activeConversationId, loadThread]);

  const openLabel = (item) => setActive({ conversation_id: item.conversation_id, title: item.label_name, kind: "support", online: item.online, status: item.status });
  const openInternal = async (a) => {
    try { const { data } = await api.post(`/chat/admin/internal/${a.user_id}`); setActive({ conversation_id: data.conversation_id, title: data.title || a.name, kind: "internal", online: a.online }); setMessages(data.messages || []); setTyping([]); }
    catch { toast.error("Gagal membuka chat"); }
  };
  const send = async (body, attachment) => {
    setBusy(true);
    try { await api.post(`/chat/admin/thread/${active.conversation_id}`, { body, attachment }); await loadThread(); }
    catch (e) { toast.error(e.response?.data?.detail || "Gagal mengirim pesan"); }
    finally { setBusy(false); }
  };
  const onType = () => { if (active) api.post("/chat/typing/" + active.conversation_id).catch(() => {}); };
  const onUpload = async (file) => {
    try { return await uploadChatAttachment(file); }
    catch (e) { toast.error(e.response?.data?.detail || "Gagal mengunggah berkas"); return null; }
  };
  const resolve = async () => {
    if (!active) return;
    try { await api.post(`/chat/admin/thread/${active.conversation_id}/resolve`); toast.success("Percakapan ditandai selesai & diarsipkan."); await loadThread(); await loadLists(); }
    catch (e) { toast.error(e.response?.data?.detail || "Gagal menyelesaikan"); }
  };

  const supportReadOnly = active?.kind === "support" && isSuperAdmin && !hasPermission?.("support.manage");

  return (
    <>
      {open && (
        <div className="fixed bottom-20 right-4 z-[60] flex h-[74vh] max-h-[600px] w-[92vw] max-w-sm flex-col overflow-hidden rounded-2xl border border-white/10 bg-[#101010] shadow-2xl md:bottom-6 md:right-24" data-testid="admin-chat-panel">
          <div className="flex items-center justify-between border-b border-white/10 bg-white/[0.03] px-4 py-3">
            <div className="text-sm font-bold text-white">Pusat Chat</div>
            <div className="flex items-center gap-1">
              {isSupport && !active && !showSettings && <button onClick={() => setShowSettings(true)} title="Jam operasional & auto-reply" className="text-zinc-400 hover:text-white" data-testid="admin-chat-settings-open"><Settings className="h-4 w-4" /></button>}
              <button onClick={() => { setOpen(false); setShowSettings(false); }} className="text-zinc-400 hover:text-white" data-testid="admin-chat-close"><X className="h-4 w-4" /></button>
            </div>
          </div>
          {showSettings ? (
            <div className="min-h-0 flex-1"><ChatSettingsPanel onBack={() => setShowSettings(false)} /></div>
          ) : active ? (
            <div className="min-h-0 flex-1">
              <ChatThread
                title={active.title} subtitle={active.kind === "support" ? (active.status === "resolved" ? "Arsip • Inbox Support" : "Inbox Support Label") : "Chat internal admin"}
                online={active.online} messages={messages} myId={user?.id} onSend={send} busy={busy}
                typing={typing} onType={onType} onUpload={onUpload}
                onBack={() => { setActive(null); setMessages([]); setTyping([]); }}
                disabled={supportReadOnly} disabledText="Super Admin memantau. Balasan wajib oleh staff Support."
                headerActions={active.kind === "support" && isSupport && active.status !== "resolved" ? (
                  <button type="button" onClick={resolve} title="Tandai selesai & arsipkan" className="flex items-center gap-1 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2.5 py-1 text-[11px] font-semibold text-emerald-300 hover:bg-emerald-400/20" data-testid="admin-chat-resolve"><CheckCircle2 className="h-3.5 w-3.5" /> Selesai</button>
                ) : null}
              />
            </div>
          ) : (
            <>
              <div className="flex border-b border-white/10">
                {isSupport && <button onClick={() => setTab("label")} className={`flex-1 py-2.5 text-xs font-bold uppercase tracking-wide ${tab === "label" ? "bg-white/[0.06] text-white" : "text-zinc-500"}`} data-testid="admin-chat-tab-label"><LifeBuoy className="mr-1 inline h-3.5 w-3.5" /> Label</button>}
                <button onClick={() => setTab("internal")} className={`flex-1 py-2.5 text-xs font-bold uppercase tracking-wide ${tab === "internal" ? "bg-white/[0.06] text-white" : "text-zinc-500"}`} data-testid="admin-chat-tab-internal"><Users className="mr-1 inline h-3.5 w-3.5" /> Internal</button>
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto">
                {tab === "label" && isSupport && (
                  <div className="border-b border-white/5 px-3 py-2 space-y-2">
                    <div className="flex gap-1">
                      <button onClick={() => setLabelFilter("online")} className={`rounded-full px-3 py-1 text-[11px] font-semibold ${labelFilter === "online" ? "bg-emerald-400/15 text-emerald-300" : "text-zinc-500"}`} data-testid="admin-chat-inbox-online">● Online</button>
                      <button onClick={() => setLabelFilter("offline")} className={`rounded-full px-3 py-1 text-[11px] font-semibold ${labelFilter === "offline" ? "bg-white/10 text-white" : "text-zinc-500"}`} data-testid="admin-chat-inbox-offline">Offline</button>
                      <button onClick={() => setLabelFilter("resolved")} className={`rounded-full px-3 py-1 text-[11px] font-semibold ${labelFilter === "resolved" ? "bg-white/10 text-white" : "text-zinc-500"}`} data-testid="admin-chat-inbox-archived">Arsip</button>
                    </div>
                    <div className="relative">
                      <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-600" />
                      <input value={labelSearch} onChange={(e) => setLabelSearch(e.target.value)} placeholder="Cari nama label…" className="w-full rounded-lg border border-white/10 bg-black/30 py-1.5 pl-8 pr-3 text-xs text-white placeholder:text-zinc-600 focus:border-white/20 focus:outline-none" data-testid="admin-chat-label-search" />
                    </div>
                  </div>
                )}
                {tab === "label" && isSupport && (() => {
                  const q = labelSearch.trim().toLowerCase();
                  const shown = labelInbox.filter((it) => {
                    const okStatus = labelFilter === "resolved" ? true : labelFilter === "online" ? it.online : !it.online;
                    const okSearch = !q || (it.label_name || "").toLowerCase().includes(q);
                    return okStatus && okSearch;
                  });
                  if (shown.length === 0) {
                    const emptyText = q ? "Tidak ada label cocok." : labelFilter === "resolved" ? "Belum ada percakapan diarsipkan." : labelFilter === "online" ? "Belum ada label online." : "Belum ada label offline.";
                    return <div className="p-6 text-center text-xs text-zinc-600" data-testid="admin-chat-label-empty">{emptyText}</div>;
                  }
                  return shown.map((it) => (
                    <button key={it.conversation_id} onClick={() => openLabel(it)} className="flex w-full items-center gap-3 border-b border-white/5 px-4 py-3 text-left hover:bg-white/[0.04]" data-testid={`admin-chat-label-item-${it.label_id}`}>
                      <OnlineDot online={it.online} />
                      <div className="min-w-0 flex-1"><div className="truncate text-sm font-semibold text-white">{it.label_name || "Label"}</div><div className="truncate text-[11px] text-zinc-500">{it.last_message_preview || "Belum ada pesan"}</div></div>
                      {it.unread > 0 && <span className="grid h-5 min-w-5 place-items-center rounded-full bg-red-500 px-1.5 text-[11px] font-bold text-white">{it.unread}</span>}
                    </button>
                  ));
                })()}
                {tab === "internal" && (adminDir.length === 0
                  ? <div className="p-6 text-center text-xs text-zinc-600">Tidak ada admin lain.</div>
                  : adminDir.map((a) => (
                    <button key={a.user_id} onClick={() => openInternal(a)} className="flex w-full items-center gap-3 border-b border-white/5 px-4 py-3 text-left hover:bg-white/[0.04]" data-testid={`admin-chat-admin-item-${a.user_id}`}>
                      <OnlineDot online={a.online} />
                      <div className="min-w-0 flex-1"><div className="truncate text-sm font-semibold text-white">{a.name}</div><div className="flex items-center gap-1.5 text-[11px] text-zinc-500"><span className={a.online ? "font-semibold text-emerald-400" : "text-zinc-600"}>{a.online ? "Online" : "Offline"}</span><span>·</span><span className="truncate">{a.role}</span></div></div>
                      {a.unread > 0 && <span className="grid h-5 min-w-5 place-items-center rounded-full bg-red-500 px-1.5 text-[11px] font-bold text-white">{a.unread}</span>}
                    </button>
                  )))}
              </div>
            </>
          )}
        </div>
      )}
      {chatNotice.notice && <NewChatNotice onOpen={chatNotice.showChat} onDismiss={chatNotice.dismiss} />}
      <button onClick={() => setOpen((v) => !v)} className="fixed bottom-6 right-6 z-[60] grid h-14 w-14 place-items-center rounded-full bg-gradient-to-br from-[#FF1F8E] to-[#A24EFF] text-white shadow-2xl transition-transform hover:scale-105" data-testid="admin-chat-toggle">
        {open ? <X className="h-6 w-6" /> : <MessageCircle className="h-6 w-6" />}
        {!open && unread > 0 && <span className="absolute -right-1 -top-1 grid h-6 min-w-6 place-items-center rounded-full bg-red-500 px-1.5 text-xs font-bold text-white" data-testid="admin-chat-unread">{unread > 99 ? "99+" : unread}</span>}
      </button>
    </>
  );
}
