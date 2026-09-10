import React, { useEffect, useRef, useState } from "react";
import SignaturePad from "signature_pad";
import { PenLine, Upload, Undo2, Trash2 } from "lucide-react";
import { CreatorImageInput } from "./CreatorImageInput";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

const signatureFile = (pad) => {
  if (!pad || pad.isEmpty()) return null;
  const points = pad.toData().flatMap((group) => group.points);
  const xs = points.map((point) => point.x); const ys = points.map((point) => point.y);
  if (!points.length || Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)) < 12) return null;
  const data = atob(pad.toDataURL("image/png").split(",")[1]);
  return new File([Uint8Array.from(data, (char) => char.charCodeAt(0))], "tanda-tangan.png", { type: "image/png" });
};

export const CreatorSignature = ({ file, onChange, prefix }) => {
  const { t } = useAppPreferences();
  const canvas = useRef(null); const pad = useRef(null); const change = useRef(onChange); change.current = onChange;
  const [mode, setMode] = useState("upload");
  useEffect(() => {
    const el = canvas.current;
    const signature = new SignaturePad(el, { penColor: "#111111", minWidth: 0.8, maxWidth: 2.4 }); pad.current = signature;
    const commit = () => change.current(signatureFile(signature), "drawn");
    signature.addEventListener("endStroke", commit);
    let previous = { width: 0, height: 0 };
    const resize = () => {
      const rect = el.getBoundingClientRect(); if (!rect.width || !rect.height) return;
      const points = signature.toData(); const ratio = Math.min(window.devicePixelRatio || 1, 3);
      el.width = Math.round(rect.width * ratio); el.height = Math.round(rect.height * ratio); el.getContext("2d").scale(ratio, ratio);
      signature.clear();
      if (previous.width && previous.height) signature.fromData(points.map((group) => ({ ...group, points: group.points.map((point) => ({ ...point, x: point.x * rect.width / previous.width, y: point.y * rect.height / previous.height })) })));
      previous = { width: rect.width, height: rect.height };
    };
    const observer = new ResizeObserver(resize); observer.observe(el); resize();
    return () => { observer.disconnect(); signature.removeEventListener("endStroke", commit); signature.off(); pad.current = null; };
  }, []);
  const undo = () => { const data = pad.current.toData(); data.pop(); pad.current.fromData(data); onChange(signatureFile(pad.current), "drawn"); };
  const clear = () => { pad.current.clear(); onChange(null, "drawn"); };
  const switchMode = (next) => { if (next === mode) return; setMode(next); if (next === "draw") onChange(signatureFile(pad.current), "drawn"); else onChange(null, "upload"); };
  return <section className="min-w-0 space-y-3" data-testid={`${prefix}-signature`}>
    <div className="rm-label">{t("Tanda Tangan Pencipta")}</div>
    <div role="tablist" aria-label={t("Metode tanda tangan")} className="inline-flex max-w-full rounded-md border border-white/10 p-1">
      <button type="button" role="tab" aria-selected={mode === "upload"} onClick={() => switchMode("upload")} className={`flex items-center gap-1.5 rounded px-3 py-2 text-xs transition-colors ${mode === "upload" ? "bg-white/10" : "text-zinc-500 hover:text-pink-400"}`} data-testid={`${prefix}-signature-upload-tab`}><Upload className="h-3.5 w-3.5" />{t("Unggah")}</button>
      <button type="button" role="tab" aria-selected={mode === "draw"} onClick={() => switchMode("draw")} className={`flex items-center gap-1.5 rounded px-3 py-2 text-xs transition-colors ${mode === "draw" ? "bg-white/10" : "text-zinc-500 hover:text-pink-400"}`} data-testid={`${prefix}-signature-draw-tab`}><PenLine className="h-3.5 w-3.5" />{t("Gambar langsung")}</button>
    </div>
    {mode === "upload" && <CreatorImageInput file={file} onChange={(value) => onChange(value, "upload")} prefix={`${prefix}-signature-upload`} label="Gambar Tanda Tangan" maxMb={5} />}
    <div className={mode === "draw" ? "space-y-2" : "hidden"}>
      <canvas ref={canvas} className="aspect-[5/2] w-full touch-none rounded-md border border-zinc-300 bg-white" style={{ background: "#ffffff" }} aria-label={t("Area tanda tangan pencipta")} data-testid={`${prefix}-signature-canvas`} />
      <div className="flex items-center justify-end gap-2"><button type="button" onClick={undo} className="rm-btn-ghost p-2" title={t("Urungkan goresan")} aria-label={t("Urungkan goresan")} data-testid={`${prefix}-signature-undo`}><Undo2 className="h-4 w-4" /></button><button type="button" onClick={clear} className="rm-btn-ghost p-2" title={t("Hapus tanda tangan")} aria-label={t("Hapus tanda tangan")} data-testid={`${prefix}-signature-clear`}><Trash2 className="h-4 w-4" /></button></div>
    </div>
    <p className={`text-xs ${file ? "text-emerald-400" : "text-zinc-500"}`} data-testid={`${prefix}-signature-status`}>{t(file ? "Tanda tangan siap." : "Tanda tangan wajib dilengkapi.")}</p>
  </section>;
};