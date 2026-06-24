import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bell, CheckCheck, Inbox } from "lucide-react";
import { api } from "@/api/client";

const POLL_INTERVAL_MS = 30_000;

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

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const navigate = useNavigate();
  const wrapRef = useRef(null);

  const load = async () => {
    try {
      const { data } = await api.get("/notifications/me", { params: { limit: 15 } });
      setItems(data.items || []);
      setUnread(data.unread_count || 0);
    } catch (_) { /* silent */ }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, POLL_INTERVAL_MS);
    return () => clearInterval(t);
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
    } catch (_) { /* silent */ }
  };

  return (
    <div ref={wrapRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="relative p-2 rounded-xl text-zinc-300 hover:text-white hover:bg-white/5 transition"
        data-testid="notification-bell-button"
        aria-label="Notifikasi"
      >
        <Bell className="w-5 h-5" />
        {unread > 0 && (
          <span
            className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 grid place-items-center text-[10px] font-bold rounded-full text-white"
            style={{ background: "linear-gradient(135deg, #FF1F8E, #A24EFF)" }}
            data-testid="notification-bell-badge"
          >
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div
          className="absolute right-0 top-full mt-2 w-[360px] max-w-[92vw] z-50 rm-glass-strong rounded-2xl overflow-hidden shadow-2xl border border-white/5"
          data-testid="notification-dropdown"
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
              data-testid="notification-mark-all-button"
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
            ) : items.map((n) => (
              <button
                key={n.id}
                onClick={() => handleClick(n)}
                className={`block w-full text-left px-4 py-3 border-b border-white/5 last:border-0 transition hover:bg-white/5 ${!n.read_at ? "bg-pink-500/[0.04]" : ""}`}
                data-testid={`notification-item-${n.id}`}
              >
                <div className="flex items-start gap-3">
                  {!n.read_at && (
                    <span className="mt-1.5 w-2 h-2 rounded-full flex-shrink-0" style={{ background: "linear-gradient(135deg, #FF1F8E, #A24EFF)" }} />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className={`text-sm font-semibold truncate ${!n.read_at ? "text-white" : "text-zinc-300"}`}>{n.title}</div>
                    <div className="text-xs text-zinc-400 line-clamp-2 mt-0.5">{n.body}</div>
                    <div className="text-[10px] text-zinc-600 mt-1">{timeAgo(n.created_at)}</div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
