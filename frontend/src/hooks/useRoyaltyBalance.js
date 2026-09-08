import { useEffect, useState } from "react";
import { api } from "@/api/client";

export const useRoyaltyBalance = (enabled = true) => {
  const [balance, setBalance] = useState(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    let pending = false;
    const refresh = async () => {
      if (pending || document.visibilityState === "hidden") return;
      pending = true;
      try { const { data } = await api.get("/withdraw/label/computed"); if (active) { setBalance(data); setError(false); } }
      catch { if (active) setError(true); }
      finally { pending = false; }
    };
    refresh();
    const timer = setInterval(refresh, 15000);
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => { active = false; clearInterval(timer); window.removeEventListener("focus", refresh); document.removeEventListener("visibilitychange", refresh); };
  }, [enabled]);
  return { balance, error };
};