import React, { useEffect, useState } from "react";
import { Disc3, ImagePlus, Upload, Loader2 } from "lucide-react";
import { api, fileUrl, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export const ReleaseArtwork = ({ release, prefix, onUpdated, large = false }) => {
  const { user, hasPermission } = useAuth(); const { t } = useAppPreferences();
  const [src, setSrc] = useState(""); const [failed, setFailed] = useState(false); const [internal, setInternal] = useState(false);
  const [open, setOpen] = useState(false); const [file, setFile] = useState(null); const [preview, setPreview] = useState(""); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const canUpload = release.imported_legacy && (user?.role === "label" || hasPermission("releases.review"));
  const id = `${prefix}-${release.id}`;
  useEffect(() => { setSrc((release.imported_legacy && release.internal_cover_url) || release.cover_url || ""); setInternal(Boolean(release.imported_legacy && release.internal_cover_url)); setFailed(false); }, [release.id, release.imported_legacy, release.internal_cover_url, release.cover_url]);
  useEffect(() => { if (!file) { setPreview(""); return; } const url = URL.createObjectURL(file); setPreview(url); return () => URL.revokeObjectURL(url); }, [file]);
  const choose = (event) => {
    const next = event.target.files?.[0]; event.target.value = ""; if (!next) return;
    if (!["image/jpeg", "image/png"].includes(next.type) || next.size > 10 * 1024 * 1024) { setError(t("Gunakan JPG/PNG maksimal 10 MB.")); return; }
    setFile(next); setError("");
  };
  const save = async () => {
    if (!file || busy) return; setBusy(true); setError("");
    try { const body = new FormData(); body.append("file", file); const { data } = await api.post(`/releases/${release.id}/internal-cover`, body, { headers: { "Content-Type": "multipart/form-data" } }); setSrc(data.internal_cover_url); setInternal(true); setFailed(false); onUpdated?.(data); setOpen(false); setFile(null); }
    catch (err) { setError(t(formatApiError(err.response?.data?.detail) || "Cover gagal disimpan.")); }
    finally { setBusy(false); }
  };
  return <div className={`relative z-10 shrink-0 ${large ? "w-28 sm:w-36" : "w-14"}`} data-testid={`${id}-artwork`}>
    <div className="relative grid aspect-square w-full place-items-center overflow-hidden rounded-md border border-white/10 bg-white/5">
      {src && !failed ? <img src={fileUrl(src)} alt={release.release_title} onError={() => setFailed(true)} className="h-full w-full object-contain" loading="lazy" data-testid={`${id}-cover-image`} /> : <Disc3 className="h-6 w-6 text-zinc-500" aria-label={t("Cover belum tersedia")} data-testid={`${id}-cover-placeholder`} />}
      {canUpload && <button type="button" onClick={(event) => { event.preventDefault(); event.stopPropagation(); setError(""); setOpen(true); }} className="absolute bottom-0 right-0 rounded-tl-md bg-black/80 p-1.5 text-white transition-colors hover:bg-pink-600" title={t("Unggah/ganti cover internal")} aria-label={t("Unggah/ganti cover internal")} data-testid={`${id}-cover-edit`}><ImagePlus className="h-3.5 w-3.5" /></button>}
    </div>
    {internal && <span className="mt-1 block text-center text-[10px] leading-tight text-amber-400" title={t("Cover internal — tidak mengubah DSP")} data-testid={`${id}-cover-internal-badge`}>{t("Cover internal")}</span>}
    <Dialog open={open} onOpenChange={(value) => { if (!busy) { setOpen(value); if (!value) setFile(null); } }}><DialogContent className="ui-menu max-h-[90dvh] w-[calc(100%-2rem)] max-w-lg overflow-y-auto rounded-lg" onClick={(event) => event.stopPropagation()} data-testid={`${id}-cover-dialog`} closeTestId={`${id}-cover-dialog-close`}>
      <DialogHeader><DialogTitle>{t("Cover internal — tidak mengubah DSP")}</DialogTitle><DialogDescription>{t("Hanya tampilan dashboard. Untuk mengganti cover di DSP, ajukan Edit Cover melalui tiket support.")}</DialogDescription></DialogHeader>
      <p className="break-words text-sm font-semibold" translate="no" data-testid={`${id}-cover-release-title`}>{release.release_title}</p>
      <label className="block"><span className="rm-label">JPG / PNG · 10 MB</span><input type="file" accept="image/jpeg,image/png" onChange={choose} disabled={busy} className="rm-input w-full min-w-0 text-xs" data-testid={`${id}-cover-input`} /></label>
      {(preview || src) && <img src={preview || fileUrl(src)} alt={t("Pratinjau cover internal")} className="aspect-square max-h-72 w-full object-contain" data-testid={`${id}-cover-preview`} />}
      {error && <p role="alert" className="text-sm text-red-400" data-testid={`${id}-cover-error`}>{error}</p>}
      <div className="flex flex-wrap justify-end gap-2"><button type="button" disabled={busy} className="rm-btn-ghost" onClick={() => { setOpen(false); setFile(null); }} data-testid={`${id}-cover-cancel`}>{t("Batal")}</button><button type="button" disabled={!file || busy} onClick={save} className="rm-btn-primary inline-flex items-center gap-2" data-testid={`${id}-cover-save`}>{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}{t(busy ? "Menyimpan…" : "Simpan Cover Internal")}</button></div>
    </DialogContent></Dialog>
  </div>;
};