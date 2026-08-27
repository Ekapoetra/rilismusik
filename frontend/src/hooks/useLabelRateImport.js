import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/api/client";
import { formatApiError } from "@/api/AuthContext";

export function useLabelRateImport() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [job, setJob] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [statusFilter, setStatusFilter] = useState("all");
  const timerRef = useRef(null);

  useEffect(() => () => timerRef.current && clearInterval(timerRef.current), []);

  const visibleRows = useMemo(() => {
    const rows = preview?.rows || [];
    return (statusFilter === "all" ? rows : rows.filter((row) => row.status === statusFilter)).slice(0, 250);
  }, [preview, statusFilter]);

  const createPreview = async () => {
    if (!file) { setError("Pilih file XLSX atau CSV terlebih dahulu."); return; }
    setBusy(true); setError(""); setPreview(null); setJob(null); setConfirmed(false);
    try {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post("/admin/labels/rate-import/preview", form, {
        headers: { "Content-Type": "multipart/form-data" }, timeout: 60000,
      });
      setPreview(data);
    } catch (requestError) {
      setError(formatApiError(requestError.response?.data?.detail || requestError.message));
    } finally { setBusy(false); }
  };

  const pollJob = (jobId) => {
    if (timerRef.current) clearInterval(timerRef.current);
    const check = async () => {
      try {
        const { data } = await api.get(`/admin/labels/rate-import/jobs/${jobId}`);
        setJob(data);
        if (["done", "done_with_errors", "error"].includes(data.status)) {
          clearInterval(timerRef.current);
          timerRef.current = null;
          setBusy(false);
          if (data.status === "error") setError(data.error_message || "Sinkronisasi gagal");
        }
      } catch (requestError) {
        clearInterval(timerRef.current);
        timerRef.current = null;
        setBusy(false);
        setError(formatApiError(requestError.response?.data?.detail || requestError.message));
      }
    };
    timerRef.current = setInterval(check, 2500);
    check();
  };

  const commit = async () => {
    if (!preview?.batch_id || !confirmed) return;
    setBusy(true); setError("");
    try {
      const { data } = await api.post("/admin/labels/rate-import/commit", {
        batch_id: preview.batch_id,
        reason: `Sinkronisasi rate dari ${preview.filename}`,
      });
      setJob({ job_id: data.job_id, status: data.status, progress_labels_done: 0, progress_labels_total: preview.summary.will_update });
      pollJob(data.job_id);
    } catch (requestError) {
      setBusy(false);
      setError(formatApiError(requestError.response?.data?.detail || requestError.message));
    }
  };

  const reset = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
    setFile(null); setPreview(null); setJob(null); setError(""); setConfirmed(false); setStatusFilter("all"); setBusy(false);
  };

  return {
    file, setFile, preview, job, busy, error, confirmed, setConfirmed,
    statusFilter, setStatusFilter, visibleRows, createPreview, commit, reset,
  };
}