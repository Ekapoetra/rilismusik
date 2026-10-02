import { useCallback, useEffect, useState } from "react";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";

// Each URL has its own lifecycle. Aborted/old responses cannot overwrite a new
// filter or a newly signed-in user's panel. An error never becomes a zero.
export function useV7Resource(url, pollMs = 0) {
  const { user } = useAuth();
  const identity = `${user?.id || ""}:${user?.role || ""}:${(user?.permissions || []).join(",")}`;
  const requestKey = `${identity}:${url || ""}`;
  const [state, setState] = useState({ key: requestKey, data: null, loading: Boolean(url), error: "" });
  const [version, setVersion] = useState(0);
  const reload = useCallback(() => setVersion((value) => value + 1), []);
  useEffect(() => {
    if (!url) { setState({ key: requestKey, data: null, loading: false, error: "" }); return; }
    const controller = new AbortController();
    setState(previous => ({ key: requestKey, data: previous.key === requestKey ? previous.data : null, loading: true, error: "" }));
    api.get(url, { signal: controller.signal }).then(({ data }) => {
      if (!controller.signal.aborted) setState({ key: requestKey, data, loading: false, error: "" });
    }).catch((error) => {
      if (!controller.signal.aborted) setState({ key: requestKey, data: null, loading: false, error: formatApiError(error.response?.data?.detail) });
    });
    return () => controller.abort();
  }, [url, requestKey, version]);
  useEffect(() => {
    if (!pollMs || !url) return;
    const update = () => { if (!document.hidden) reload(); };
    const timer = setInterval(update, pollMs);
    window.addEventListener("rilismusik:new-notification", update);
    return () => { clearInterval(timer); window.removeEventListener("rilismusik:new-notification", update); };
  }, [pollMs, url, reload]);
  return state.key === requestKey ? { ...state, reload } : { data: null, loading: Boolean(url), error: "", reload };
}
