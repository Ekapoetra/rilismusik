import React, { useCallback, useEffect, useRef, useState } from "react";
import { MessageCircle, X, Users, LifeBuoy, CheckCircle2, Settings, Search, MessagesSquare } from "lucide-react";
import { api } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { toast } from "@/components/ui/sonner";
import { ChatThread, OnlineDot } from "./ChatThread";
import { ChatSettingsPanel } from "./ChatSettingsPanel";
import { uploadChatAttachment } from "./chatUtils";
import { useIncomingChat, NewChatNotice } from "./NewChatNotice";

// Conversation-state filters (NOT presence). Online/Offline is presence and is shown
// only as an indicator dot on each row — never as a conversation filter.
const CONV_FILTERS = [
  { key: "all", id: "Semua", en: "All" },
  { key: "unread", id: "Belum Dibaca", en: "Unread" },
  { key: "active", id: "Aktif", en: "Active" },
  { key: "archived", id: "Arsip", en: "Archived" },
];
const backendStatusFor = (filter) => (filter === "archived" ? "resolved" : filter === "active" ? "active" : "all");

export default function AdminChatWidget() {
  const { user, hasPermission } = useAuth();
  const { t, locale } = useAppPreferences();
  const isSupport = user?.role === "super_admin" || hasPermission?.("support.manage");
  const isSuperAdmin = user?.role === "super_admin";
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState(isSupport ? "label" : "internal");
  const [labelFilter, setLabelFilter] = useState("active");
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
  const openRef = useRef(false);
  const activeRef = useRef(null);
  const labelFilterRef = useRef("active");
  useEffect(() => { openRef.current = open; }, [open]);
  useEffect(() => { activeRef.current = active; }, [active]);
  useEffect(() => { labelFilterRef.current = labelFilter; }, [labelFilter]);

  const loadLists = useCallback(async () => {
    if (isSupport) { try { const { data } = await api.get("/chat/admin/labels", { params: { status: backendStatusFor(labelFilterRef.current) } }); setLabelInbox(data.items || []); } catch { /* */ } }
    // Presence updates only refresh indicators — they NEVER trigger sound/notification.
    try { const { data } = await api.get("/chat/admin/admins"); setAdminDir(data.items || []); } catch { /* */ }
  }, [isSupport]);

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
        receiveChat(data);
        setUnread(data.unread || 0);
      } catch { /* */ }
    }, 4000);
    return () => { clearInterval(hb); clearInterval(poll); };
  }, [receiveChat]);

  useEffect(() => { loadLists(); const timer = setInterval(() => { if (!openRef.current) loadLists(); }, 15000); return () => clearInterval(timer); }, [loadLists]);
  useEffect(() => { if (!open) return; loadLists(); const timer = setInterval(loadLists, 4000); return () => clearInterval(timer); }, [open, loadLists, labelFilter]);
  useEffect(() => { if (!open || !activeConversationId) return; loadThread(); const timer = setInterval(loadThread, 3000); return () => clearInterval(timer); }, [open, activeConversationId, loadThread]);

  const openLabel = (item) => setActive({ conversation_id: item.conversation_id, title: item.label_name, kind: "support", online: item.online, status: item.status });
  const openInternal = async (a) => {
    try { const { data } = await api.post(`/chat/admin/internal/${a.user_id}`); setActive({ conversation_id: data.conversation_id, title: data.title || a.name, kind: "internal", online: a.online }); setMessages(data.messages || []); setTyping([]); }
    catch { toast.error(t("Gagal membuka chat")); }
  };
  const send = async (body, attachment) => {
    setBusy(true);
    try { await api.post(`/chat/admin/thread/${active.conversation_id}`, { body, attachment }); await loadThread(); }
    catch (e) { toast.error(e.response?.data?.detail || t("Gagal mengirim pesan")); }
    finally { setBusy(false); }
  };
  const onType = () => { if (active) api.post("/chat/typing/" + active.conversation_id).catch(() => {}); };
  const onUpload = async (file) => { try { return await uploadChatAttachment(file); } catch (e) { toast.error(e.response?.data?.detail || t("Gagal mengunggah berkas")); return null; } };
  const resolve = async () => {
    if (!active) return;
    try { await api.post(`/chat/admin/thread/${active.conversation_id}/resolve`); toast.success(t("Percakapan ditandai selesai & diarsipkan.")); await loadThread(); await loadLists(); }
    catch (e) { toast.error(e.response?.data?.detail || t("Gagal menyelesaikan")); }
  };

  const supportReadOnly = active?.kind === "support" && isSuperAdmin && !hasPermission?.("support.manage");
  const tr = (o) => (locale === "en" ? o.en : o.id);

  const shownLabels = (() => {
    const q = labelSearch.trim().toLowerCase();
    return labelInbox.filter((it) => {
      const okState = labelFilter === "unread" ? it.unread > 0 : true;
      const okSearch = !q || (it.label_name || "").toLowerCase().includes(q);
      return okState && okSearch;
    });
  })();

  const ListPane = (
    <div className={`min-h-0 w-full flex-col lg:flex lg:w-80 lg:shrink-0 lg:border-r lg:border-white/10 ${active ? "hidden lg:flex" : "flex"}`} data-testid="admin-chat-list-pane">
      <div className="flex border-b border-white/10">
        {isSupport && <button onClick={() => setTab("label")} className={`flex-1 py-2.5 text-xs font-bold uppercase tracking-wide ${tab === "label" ? "bg-white/[0.06] text-white" : "text-zinc-500"}`} data-testid="admin-chat-tab-label"><LifeBuoy className="mr-1 inline h-3.5 w-3.5" /> {t("Label")}</button>}
        <button onClick={() => setTab("internal")} className={`flex-1 py-2.5 text-xs font-bold uppercase tracking-wide ${tab === "internal" ? "bg-white/[0.06] text-white" : "text-zinc-500"}`} data-testid="admin-chat-tab-internal"><Users className="mr-1 inline h-3.5 w-3.5" /> {t("Internal")}</button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {tab === "label" && isSupport && (
          <div className="border-b border-white/5 px-3 py-2 space-y-2">
            <div className="flex flex-wrap gap-1">
              {CONV_FILTERS.map((f) => (
                <button key={f.key} onClick={() => setLabelFilter(f.key)} className={`rounded-full px-3 py-1 text-[11px] font-semibold ${labelFilter === f.key ? "bg-pink-500/15 text-pink-300" : "text-zinc-500 hover:text-white"}`} data-testid={`admin-chat-filter-${f.key}`}>{tr(f)}</button>
              ))}
            </div>
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-600" />
              <input value={labelSearch} onChange={(e) => setLabelSearch(e.target.value)} placeholder={t("Cari nama label…")} className="w-full rounded-lg border border-white/10 bg-black/30 py-1.5 pl-8 pr-3 text-xs text-white placeholder:text-zinc-600 focus:border-white/20 focus:outline-none" data-testid="admin-chat-label-search" />
            </div>
          </div>
        )}
        {tab === "label" && isSupport && (shownLabels.length === 0 ? (
          <div className="p-6 text-center text-xs text-zinc-600" data-testid="admin-chat-label-empty">{labelSearch ? t("Tidak ada label cocok.") : labelFilter === "archived" ? t("Belum ada percakapan diarsipkan.") : labelFilter === "unread" ? t("Tidak ada pesan belum dibaca.") : t("Belum ada percakapan.")}</div>
        ) : shownLabels.map((it) => (
          <button key={it.conversation_id} onClick={() => openLabel(it)} className={`flex w-full items-center gap-3 border-b border-white/5 px-4 py-3 text-left hover:bg-white/[0.04] ${active?.conversation_id === it.conversation_id ? "bg-white/[0.05]" : ""}`} data-testid={`admin-chat-label-item-${it.label_id}`}>
            <OnlineDot online={it.online} />
            <div className="min-w-0 flex-1"><div className="truncate text-sm font-semibold text-white">{it.label_name || t("Label")}{it.status === "resolved" && <span className="ml-1.5 rounded bg-white/10 px-1 py-0.5 text-[9px] uppercase text-zinc-400">{t("Arsip")}</span>}</div><div className="truncate text-[11px] text-zinc-500">{it.last_message_preview || t("Belum ada pesan")}</div></div>
            {it.unread > 0 && <span className="grid h-5 min-w-5 place-items-center rounded-full bg-red-500 px-1.5 text-[11px] font-bold text-white">{it.unread}</span>}
          </button>
        )))}
        {tab === "internal" && (adminDir.length === 0
          ? <div className="p-6 text-center text-xs text-zinc-600">{t("Tidak ada admin lain.")}</div>
          : adminDir.map((a) => (
            <button key={a.user_id} onClick={() => openInternal(a)} className={`flex w-full items-center gap-3 border-b border-white/5 px-4 py-3 text-left hover:bg-white/[0.04] ${active?.conversation_id === a.conversation_id ? "bg-white/[0.05]" : ""}`} data-testid={`admin-chat-admin-item-${a.user_id}`}>
              <OnlineDot online={a.online} />
              <div className="min-w-0 flex-1"><div className="truncate text-sm font-semibold text-white">{a.name}</div><div className="flex items-center gap-1.5 text-[11px] text-zinc-500"><span className={a.online ? "font-semibold text-emerald-400" : "text-zinc-600"}>{a.online ? t("Online") : t("Offline")}</span><span>·</span><span className="truncate">{a.role}</span></div></div>
              {a.unread > 0 && <span className="grid h-5 min-w-5 place-items-center rounded-full bg-red-500 px-1.5 text-[11px] font-bold text-white">{a.unread}</span>}
            </button>
          )))}
      </div>
    </div>
  );

  const DetailPane = (
    <div className={`min-h-0 flex-1 flex-col ${active ? "flex" : "hidden lg:flex"}`} data-testid="admin-chat-detail-pane">
      {active ? (
        <ChatThread
          title={active.title} subtitle={active.kind === "support" ? (active.status === "resolved" ? t("Arsip • Inbox Support") : t("Inbox Support Label")) : t("Chat internal admin")}
          online={active.online} messages={messages} myId={user?.id} onSend={send} busy={busy}
          typing={typing} onType={onType} onUpload={onUpload}
          onBack={() => { setActive(null); setMessages([]); setTyping([]); }}
          disabled={supportReadOnly} disabledText={t("Super Admin memantau. Balasan wajib oleh staff Support.")}
          headerActions={active.kind === "support" && isSupport && active.status !== "resolved" ? (
            <button type="button" onClick={resolve} title={t("Tandai selesai & arsipkan")} className="flex items-center gap-1 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2.5 py-1 text-[11px] font-semibold text-emerald-300 hover:bg-emerald-400/20" data-testid="admin-chat-resolve"><CheckCircle2 className="h-3.5 w-3.5" /> {t("Selesai")}</button>
          ) : null}
        />
      ) : (
        <div className="hidden min-h-0 flex-1 flex-col items-center justify-center gap-2 p-6 text-center text-zinc-600 lg:flex" data-testid="admin-chat-detail-empty">
          <MessagesSquare className="h-8 w-8" /><span className="text-xs">{t("Pilih percakapan untuk mulai.")}</span>
        </div>
      )}
    </div>
  );

  return (
    <>
      {open && (
        <div className="fixed bottom-0 right-4 z-[60] flex h-[74vh] max-h-[600px] w-[92vw] max-w-sm flex-col overflow-hidden rounded-2xl rounded-b-none border border-white/10 bg-[#101010] shadow-2xl md:right-6 lg:h-[72vh] lg:max-w-3xl" data-testid="admin-chat-panel">
          <div className="flex items-center justify-between border-b border-white/10 bg-white/[0.03] px-4 py-3">
            <div className="text-sm font-bold text-white" data-testid="admin-chat-title">{t("Chat")}</div>
            <div className="flex items-center gap-1">
              {isSupport && !showSettings && <button onClick={() => setShowSettings(true)} title={t("Jam operasional & auto-reply")} className="text-zinc-400 hover:text-white" data-testid="admin-chat-settings-open"><Settings className="h-4 w-4" /></button>}
              <button onClick={() => { setOpen(false); setShowSettings(false); }} className="text-zinc-400 hover:text-white" data-testid="admin-chat-close"><X className="h-4 w-4" /></button>
            </div>
          </div>
          {showSettings ? (
            <div className="min-h-0 flex-1"><ChatSettingsPanel onBack={() => setShowSettings(false)} /></div>
          ) : (
            <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
              {ListPane}
              {DetailPane}
            </div>
          )}
        </div>
      )}
      {chatNotice.notice && <NewChatNotice onOpen={chatNotice.showChat} onDismiss={chatNotice.dismiss} />}
      {!open && (
        <button onClick={() => setOpen(true)} className="fixed bottom-0 right-4 z-[60] inline-flex items-center gap-2 rounded-t-xl border border-b-0 border-white/10 bg-gradient-to-r from-[#FF1F8E] to-[#A24EFF] px-4 py-2.5 text-sm font-bold text-white shadow-2xl transition-transform hover:-translate-y-0.5 md:right-6" data-testid="admin-chat-toggle">
          <MessageCircle className="h-4 w-4" /> {t("Chat")}
          {unread > 0 && <span className="grid h-5 min-w-5 place-items-center rounded-full bg-white px-1.5 text-[11px] font-bold text-[#FF1F8E]" data-testid="admin-chat-unread">{unread > 99 ? "99+" : unread}</span>}
        </button>
      )}
    </>
  );
}
