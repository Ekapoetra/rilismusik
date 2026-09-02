import { useEffect, useRef, useState } from "react";
import { api, formatApiError } from "@/api/client";

const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

export function useRoyaltyDuplicateAudit() {
  const [job, setJob] = useState(null);
  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [warning, setWarning] = useState("");
  const mounted = useRef(true);

  useEffect(() => () => { mounted.current = false; }, []);

  const loadRows = async (jobId) => {
    const response = await api.get(`/royalty/admin/duplicate-audit/jobs/${jobId}/rows`, { params: { limit: 100 } });
    if (mounted.current) setRows(response.data.items || []);
  };

  const poll = async (jobId) => {
    const deadline = Date.now() + (15 * 60 * 1000);
    while (mounted.current) {
      if (Date.now() > deadline) throw new Error("Audit belum selesai setelah 15 menit. Proses dapat dilanjutkan dari pekerjaan yang sama.");
      try {
        const response = await api.get(`/royalty/admin/duplicate-audit/jobs/${jobId}`, { timeout: 15000 });
        const current = response.data;
        if (mounted.current) { setJob(current); setWarning(""); }
        if (current.status === "done") { await loadRows(jobId); return; }
        if (current.status === "error") {
          const terminalError = new Error(current.error_message || "Audit duplikat gagal");
          terminalError.terminal = true;
          throw terminalError;
        }
      } catch (requestError) {
        if (requestError.terminal) throw requestError;
        if (requestError.response?.status === 404) throw requestError;
        if (mounted.current) setWarning("Koneksi pemantauan sempat terputus. Audit tetap berjalan dan akan diperiksa kembali.");
      }
      await wait(1500);
    }
  };

  const start = async () => {
    setBusy(true); setError(""); setWarning(""); setRows([]);
    try {
      const response = await api.post("/royalty/admin/duplicate-audit/preview");
      setJob({ id: response.data.job_id, status: response.data.status || "queued", phase: "menunggu_proses", progress_groups_done: 0, progress_groups_total: 0 });
      await poll(response.data.job_id);
    } catch (requestError) {
      setError(formatApiError(requestError.response?.data?.detail || requestError.message));
    } finally {
      if (mounted.current) setBusy(false);
    }
  };

  return { job, rows, busy, error, warning, start };
}