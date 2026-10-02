import { useEffect, useState } from "react";
import { useAuth } from "@/api/AuthContext";
import { sharedRead } from "@/api/sharedRead";

export const useRoyaltyBalance = (enabled = true, initialBalance) => {
  const { user } = useAuth();
  const [balance, setBalance] = useState(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    if (!enabled) { setBalance(null); return undefined; }
    let active = true;
    let pending = false;
    let lastRead = initialBalance ? Date.now() : 0;
    if (initialBalance) setBalance(initialBalance);
    const refresh = async () => {
      if (pending || document.visibilityState === "hidden" || Date.now() - lastRead < 15000) return;
      pending = true;
      try {
        const { data } = await sharedRead(user?.id, "/withdraw/label/computed");
        if (active) { setBalance(data); setError(false); lastRead = Date.now(); }
      } catch { if (active) setError(true); }
      finally { pending = false; }
    };
    if (!initialBalance) refresh();
    const timer = setInterval(refresh, 15000);
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => { active = false; clearInterval(timer); window.removeEventListener("focus", refresh); document.removeEventListener("visibilitychange", refresh); };
  }, [enabled, initialBalance, user?.id]);
  return { balance, error };
};
