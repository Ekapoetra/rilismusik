import { useEffect, useState } from "react";
import { useAuth } from "@/api/AuthContext";
import { sharedRead } from "@/api/sharedRead";

// One request per key, including StrictMode/remounts. Hidden tabs do no polling.
export function usePollingRead(url, params = {}, { interval = 15000, enabled = true, refreshEvent } = {}) {
  const { user } = useAuth();
  const key = JSON.stringify([JSON.stringify([user?.id, user?.active_label_id]), url, Object.entries(params).sort()]);
  const [state, setState] = useState({ key: null, data: null, error: false, loading: true });
  useEffect(() => {
    if (!enabled) return undefined;
    let active = true, pending = false;
    const [, requestUrl, entries] = JSON.parse(key);
    const refresh = async () => {
      if (pending || document.visibilityState === "hidden") return;
      pending = true;
      try {
        const { data } = await sharedRead(JSON.stringify([user?.id, user?.active_label_id]), requestUrl, Object.fromEntries(entries));
        if (active) setState({ key, data, error: false, loading: false });
      } catch {
        if (active) setState((value) => ({ key, data: value.key === key ? value.data : null, error: true, loading: false }));
      } finally { pending = false; }
    };
    refresh();
    const timer = interval ? setInterval(refresh, interval) : null;
    document.addEventListener("visibilitychange", refresh);
    if (refreshEvent) window.addEventListener(refreshEvent, refresh);
    return () => {
      active = false; if (timer) clearInterval(timer);
      document.removeEventListener("visibilitychange", refresh);
      if (refreshEvent) window.removeEventListener(refreshEvent, refresh);
    };
  }, [key, enabled, interval, refreshEvent, user?.id, user?.active_label_id]);
  if (!enabled) return { data: null, error: false, loading: false };
  return state.key === key ? state : { data: null, error: false, loading: enabled };
}
