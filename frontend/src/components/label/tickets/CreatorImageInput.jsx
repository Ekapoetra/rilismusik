import React, { useEffect, useState } from "react";
import { Upload, X } from "lucide-react";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

export const useLocalImage = (file) => {
  const [url, setUrl] = useState("");
  useEffect(() => {
    if (!file) { setUrl(""); return; }
    const next = URL.createObjectURL(file); setUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [file]);
  return url;
};

export const CreatorImageInput = ({ file, onChange, prefix, label, maxMb = 10 }) => {
  const { t } = useAppPreferences();
  const [error, setError] = useState("");
  const preview = useLocalImage(file);
  const choose = (event) => {
    const selected = event.target.files?.[0]; event.target.value = "";
    if (!selected) return;
    if (!["image/png", "image/jpeg"].includes(selected.type)) { setError(t("Gunakan PNG atau JPG.")); return; }
    if (selected.size > maxMb * 1024 * 1024) { setError(`${t("Ukuran maksimal")}: ${maxMb} MB`); return; }
    setError(""); onChange(selected);
  };
  return <div className="min-w-0 space-y-2" data-testid={`${prefix}-field`}>
    <label className="rm-label" htmlFor={`${prefix}-input`}>{t(label)}</label>
    <div className="flex min-w-0 items-center gap-2"><Upload className="h-4 w-4 shrink-0 text-zinc-500" /><input id={`${prefix}-input`} type="file" accept="image/png,image/jpeg" onChange={choose} className="rm-input min-w-0 w-full text-xs" data-testid={`${prefix}-input`} /></div>
    <p className="text-xs text-zinc-500" data-testid={`${prefix}-limit`}>PNG / JPG · {maxMb} MB</p>
    {error && <p role="alert" className="text-xs text-red-400" data-testid={`${prefix}-error`}>{error}</p>}
    {preview && <div className="relative flex aspect-[8/5] items-center justify-center overflow-hidden rounded-md border border-white/10 bg-white p-2" data-testid={`${prefix}-preview`}><img src={preview} alt={t(label)} className="h-full w-full object-contain" data-testid={`${prefix}-image`} /><button type="button" onClick={() => onChange(null)} className="absolute right-1 top-1 rounded bg-black/70 p-1.5 text-white transition-colors hover:bg-black" title={t("Hapus gambar")} aria-label={t("Hapus gambar")} data-testid={`${prefix}-remove`}><X className="h-4 w-4" /></button></div>}
  </div>;
};