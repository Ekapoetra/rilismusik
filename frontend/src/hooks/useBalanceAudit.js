import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import { formatApiError } from "@/api/AuthContext";

export function useBalanceAudit() {
  const [previewJob, setPreviewJob] = useState(null);
  const [commitJob, setCommitJob] = useState(null);
  const [rows, setRows] = useState([]);
  const [totalRows, setTotalRows] = useState(0);
  const [filter, setFilter] = useState("drift");
  const [search, setSearch] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const timerRef = useRef(null);

  useEffect(() => () => timerRef.current && clearInterval(timerRef.current), []);

  const loadRows = useCallback(async (jobId, nextFilter = filter, nextSearch = search) => {
    if (!jobId) return;
    const { data } = await api.get(`/admin/balance-audit/jobs/${jobId}/rows`, {
      params: { status: nextFilter || undefined, search: nextSearch || undefined, limit: 500 },
    });
    setRows(data.items || []); setTotalRows(data.total || 0);
  }, [filter, search]);

  const poll = (jobId, kind) => {
    if (timerRef.current) clearInterval(timerRef.current);
    const check = async () => {
      try {
        const { data } = await api.get(`/admin/balance-audit/jobs/${jobId}`);
        if (kind === "preview") setPreviewJob(data); else setCommitJob(data);
        if (["done", "done_with_errors", "error"].includes(data.status)) {
          clearInterval(timerRef.current); timerRef.current = null; setBusy(false);
          if (data.status === "error") setError(data.error_message || "Job audit gagal");
          if (kind === "preview" && data.status === "done") await loadRows(jobId);
        }
      } catch (requestError) {
        clearInterval(timerRef.current); timerRef.current = null; setBusy(false);
        setError(formatApiError(requestError.response?.data?.detail || requestError.message));
      }
    };
    timerRef.current = setInterval(check, 2500);
    check();
  };

  const startPreview = async () => {
    setBusy(true); setError(""); setRows([]); setCommitJob(null); setConfirmed(false);
    try {
      const { data } = await api.post("/admin/balance-audit/preview");
      setPreviewJob({ id: data.job_id, status: data.status, phase: "queued" });
      poll(data.job_id, "preview");
    } catch (requestError) {
      setBusy(false); setError(formatApiError(requestError.response?.data?.detail || requestError.message));
    }
  };

  const commit = async () => {
    if (!previewJob?.id || !confirmed) return;
    setBusy(true); setError("");
    try {
      const { data } = await api.post("/admin/balance-audit/commit", { preview_job_id: previewJob.id });
      setCommitJob({ id: data.job_id, status: data.status, phase: "queued" });
      poll(data.job_id, "commit");
    } catch (requestError) {
      setBusy(false); setError(formatApiError(requestError.response?.data?.detail || requestError.message));
    }
  };

  const applyFilter = async (nextFilter) => {
    setFilter(nextFilter);
    try { await loadRows(previewJob?.id, nextFilter, search); }
    catch (requestError) { setError(formatApiError(requestError.response?.data?.detail || requestError.message)); }
  };

  const applySearch = async () => {
    try { await loadRows(previewJob?.id, filter, search); }
    catch (requestError) { setError(formatApiError(requestError.response?.data?.detail || requestError.message)); }
  };

  return {
    previewJob, commitJob, rows, totalRows, filter, search, setSearch,
    confirmed, setConfirmed, busy, error, startPreview, commit, applyFilter, applySearch,
  };
}