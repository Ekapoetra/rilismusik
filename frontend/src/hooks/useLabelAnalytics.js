import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { formatApiError } from "@/api/AuthContext";

export function useLabelAnalytics() {
  const [windowValue, setWindowValue] = useState("latest");
  const [labelId, setLabelId] = useState("all");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true); setError("");
    const params = { window: windowValue };
    if (labelId && labelId !== "all") params.label_id = labelId;
    api.get("/label/analytics", { params })
      .then((response) => { if (active) setData(response.data); })
      .catch((requestError) => { if (active) setError(formatApiError(requestError.response?.data?.detail || requestError.message)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [windowValue, labelId]);

  return { data, loading, error, windowValue, setWindowValue, labelId, setLabelId };
}