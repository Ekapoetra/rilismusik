import { useEffect, useState } from "react";
import { formatApiError, useAuth } from "@/api/AuthContext";
import { sharedRead } from "@/api/sharedRead";

export function useLabelAnalytics({ enabled = true, windowValue: fixedWindow, labelId: fixedLabel } = {}) {
  const { user } = useAuth();
  const [selectedWindow, setWindowValue] = useState("6");
  const [selectedLabel, setLabelId] = useState("all");
  const windowValue = fixedWindow ?? selectedWindow;
  const labelId = fixedLabel ?? selectedLabel;
  const [result, setResult] = useState({ data: null, key: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const key = JSON.stringify([user?.id, user?.active_label_id, labelId, windowValue]);
  useEffect(() => {
    if (!enabled) { setLoading(false); return undefined; }
    let active = true;
    setLoading(true); setError("");
    const params = { window: windowValue };
    if (labelId && labelId !== "all") params.label_id = labelId;
    sharedRead(JSON.stringify([user?.id, user?.active_label_id]), "/label/analytics", params)
      .then((response) => { if (active) setResult({ data: response.data, key }); })
      .catch((requestError) => { if (active) setError(formatApiError(requestError.response?.data?.detail || requestError.message)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [enabled, windowValue, labelId, user?.id, user?.active_label_id, key]);
  return { data: result.key === key ? result.data : null, loading, error, windowValue, setWindowValue, labelId, setLabelId };
}
