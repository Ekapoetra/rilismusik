import { useEffect, useMemo, useState } from "react";
import { api, formatApiError } from "@/api/client";

const fmtPeriod = (period) => {
  if (!period || period.length !== 7) return period || "";
  const [year, month] = period.split("-");
  const months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
  return `${months[Number(month) - 1] || month} ${year}`;
};

function defaultRange(periods) {
  if (!periods?.length) return ["", ""];
  const max = periods.at(-1);
  const [year, month] = max.split("-").map(Number);
  const fromDate = new Date(Date.UTC(year, month - 1, 1));
  fromDate.setUTCMonth(fromDate.getUTCMonth() - 11);
  const from = `${fromDate.getUTCFullYear()}-${String(fromDate.getUTCMonth() + 1).padStart(2, "0")}`;
  return [periods.includes(from) ? from : periods[0], max];
}

function analyticsQuery(periodFrom, periodTo, filters = {}) {
  const params = new URLSearchParams({ period_from: periodFrom, period_to: periodTo, top_n: "10" });
  Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, value); });
  return params.toString();
}

export function useAdminAnalytics() {
  const [periods, setPeriods] = useState([]);
  const [periodFrom, setPeriodFrom] = useState("");
  const [periodTo, setPeriodTo] = useState("");
  const [filters, setFilters] = useState({ label_id: "", platform: "", country: "", artist_id: "", track_id: "" });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [cacheStatus, setCacheStatus] = useState(null);

  useEffect(() => {
    let active = true;
    Promise.all([api.get("/admin/analytics/periods"), api.get("/admin/analytics/status")])
      .then(([periodResponse, statusResponse]) => {
        if (!active) return;
        const available = periodResponse.data.periods || [];
        const [from, to] = defaultRange(available);
        setPeriods(available); setPeriodFrom(from); setPeriodTo(to); setCacheStatus(statusResponse.data);
      })
      .catch((error) => active && setErr(`Gagal memuat list periode: ${formatApiError(error.response?.data?.detail || error.message)}`));
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!periodFrom || !periodTo) return undefined;
    let active = true;
    setLoading(true); setErr("");
    api.get(`/admin/analytics/monthly?${analyticsQuery(periodFrom, periodTo, filters)}`)
      .then((response) => active && setData(response.data))
      .catch((error) => active && setErr(`Gagal: ${formatApiError(error.response?.data?.detail || error.message)}`))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [periodFrom, periodTo, filters]);

  useEffect(() => {
    if (!cacheStatus?.running) return undefined;
    let active = true;
    const poll = async () => {
      try {
        const statusResponse = await api.get("/admin/analytics/status");
        if (!active) return;
        const status = statusResponse.data;
        setCacheStatus(status);
        if (!status.running) {
          const periodResponse = await api.get("/admin/analytics/periods");
          if (!active) return;
          const available = periodResponse.data.periods || [];
          const [fallbackFrom, fallbackTo] = defaultRange(available);
          setPeriods(available);
          setPeriodFrom((current) => available.includes(current) ? current : fallbackFrom);
          setPeriodTo(fallbackTo);
          setRefreshing(false);
        }
      } catch (error) {
        if (active) {
          setErr(`Status rebuild gagal dibaca: ${formatApiError(error.response?.data?.detail || error.message)}`);
          setRefreshing(false);
        }
      }
    };
    poll();
    const timer = setInterval(poll, 3000);
    return () => { active = false; clearInterval(timer); };
  }, [cacheStatus?.running]);

  const recompute = async () => {
    setRefreshing(true); setErr("");
    try {
      const response = await api.post("/admin/analytics/recompute");
      setCacheStatus(response.data.meta);
    } catch (error) {
      setErr(`Recompute gagal: ${formatApiError(error.response?.data?.detail || error.message)}`);
      setRefreshing(false);
    }
  };

  const monthlyChart = useMemo(() => (data?.monthly || []).map((row) => ({
    period: row.period, label: fmtPeriod(row.period), EUR: row.revenue_eur, IDR: row.revenue_idr,
  })), [data]);

  return {
    periods, periodFrom, setPeriodFrom, periodTo, setPeriodTo, filters, setFilters,
    data, loading, err, refreshing, cacheStatus, recompute, monthlyChart,
  };
}

export { fmtPeriod };