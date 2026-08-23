import { useCallback, useEffect, useRef, useState } from "react";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";

const freshForm = () => ({ rate_eur_idr: 17500, file: null, note: "" });
const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

export function useRoyaltyImports() {
  const { user } = useAuth();
  const [imports, setImports] = useState([]);
  const [open, setOpen] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);
  const [resetConfirm, setResetConfirm] = useState("");
  const [form, setForm] = useState(freshForm());
  const [busy, setBusy] = useState(false);
  const [uploadStage, setUploadStage] = useState("");
  const [uploadPct, setUploadPct] = useState(0);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [recalcBusy, setRecalcBusy] = useState(false);
  const [recalcJob, setRecalcJob] = useState(null);
  const pollRef = useRef(null);

  const load = useCallback(async () => {
    const response = await api.get("/royalty/admin/imports");
    setImports(response.data);
  }, []);

  useEffect(() => { load().catch((error) => setErr(formatApiError(error.response?.data?.detail))); }, [load]);
  useEffect(() => {
    const inFlight = imports.some((item) => ["processing", "publishing", "receiving", "deleting"].includes(item.status));
    if (inFlight && !pollRef.current) pollRef.current = setInterval(load, 4000);
    if (!inFlight && pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [imports, load]);

  const runRowAction = async (event, action, success) => {
    event.preventDefault(); event.stopPropagation(); setErr(""); setMsg("");
    try { await action(); setMsg(success); await load(); }
    catch (error) { setErr(formatApiError(error.response?.data?.detail)); }
  };
  const retry = (id, event) => runRowAction(event, () => api.post(`/royalty/admin/imports/${id}/retry`), "Retry dijadwalkan — proses akan jalan di background.");
  const forceFinalize = async (id, event) => {
    if (!window.confirm("Force-finalize import ini dari baris yang sudah masuk MongoDB?")) return;
    await runRowAction(event, async () => {
      const response = await api.post(`/royalty/admin/imports/${id}/force-finalize`);
      setMsg(response.data.ok ? `Force-finalize berhasil — ${(response.data.total_lines || 0).toLocaleString("id-ID")} baris.` : response.data.detail);
    }, "Force-finalize selesai.");
  };
  const remove = async (item, event) => {
    if (!window.confirm(`Hapus import ${item.period || item.id.slice(0, 8)} (${item.status}) secara permanen?`)) return;
    await runRowAction(event, () => api.delete(`/royalty/admin/imports/${item.id}`), "Penghapusan dijadwalkan di background.");
  };

  const uploadToR2 = (init, file) => new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", init.presigned_put_url); xhr.setRequestHeader("Content-Type", init.content_type);
    xhr.upload.onprogress = (event) => event.lengthComputable && setUploadPct(Math.round((event.loaded / event.total) * 100));
    xhr.onload = () => xhr.status >= 200 && xhr.status < 300 ? resolve() : reject(new Error(`Upload R2 gagal (HTTP ${xhr.status})`));
    xhr.onerror = () => reject(new Error("Network error saat upload ke R2"));
    xhr.send(file);
  });

  const submit = async (event) => {
    event.preventDefault(); setErr(""); setMsg("");
    if (!form.file) { setErr("File CSV wajib diupload"); return; }
    setBusy(true); setUploadPct(0);
    try {
      setUploadStage("initiating");
      const response = await api.post("/royalty/admin/imports/initiate", {
        filename: form.file.name, rate_eur_idr: Number(form.rate_eur_idr),
        note: form.note || null, file_size_bytes: form.file.size,
      });
      setUploadStage("uploading"); await uploadToR2(response.data, form.file);
      setUploadStage("finalizing"); await api.post(`/royalty/admin/imports/${response.data.import_id}/finalize`);
      setMsg(`File berhasil diupload (${(form.file.size / 1024 / 1024).toFixed(1)} MB) — processing di background.`);
      setOpen(false); setForm(freshForm()); setUploadPct(0); setUploadStage(""); await load();
    } catch (error) { setErr(error.message || formatApiError(error.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const pollJob = async (jobId, onDone) => {
    while (true) {
      const response = await api.get(`/admin/migrate/jobs/${jobId}`);
      const job = response.data;
      if (job.status === "done") { await onDone(job); return; }
      if (job.status === "error") throw new Error(job.error_message || "Background job gagal");
      setMsg(`Proses background: ${job.phase || job.status}…`); await wait(2000);
    }
  };

  const submitReset = async (event) => {
    event.preventDefault(); setErr(""); setMsg(""); setBusy(true);
    try {
      const body = new FormData(); body.append("confirm", resetConfirm);
      const response = await api.post("/royalty/admin/reset-demo-data", body);
      setResetOpen(false); setResetConfirm("");
      await pollJob(response.data.job_id, async (job) => {
        setMsg(`Reset selesai — ${job.result?.imports_deleted || 0} import dan ${job.result?.lines_deleted || 0} lines dihapus.`);
        await load();
      });
    } catch (error) { setErr(formatApiError(error.response?.data?.detail || error.message)); }
    finally { setBusy(false); }
  };

  const recalculateAll = async () => {
    if (!window.confirm("Hitung ulang seluruh royalti yang belum withdrawn dengan persentase label saat ini?")) return;
    setErr(""); setMsg(""); setRecalcBusy(true);
    try {
      const response = await api.post("/royalty/admin/recalculate-unwithdrawn");
      await pollJob(response.data.job_id, async (job) => {
        setRecalcJob(job);
        setMsg(`Hitung ulang selesai — ${(job.result?.labels_recalculated || 0).toLocaleString("id-ID")} label.`);
        await load();
      });
    } catch (error) { setErr(formatApiError(error.response?.data?.detail || error.message)); }
    finally { setRecalcBusy(false); }
  };

  return {
    user, imports, open, setOpen, resetOpen, setResetOpen, resetConfirm, setResetConfirm,
    form, setForm, busy, uploadStage, uploadPct, err, msg, recalcBusy, recalcJob,
    retry, forceFinalize, remove, submit, submitReset, recalculateAll,
  };
}