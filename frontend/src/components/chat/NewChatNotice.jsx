import React, { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { MessageCircle, ArrowUpRight, X } from "lucide-react";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { playNotificationSound } from "@/lib/notificationSound";

export const useIncomingChat = (openChat) => {
  const previous = useRef(undefined); const openRef = useRef(openChat); openRef.current = openChat;
  const [notice, setNotice] = useState(null);
  const receive = useCallback((data) => {
    const latest = data.latest_incoming_id || null;
    if (previous.current !== undefined && latest && latest !== previous.current) {
      setNotice(latest); playNotificationSound("chat", `chat:${latest}`);
    }
    previous.current = latest;
  }, []);
  useEffect(() => { if (!notice) return; const timer = setTimeout(() => setNotice(null), 6500); return () => clearTimeout(timer); }, [notice]);
  return { receive, notice, dismiss: () => setNotice(null), showChat: () => { setNotice(null); openRef.current(); } };
};
export const NewChatNotice = ({ onOpen, onDismiss }) => {
  const { t } = useAppPreferences();
  return createPortal(<div className="chat-message-notice flex items-center gap-3 p-4" role="status" aria-live="polite" data-testid="new-chat-notice"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-pink-500/10 text-pink-500"><MessageCircle className="h-5 w-5" /></span><button type="button" onClick={onOpen} className="min-w-0 flex-1 text-left" data-testid="new-chat-notice-open"><span className="block text-sm font-bold" data-testid="new-chat-notice-title">{t("Pesan Chat Baru")}</span><span className="mt-1 inline-flex items-center gap-1 text-xs text-[var(--ui-muted)]">{t("Buka chat")}<ArrowUpRight className="h-3 w-3" /></span></button><button type="button" onClick={onDismiss} aria-label={t("Tutup")} className="p-1 text-[var(--ui-muted)] hover:text-[var(--ui-text)]" data-testid="new-chat-notice-dismiss"><X className="h-4 w-4" /></button></div>, document.body);
};