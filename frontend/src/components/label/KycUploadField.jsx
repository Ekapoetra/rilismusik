import React, { useRef, useState } from "react";
import { ImagePlus, Loader2, ShieldCheck, UploadCloud } from "lucide-react";
import { api, fileUrl, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";

export const KycUploadField = ({ kind, title, description, maxMb, currentUrl, disabled, onUploaded }) => {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const endpoint = kind === "logo" ? "/label/logo" : "/label/kyc/ktp";

  const upload = async (file) => {
    if (!file) return;
    if (!["image/jpeg", "image/png"].includes(file.type)) { setError("File wajib JPG atau PNG."); return; }
    if (file.size > maxMb * 1024 * 1024) { setError(`Ukuran file maksimal ${maxMb} MB.`); return; }
    setBusy(true); setError("");
    try {
      const form = new FormData(); form.append("file", file);
      await api.post(endpoint, form, { headers: { "Content-Type": "multipart/form-data" } });
      await onUploaded();
      toast.success(kind === "logo" ? "Logo label berhasil diunggah." : "KTP berhasil dikirim untuk review.");
    } catch (err) { setError(formatApiError(err.response?.data?.detail)); }
    finally { setBusy(false); if (inputRef.current) inputRef.current.value = ""; }
  };

  return (
    <div className="space-y-3" data-testid={`kyc-${kind}-upload-section`}>
      <div className="flex items-start justify-between gap-4">
        <div><h3 className="font-display text-lg font-bold">{title}</h3><p className="mt-1 text-sm leading-relaxed text-zinc-500">{description}</p></div>
        {kind === "ktp" && <ShieldCheck className="h-5 w-5 shrink-0 text-emerald-300" />}
      </div>
      {currentUrl && <div className="overflow-hidden rounded-lg border border-white/10 bg-black/30 p-3" data-testid={`kyc-${kind}-preview`}><img src={fileUrl(currentUrl)} alt={title} className="mx-auto max-h-56 w-full object-contain" /></div>}
      <button type="button" disabled={disabled || busy} onClick={() => inputRef.current?.click()} className="group flex w-full items-center gap-4 rounded-lg border border-dashed border-white/20 bg-white/[0.03] p-5 text-left transition-colors hover:border-white/35 hover:bg-white/[0.06] disabled:cursor-not-allowed disabled:opacity-40" data-testid={`kyc-${kind}-upload-button`}>
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-md bg-white/[0.06] text-zinc-300">{busy ? <Loader2 className="h-5 w-5 animate-spin" /> : kind === "logo" ? <ImagePlus className="h-5 w-5" /> : <UploadCloud className="h-5 w-5" />}</span>
        <span><span className="block text-sm font-semibold text-white">{busy ? "Mengunggah…" : currentUrl ? "Ganti file" : "Pilih file"}</span><span className="mt-1 block text-xs text-zinc-500">JPG atau PNG · Maksimal {maxMb} MB</span></span>
      </button>
      <input ref={inputRef} type="file" accept="image/jpeg,image/png" className="hidden" disabled={disabled || busy} onChange={(event) => upload(event.target.files?.[0])} data-testid={`kyc-${kind}-file-input`} />
      {error && <div role="alert" className="text-sm text-red-300" data-testid={`kyc-${kind}-upload-error`}>{error}</div>}
    </div>
  );
};