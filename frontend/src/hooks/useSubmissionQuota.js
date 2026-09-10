import { useCallback, useEffect, useState } from "react";
import { api } from "@/api/client";

export const useSubmissionQuota = (releaseId, enabled = true) => {
  const [quota, setQuota] = useState(null); const [error, setError] = useState(false);
  const reload = useCallback(async () => {
    if (!enabled) return;
    try { const { data } = await api.get("/releases/submission-quota", { params: releaseId ? { release_id: releaseId } : {} }); setQuota(data); setError(false); }
    catch { setError(true); }
  }, [releaseId, enabled]);
  useEffect(() => {
    if (!enabled) return;
    reload(); const interval = setInterval(reload, 30000); window.addEventListener("focus", reload);
    return () => { clearInterval(interval); window.removeEventListener("focus", reload); };
  }, [reload, enabled]);
  return { quota, error, reload, blocked: quota?.remaining === 0 && !quota?.already_counted };
};