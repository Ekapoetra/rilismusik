import { useState } from "react";
import { api, formatApiError } from "@/api/client";

const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

export function useRoyaltyImportReplacement(oldImport, onCompleted) {
  const [file, setFile] = useState(null);
  const [rate, setRate] = useState(oldImport?.exchange_rate_eur_idr || 17500);
  const [note, setNote] = useState("");
  const [stage, setStage] = useState("form");
  const [progress, setProgress] = useState(0);
  const [replacementId, setReplacementId] = useState(null);
  const [previewJob, setPreviewJob] = useState(null);
  const [rows, setRows] = useState([]);
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const pollImport = async (id) => {
    while (true) {
      const response = await api.get(`/royalty/admin/imports/${oldImport.id}/replacement/${id}/status`);
      const current = response.data;
      setProgress(current.progress_pct || 0);
      if (current.status === "replacement_preview") return current;
      if (current.status === "error") throw new Error(current.error_message || "Pemrosesan file pengganti gagal");
      await wait(2000);
    }
  };

  const pollJob = async (jobId) => {
    while (true) {
      const response = await api.get(`/royalty/admin/imports/replacement/jobs/${jobId}`);
      const current = response.data;
      if (current.status === "done") return current;
      if (current.status === "error") throw new Error(current.error_message || "Proses penggantian gagal");
      await wait(1800);
    }
  };

  const uploadToR2 = (payload) => new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", payload.upload_url); xhr.setRequestHeader("Content-Type", payload.content_type);
    xhr.upload.onprogress = (event) => event.lengthComputable && setProgress(Math.round((event.loaded / event.total) * 100));
    xhr.onload = () => xhr.status >= 200 && xhr.status < 300 ? resolve() : reject(new Error(`Upload gagal (${xhr.status})`));
    xhr.onerror = () => reject(new Error("Koneksi upload terputus")); xhr.send(file);
  });

  const createPreview = async (id) => {
    setStage("previewing");
    const started = await api.post(`/royalty/admin/imports/${oldImport.id}/replacement/${id}/preview`);
    const job = await pollJob(started.data.job_id); setPreviewJob(job);
    const result = await api.get(`/royalty/admin/imports/replacement/jobs/${job.id}/rows`, { params: { limit: 500 } });
    setRows(result.data.items || []); setStage("preview");
  };

  const submit = async (event) => {
    event.preventDefault(); setError("");
    if (!file) { setError("Pilih file CSV pengganti"); return; }
    setBusy(true);
    try {
      setStage("uploading"); setProgress(0);
      const initiated = await api.post(`/royalty/admin/imports/${oldImport.id}/replacement/initiate`, {
        filename: file.name, size_bytes: file.size, rate_eur_idr: Number(rate), note: note || null,
      });
      const id = initiated.data.replacement_import_id; setReplacementId(id);
      await uploadToR2(initiated.data);
      setStage("processing"); setProgress(0);
      await api.post(`/royalty/admin/imports/${oldImport.id}/replacement/${id}/finalize`);
      await pollImport(id); await createPreview(id);
    } catch (requestError) {
      setError(formatApiError(requestError.response?.data?.detail || requestError.message)); setStage("form");
    } finally { setBusy(false); }
  };

  const commit = async () => {
    setError(""); setBusy(true); setStage("committing");
    try {
      const started = await api.post(`/royalty/admin/imports/${oldImport.id}/replacement/${replacementId}/commit`, {
        preview_job_id: previewJob.id, confirmation,
      });
      const job = await pollJob(started.data.job_id); setStage("done");
      onCompleted?.(job.result?.replacement_import_id);
    } catch (requestError) {
      setError(formatApiError(requestError.response?.data?.detail || requestError.message)); setStage("preview");
    } finally { setBusy(false); }
  };

  const cancel = async () => {
    if (replacementId) await api.delete(`/royalty/admin/imports/${oldImport.id}/replacement/${replacementId}`);
  };

  return { file, setFile, rate, setRate, note, setNote, stage, progress, previewJob, rows, confirmation, setConfirmation, error, busy, replacementId, submit, commit, cancel };
}