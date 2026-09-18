import React, { useCallback, useEffect, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import { api } from "@/api/client";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel } from "@/components/ui/dropdown-menu";

const IDLE_MS = 5 * 60 * 1000; // auto-idle after 5 minutes of inactivity
const PIN_KEY = "rm-presence-pin"; // "idle" when manually pinned idle

const META = {
  online: { label: "Online", dot: "bg-emerald-400", ring: "ring-emerald-400/40" },
  idle: { label: "Idle", dot: "bg-amber-400", ring: "ring-amber-400/40" },
};

export const StatusMenu = ({ instance = "admin" }) => {
  const { t } = useAppPreferences();
  const [pinnedIdle, setPinnedIdle] = useState(() => localStorage.getItem(PIN_KEY) === "idle");
  const [autoIdle, setAutoIdle] = useState(false);
  const timerRef = useRef(null);
  const status = pinnedIdle || autoIdle ? "idle" : "online";
  const meta = META[status];

  // Auto-idle detection: reset the timer on real user activity.
  useEffect(() => {
    if (pinnedIdle) return undefined;
    const arm = () => {
      setAutoIdle(false);
      clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setAutoIdle(true), IDLE_MS);
    };
    const events = ["mousemove", "mousedown", "keydown", "touchstart", "scroll", "focus"];
    events.forEach((e) => window.addEventListener(e, arm, { passive: true }));
    arm();
    return () => { events.forEach((e) => window.removeEventListener(e, arm)); clearTimeout(timerRef.current); };
  }, [pinnedIdle]);

  // Report presence status to the backend (best-effort, non-blocking).
  const report = useCallback((s) => { api.post("/chat/heartbeat", { status: s }).catch(() => {}); }, []);
  useEffect(() => { report(status); const iv = setInterval(() => report(status), 25000); return () => clearInterval(iv); }, [status, report]);

  const pick = (value) => {
    if (value === "idle") { setPinnedIdle(true); localStorage.setItem(PIN_KEY, "idle"); }
    else { setPinnedIdle(false); localStorage.removeItem(PIN_KEY); setAutoIdle(false); }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button type="button" className={`ui-icon-button w-auto gap-1.5 px-2.5 ring-1 ${meta.ring}`} title={t("Status")} aria-label={t("Status")} data-testid={`status-menu-${instance}`}>
          <span className={`h-2.5 w-2.5 rounded-full ${meta.dot}`} data-testid={`status-dot-${instance}`} />
          <span className="hidden text-[11px] font-bold sm:inline" data-testid={`status-current-${instance}`}>{t(meta.label)}</span>
          <ChevronDown className="h-3 w-3 opacity-60" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="ui-menu w-44" align="end" data-testid={`status-dropdown-${instance}`}>
        <DropdownMenuLabel>{t("Status")}</DropdownMenuLabel>
        {["online", "idle"].map((value) => (
          <DropdownMenuItem key={value} onSelect={() => pick(value)} data-testid={`status-option-${value}-${instance}`}>
            <span className={`mr-2 h-2.5 w-2.5 rounded-full ${META[value].dot}`} />
            {t(META[value].label)}
            {status === value && <Check className="ml-auto h-3.5 w-3.5" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};
