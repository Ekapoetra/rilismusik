import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bell, CheckCheck, History, Inbox } from "lucide-react";
import { api } from "@/api/client";
import { playNotificationSound } from "@/lib/notificationSound";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

const POLL_INTERVAL_MS = 10_000;

function timeAgo(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "baru saja";
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}j`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}h`;
  return d.toLocaleDateString("id-ID");
}

export default function NotificationBell({ instance = "desktop", historyPath = null }) {
  const { t, locale } = useAppPreferences();
  const known = useRef(null);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const navigate = useNavigate();
  const wrapRef = useRef(null);

  const load = async () => {
    try {
      const { data } = await api.get("/notifications/me", { params: { limit: 25 } });
      const rows = data.items || [];
      if (known.current) { const fresh = rows.find((item) => !known.current.has(item.id) && !item.read_at && !String(item.type || "").includes("chat")); if (fresh) playNotificationSound("notification", `notification:${fresh.id}`); }
      known.current = new Set(rows.map((item) => item.id));
      setItems(data.items || []);
      setUnread(data.unread_count || 0);
    } catch (_) { /* silent */ }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, POLL_INTERVAL_MS);
    const refresh = () => load();
    window.addEventListener("rilismusik:notifications-updated", refresh);
    return () => { clearInterval(t); window.removeEventListener("rilismusik:notifications-updated", refresh); };
  }, []);

  useEffect(() => {
    const onClickOutside = (e) => {
      if (open && wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [open]);

  const handleClick = async (n) => {
    if (!n.read_at) {
      try {
        await api.post(`/notifications/mark-read/${n.id}`);
        setUnread((u) => Math.max(0, u - 1));
        setItems((arr) => arr.map((x) => x.id === n.id ? { ...x, read_at: new Date().toISOString() } : x));
        window.dispatchEvent(new CustomEvent("rilismusik:notifications-updated"));
      } catch (_) { /* silent */ }
    }
    setOpen(false);
    if (n.link) navigate(n.link);
  };

  const markAll = async () => {
    try {
      await api.post("/notifications/mark-all-read");
      setUnread(0);
      setItems((arr) => arr.map((x) => x.read_at ? x : { ...x, read_at: new Date().toISOString() }));
      window.dispatchEvent(new CustomEvent("rilismusik:notifications-updated"));
    } catch (_) { /* silent */ }
  };

  return (
    <div ref={wrapRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="ui-icon-button relative"
        data-testid={instance === "desktop" ? "notification-bell-button" : `notification-bell-button-${instance}`}
        aria-label="Notifikasi"
      >
        <Bell className="w-5 h-5" />
        {unread > 0 && (
          <span
            className="absolute -right-1 -top-1 grid h-[18px] min-w-[18px] place-items-center rounded-full bg-[#FF1F8E] px-1 text-[10px] font-bold text-white"
            data-testid={instance === "desktop" ? "notification-bell-badge" : `notification-bell-badge-${instance}`}
          >
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div
          className="absolute right-0 top-full z-50 mt-2 w-[380px] max-w-[calc(100vw-2rem)] overflow-hidden rounded-lg border border-white/10 bg-[#101010] shadow-2xl"
          data-testid={instance === "desktop" ? "notification-dropdown" : `notification-dropdown-${instance}`}
        >
          <div className="px-4 py-3 flex items-center justify-between border-b border-white/5">
            <div>
              <div className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold">Notifikasi</div>
              <div className="font-display font-extrabold text-sm">{unread} belum dibaca</div>
            </div>
            <button
              onClick={markAll}
              disabled={unread === 0}
              className="text-xs flex items-center gap-1 text-zinc-400 hover:text-white disabled:opacity-40"
              data-testid={instance === "desktop" ? "notification-mark-all-button" : `notification-mark-all-button-${instance}`}
            >
              <CheckCheck className="w-3 h-3" /> Tandai dibaca
            </button>
          </div>
          <div className="max-h-[420px] overflow-y-auto">
            {items.length === 0 ? (
              <div className="p-10 text-center text-zinc-500 text-sm">
                <Inbox className="w-8 h-8 mx-auto mb-2 text-zinc-700" />
                Belum ada notifikasi.
              </div>
            ) : (() => {
              const renderItem = (n) => (
                <button
                  key={n.id}
                  onClick={() => handleClick(n)}
                  className={`block w-full text-left px-4 py-3 border-b border-white/5 last:border-0 transition hover:bg-white/5 ${!n.read_at ? "bg-pink-500/[0.04]" : ""}`}
                  data-testid={`notification-item-${n.id}-${instance}`}
                >
                  <div className="flex items-start gap-3">
                    {(
                      <span className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${n.priority === "urgent" ? "bg-red-500" : n.priority === "important" ? "bg-amber-400" : n.priority === "info" ? "bg-zinc-500" : "bg-[#FF1F8E]"} ${n.read_at ? "opacity-40" : ""}`} />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className={`text-sm font-semibold truncate ${!n.read_at ? "text-white" : "text-zinc-300"}`} data-testid={`notification-title-${n.id}-${instance}`}>{n.type === "chat_message" ? n.title : t(n.title)}</div>
                      <div className="text-xs text-zinc-400 line-clamp-2 mt-0.5" data-testid={`notification-body-${n.id}-${instance}`}>{n.type === "chat_message" ? n.body : t(n.body)}</div>
                      <div className="text-[10px] text-zinc-600 mt-1">{locale === "id" ? timeAgo(n.created_at) : new Date(n.created_at).toLocaleString("en-GB")}{n.stale ? ` · ${t("kedaluwarsa")}` : ""}</div>
                    </div>
                  </div>
                </button>
              );
              const todayStr = new Date().toDateString();
              const today = items.filter((n) => new Date(n.created_at).toDateString() === todayStr).slice(0, 8);
              const todayIds = new Set(today.map((n) => n.id));
              const earlierUnread = items.filter((n) => !todayIds.has(n.id) && !n.read_at).slice(0, 8);
              const SectionHeader = ({ label, testid }) => (
                <div className="sticky top-0 bg-[#101010] px-4 py-1.5 text-[10px] font-bold uppercase tracking-widest text-zinc-500" data-testid={testid}>{label}</div>
              );
              return (
                <>
                  {today.length > 0 && <SectionHeader label={t("Hari Ini")} testid={`notification-section-today-${instance}`} />}
                  {today.length === 0 ? (
                    <div className="px-4 py-6 text-center text-xs text-zinc-600" data-testid={`notification-today-empty-${instance}`}>{t("Belum ada notifikasi hari ini.")}</div>
                  ) : (() => {
                    const byType = {};
                    today.forEach((n) => { (byType[n.type] = byType[n.type] || []).push(n); });
                    const seen = new Set();
                    return today.map((n) => {
                      const list = byType[n.type] || [n];
                      if (list.length >= 3 && n.type !== "chat_message") {
                        if (seen.has(n.type)) return null;
                        seen.add(n.type);
                        const latest = list[0];
                        const unreadCount = list.filter((x) => !x.read_at).length;
                        return (
                          <button key={`grp-${n.type}`} onClick={() => handleClick(latest)} className="block w-full text-left px-4 py-3 border-b border-white/5 transition hover:bg-white/5" data-testid={`notification-group-${n.type}-${instance}`}>
                            <div className="flex items-center gap-3">
                              <span className="grid h-6 min-w-6 place-items-center rounded-full bg-[#FF1F8E] px-1.5 text-[11px] font-bold text-white">{list.length}</span>
                              <div className="min-w-0 flex-1">
                                <div className="truncate text-sm font-semibold text-white">{t(latest.title)}</div>
                                <div className="text-[11px] text-zinc-500">{list.length} {t("serupa")}{unreadCount ? ` · ${unreadCount} ${t("belum dibaca")}` : ""}</div>
                              </div>
                            </div>
                          </button>
                        );
                      }
                      return renderItem(n);
                    });
                  })()}
                  {earlierUnread.length > 0 && <SectionHeader label={t("Sebelumnya · Belum dibaca")} testid={`notification-section-earlier-${instance}`} />}
                  {earlierUnread.map(renderItem)}
                </>
              );
            })()}
          </div>
          {historyPath && <Link to={historyPath} onClick={() => setOpen(false)} className="flex items-center justify-center gap-2 border-t border-white/10 px-4 py-3 text-xs font-bold text-zinc-300 transition-colors hover:bg-white/5 hover:text-white" data-testid={`notification-history-link-${instance}`}><History className="h-3.5 w-3.5" /> Lihat Riwayat Notifikasi</Link>}
        </div>
      )}
    </div>
  );
}
