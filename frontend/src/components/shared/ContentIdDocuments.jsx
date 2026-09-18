import React, { useCallback, useEffect, useState } from "react";
import { Download, FileText, CreditCard, PenLine, Eye, EyeOff, RefreshCw, ShieldAlert, FileWarning } from "lucide-react";
import { api } from "@/api/client";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";

export const ContentIdDocuments = ({ ticket, prefix }) => {
  const { t } = useAppPreferences();
  const [documents, setDocuments] = useState([]); const [loading, setLoading] = useState(true);
  const [error, setError] = useState(""); const [busy, setBusy] = useState(""); const [revealed, setRevealed] = useState({});
  const [preview, setPreview] = useState(null);
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { const { data } = await api.get(`/tickets/content-id/tickets/${ticket.id}`); setDocuments(data); }
    catch { setError("Dokumen belum dapat dimuat."); }
    finally { setLoading(false); }
  }, [ticket.id]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => () => { if (preview?.url) URL.revokeObjectURL(preview.url); }, [preview]);
  const viewAsset = async (doc, kind) => {
    setBusy(`${doc.id}-${kind}`); setError("");
    try { const { data } = await api.get(`/tickets/content-id/assets/${doc[`${kind}_asset_id`]}`, { responseType: "blob" }); setPreview({ url: URL.createObjectURL(data), title: kind === "ktp" ? "KTP Pencipta" : "Tanda Tangan Pencipta", name: doc.creator_name }); }
    catch { setError("Dokumen belum dapat dimuat."); }
    finally { setBusy(""); }
  };
  const download = async (doc, index) => {
    setBusy(`${doc.id}-pdf`); setError("");
    try {
      const { data } = await api.get(`/tickets/content-id/tickets/${ticket.id}/${doc.id}/pdf`, { responseType: "blob" });
      const url = URL.createObjectURL(data); const anchor = document.createElement("a"); anchor.href = url; anchor.download = `Surat-Pernyataan-Hak-Cipta-${index + 1}.pdf`; document.body.appendChild(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch { setError("PDF belum dapat diunduh. Silakan coba lagi."); }
    finally { setBusy(""); }
  };
  const downloadLetter = async (doc, index, kind, filenamePrefix) => {
    setBusy(`${doc.id}-${kind}`); setError("");
    try {
      const { data } = await api.get(`/tickets/content-id/tickets/${ticket.id}/${doc.id}/${kind}`, { responseType: "blob" });
      const url = URL.createObjectURL(data); const anchor = document.createElement("a"); anchor.href = url; anchor.download = `${filenamePrefix}-${index + 1}.pdf`; document.body.appendChild(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch { setError("PDF belum dapat diunduh. Silakan coba lagi."); }
    finally { setBusy(""); }
  };
  return <section className="min-w-0 space-y-4 border-y border-white/10 py-5" data-testid={`${prefix}-contentid-documents`}>
    <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="flex items-center gap-2 text-base font-bold"><FileText className="h-4 w-4 text-pink-400" />{t("Surat Pernyataan Hak Cipta")}</h2><span className="text-xs text-zinc-500" data-testid={`${prefix}-contentid-document-count`}>{documents.length} PDF</span></div>
    {loading && <p className="text-sm text-zinc-500" data-testid={`${prefix}-contentid-loading`}>{t("Memuat dokumen…")}</p>}
    {error && <div role="alert" className="flex flex-wrap items-center gap-2 text-sm text-red-400" data-testid={`${prefix}-contentid-error`}>{t(error)}<button type="button" onClick={load} disabled={loading} className="rounded p-1 transition-colors hover:text-pink-400" aria-label={t("Coba lagi")} title={t("Coba lagi")} data-testid={`${prefix}-contentid-retry`}><RefreshCw className="h-4 w-4" /></button></div>}
    {!loading && !error && !documents.length && <p className="text-sm text-zinc-500" data-testid={`${prefix}-contentid-empty`}>{t("Surat belum tersedia untuk tiket ini.")}</p>}
    {documents.map((doc, index) => <article key={doc.id} className="min-w-0 space-y-3 rounded-lg border border-white/10 p-4" data-testid={`${prefix}-contentid-document-${index}`}>
      <div className="flex flex-wrap items-start justify-between gap-2"><strong className="min-w-0 break-words" translate="no" data-testid={`${prefix}-contentid-name-${index}`}>{doc.creator_name}</strong><span className="text-xs text-emerald-400" data-testid={`${prefix}-contentid-status-${index}`}>{t("PDF siap diunduh")}</span></div>
      <div className="flex flex-wrap items-center gap-2 text-sm"><span className="text-zinc-500">NIK</span><code translate="no" data-testid={`${prefix}-contentid-nik-${index}`}>{revealed[doc.id] ? doc.nik : `•••• •••• •••• ${doc.nik.slice(-4)}`}</code><button type="button" onClick={() => setRevealed((current) => ({ ...current, [doc.id]: !current[doc.id] }))} className="rounded p-1 text-zinc-500 transition-colors hover:text-pink-400" aria-label={t(revealed[doc.id] ? "Sembunyikan NIK" : "Tampilkan NIK")} title={t(revealed[doc.id] ? "Sembunyikan NIK" : "Tampilkan NIK")} data-testid={`${prefix}-contentid-nik-toggle-${index}`}>{revealed[doc.id] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button></div>
      <p className="break-words text-xs text-zinc-500" translate="no" data-testid={`${prefix}-contentid-domicile-${index}`}>{doc.domicile}</p>
      <ul className="space-y-1 text-sm">{doc.tracks.map((track) => <li key={track.id} translate="no" className="break-words" data-testid={`${prefix}-contentid-track-${index}-${track.id}`}>{track.track_title} <span className="text-xs text-zinc-500">· {track.isrc || "—"}</span></li>)}</ul>
      <div className="flex flex-wrap gap-2"><button type="button" onClick={() => download(doc, index)} disabled={!!busy} className="rm-btn-primary inline-flex items-center gap-2 text-xs" data-testid={`${prefix}-contentid-pdf-${index}`}><Download className="h-4 w-4" />{t(busy === `${doc.id}-pdf` ? "Mengunduh…" : "Unduh PDF")}</button><button type="button" onClick={() => downloadLetter(doc, index, "indemnification", "Indemnification-Letter")} disabled={!!busy} className="rm-btn-ghost inline-flex items-center gap-2 text-xs" data-testid={`${prefix}-contentid-indemnification-${index}`}><ShieldAlert className="h-4 w-4" />{t(busy === `${doc.id}-indemnification` ? "Mengunduh…" : "Indemnification Letter")}</button><button type="button" onClick={() => downloadLetter(doc, index, "dmca", "DMCA-Counter-Notification")} disabled={!!busy} className="rm-btn-ghost inline-flex items-center gap-2 text-xs" data-testid={`${prefix}-contentid-dmca-${index}`}><FileWarning className="h-4 w-4" />{t(busy === `${doc.id}-dmca` ? "Mengunduh…" : "DMCA Counter Notification")}</button><button type="button" onClick={() => viewAsset(doc, "ktp")} disabled={!!busy} className="rm-btn-ghost inline-flex items-center gap-2 text-xs" data-testid={`${prefix}-contentid-ktp-${index}`}><CreditCard className="h-4 w-4" />{t("Lihat KTP")}</button><button type="button" onClick={() => viewAsset(doc, "signature")} disabled={!!busy} className="rm-btn-ghost inline-flex items-center gap-2 text-xs" data-testid={`${prefix}-contentid-signature-${index}`}><PenLine className="h-4 w-4" />{t("Tanda tangan")}</button></div>
    </article>)}
    <Dialog open={!!preview} onOpenChange={(open) => !open && setPreview(null)}><DialogContent className="ui-menu max-h-[90dvh] w-[calc(100%-2rem)] max-w-2xl overflow-y-auto rounded-lg" data-testid={`${prefix}-contentid-image-dialog`} closeTestId={`${prefix}-contentid-image-close`}>
      <DialogHeader><DialogTitle>{t(preview?.title || "Dokumen Pencipta")}</DialogTitle><DialogDescription translate="no">{preview?.name}</DialogDescription></DialogHeader>
      {preview && <img src={preview.url} alt={t(preview.title)} className="max-h-[65dvh] w-full rounded-md object-contain" style={{ background: "#ffffff" }} data-testid={`${prefix}-contentid-private-image`} />}
    </DialogContent></Dialog>
  </section>;
};