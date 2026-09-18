import React, { useEffect, useState } from "react";
import { MessageCircle } from "lucide-react";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

export const OPEN_CHAT_EVENT = "rilismusik:open-chat";
export const CHAT_UNREAD_EVENT = "rilismusik:chat-unread";

export const QuickChatButton = ({ instance = "admin" }) => {
  const { t } = useAppPreferences();
  const [unread, setUnread] = useState(0);
  useEffect(() => {
    const onUnread = (e) => setUnread(Number(e.detail || 0));
    window.addEventListener(CHAT_UNREAD_EVENT, onUnread);
    return () => window.removeEventListener(CHAT_UNREAD_EVENT, onUnread);
  }, []);
  return (
    <button
      type="button"
      onClick={() => window.dispatchEvent(new CustomEvent(OPEN_CHAT_EVENT))}
      className="ui-icon-button relative"
      title={t("Chat")}
      aria-label={t("Chat")}
      data-testid={`quick-chat-button-${instance}`}
    >
      <MessageCircle className="h-5 w-5" />
      {unread > 0 && (
        <span className="absolute -right-1 -top-1 grid h-[18px] min-w-[18px] place-items-center rounded-full bg-[#FF1F8E] px-1 text-[10px] font-bold text-white" data-testid={`quick-chat-unread-${instance}`}>
          {unread > 99 ? "99+" : unread}
        </span>
      )}
    </button>
  );
};
