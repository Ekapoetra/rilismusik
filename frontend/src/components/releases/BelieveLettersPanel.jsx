import React, { useMemo, useState } from "react";
import { FileWarning, ShieldAlert, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/api/client";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";

const downloadBlob = (data, filename) => {
  const url = URL.createObjectURL(data);
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = filename;
  document.body.appendChild(anchor); anchor.click(); anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
};

const readError = async (requestError) => {
  let detail = requestError.response?.data?.detail;
  if (requestError.response?.data instanceof Blob) { try { detail = JSON.parse(await requestError.response.data.text())?.detail; } catch { /* ignore */ } }
  return formatApiError(detail) || "Terjadi kesalahan";
};

const dmcaTemplate = (tracks) => {
  const titles = tracks.map((t) => `"${t.track_title}"`).join(", ") || "\"\"";
  const artist = tracks[0]?.artist_name || "";
  return `The removal of this content is a mistake. I am the original producer and rights owner of the sound recording ${titles} performed by "${artist}". The track was created and produced by me and legally distributed via Believe. I hold full rights to the master recording and composition. The claimant does not own the rights to this recording. Therefore this claim is a misidentification and should be withdrawn.`;
};

export const BelieveLettersPanel = ({ release }) => {
  const tracks = useMemo(() => release.tracks || [], [release.tracks]);
  const isrcTracks = tracks.filter((t) => t.isrc);
  const [indemOpen, setIndemOpen] = useState(false);
  const [dmcaOpen, setDmcaOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  // Indemnification state
  const [selectedIsrcs, setSelectedIsrcs] = useState([]);
  const openIndem = () => { setSelectedIsrcs(isrcTracks.map((t) => t.isrc)); setIndemOpen(true); };
  const toggleIsrc = (isrc) => setSelectedIsrcs((cur) => cur.includes(isrc) ? cur.filter((x) => x !== isrc) : [...cur, isrc]);
  const generateIndem = async () => {
    setBusy(true);
    try {
      const response = await api.post(`/releases/${release.id}/admin/indemnification-letter`, { isrcs: selectedIsrcs }, { responseType: "blob" });
      downloadBlob(response.data, `Indemnification-Letter-${release.release_title || release.id}.pdf`);
      toast.success("Indemnification Letter berhasil diunduh");
      setIndemOpen(false);
    } catch (e) { toast.error(await readError(e)); } finally { setBusy(false); }
  };

  // DMCA state
  const contact0 = release.label_contact || {};
  const [dmcaTracks, setDmcaTracks] = useState([]);
  const [explanation, setExplanation] = useState("");
  const [explanationTouched, setExplanationTouched] = useState(false);
  const [contact, setContact] = useState({ legal_name: "", phone: "", email: "", country: "Indonesia", street: "", city: "", postcode: "" });
  const [signatureName, setSignatureName] = useState("");
  const selectedDmcaTracks = useMemo(() => tracks.filter((t) => dmcaTracks.includes(t.id)), [tracks, dmcaTracks]);

  const openDmca = () => {
    const initial = tracks.map((t) => t.id);
    setDmcaTracks(initial);
    setExplanation(dmcaTemplate(tracks));
    setExplanationTouched(false);
    setContact({ legal_name: contact0.legal_name || "", phone: contact0.phone || "", email: contact0.email || "", country: contact0.country || "Indonesia", street: contact0.street || "", city: contact0.city || "", postcode: contact0.postcode || "" });
    setSignatureName(contact0.legal_name || "");
    setDmcaOpen(true);
  };
  const toggleDmcaTrack = (id) => setDmcaTracks((cur) => {
    const next = cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id];
    if (!explanationTouched) setExplanation(dmcaTemplate(tracks.filter((t) => next.includes(t.id))));
    return next;
  });
  const setC = (key) => (event) => setContact((cur) => ({ ...cur, [key]: event.target.value }));
  const generateDmca = async () => {
    setBusy(true);
    try {
      const response = await api.post(`/releases/${release.id}/admin/dmca-letter`, {
        track_ids: dmcaTracks, explanation, contact, signature_name: signatureName,
      }, { responseType: "blob" });
      downloadBlob(response.data, `DMCA-Counter-Notification-${release.release_title || release.id}.pdf`);
      toast.success("DMCA Counter Notification berhasil diunduh");
      setDmcaOpen(false);
    } catch (e) { toast.error(await readError(e)); } finally { setBusy(false); }
  };

  return <>
    <button type="button" onClick={openIndem} className="rm-btn-ghost inline-flex items-center gap-2" data-testid="admin-release-indemnification-button" title="Surat ganti rugi untuk reinstate konten Content ID di Believe"><ShieldAlert className="h-4 w-4" /> Indemnification Letter</button>
    <button type="button" onClick={openDmca} className="rm-btn-ghost inline-flex items-center gap-2" data-testid="admin-release-dmca-button" title="Surat sanggahan takedown DMCA untuk Believe"><FileWarning className="h-4 w-4" /> DMCA Counter Notification</button>

    <Dialog open={indemOpen} onOpenChange={setIndemOpen}>
      <DialogContent className="max-w-lg" data-testid="admin-indemnification-dialog">
        <DialogHeader><DialogTitle className="font-display text-xl font-extrabold">Indemnification Letter</DialogTitle><DialogDescription className="text-zinc-400">Ditandatangani atas nama RILIS MUSIK (dari CMS). Pilih ISRC yang akan dicantumkan.</DialogDescription></DialogHeader>
        <div className="space-y-3">
          <div className="text-xs text-zinc-500">UPC: <span className="font-mono text-zinc-200" data-testid="indem-upc">{release.upc || "— (rilisan belum tayang)"}</span></div>
          {isrcTracks.length === 0 ? <div className="rounded-md bg-amber-500/15 px-3 py-2 text-sm text-amber-200" data-testid="indem-no-isrc">Belum ada ISRC pada rilisan ini. Surat tersedia setelah ISRC/UPC terisi (rilisan tayang).</div> :
            <div className="max-h-64 space-y-2 overflow-auto rounded-md border border-white/10 p-3" data-testid="indem-isrc-list">
              {isrcTracks.map((t) => <label key={t.id} className="flex items-center gap-3 text-sm" data-testid={`indem-isrc-${t.id}`}>
                <input type="checkbox" checked={selectedIsrcs.includes(t.isrc)} onChange={() => toggleIsrc(t.isrc)} className="h-4 w-4" data-testid={`indem-isrc-checkbox-${t.id}`} />
                <span className="font-mono text-zinc-300">{t.isrc}</span><span className="truncate text-zinc-500">— {t.track_title}</span>
              </label>)}
            </div>}
        </div>
        <DialogFooter>
          <button type="button" className="rm-btn-ghost" onClick={() => setIndemOpen(false)} data-testid="indem-cancel">Batal</button>
          <button type="button" className="rm-btn-primary inline-flex items-center gap-2" disabled={busy || selectedIsrcs.length === 0 || !release.upc} onClick={generateIndem} data-testid="indem-generate">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null} Generate & Unduh PDF</button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog open={dmcaOpen} onOpenChange={setDmcaOpen}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-auto" data-testid="admin-dmca-dialog">
        <DialogHeader><DialogTitle className="font-display text-xl font-extrabold">DMCA Counter Notification</DialogTitle><DialogDescription className="text-zinc-400">Isi data kontak & pernyataan. Kotak persetujuan otomatis tercentang di PDF.</DialogDescription></DialogHeader>
        <div className="space-y-4">
          <div>
            <div className="mb-2 text-xs font-bold uppercase tracking-widest text-zinc-500">Track (ISRC)</div>
            <div className="max-h-40 space-y-2 overflow-auto rounded-md border border-white/10 p-3" data-testid="dmca-track-list">
              {tracks.map((t) => <label key={t.id} className="flex items-center gap-3 text-sm" data-testid={`dmca-track-${t.id}`}>
                <input type="checkbox" checked={dmcaTracks.includes(t.id)} onChange={() => toggleDmcaTrack(t.id)} className="h-4 w-4" data-testid={`dmca-track-checkbox-${t.id}`} />
                <span className="font-mono text-zinc-300">{t.isrc || "(tanpa ISRC)"}</span><span className="truncate text-zinc-500">— {t.track_title}</span>
              </label>)}
            </div>
          </div>
          <div>
            <label className="rm-label">Penjelasan (Section 2)</label>
            <textarea className="rm-input min-h-[120px]" value={explanation} onChange={(e) => { setExplanation(e.target.value); setExplanationTouched(true); }} data-testid="dmca-explanation" />
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div><label className="rm-label">Nama Legal Lengkap</label><input className="rm-input" value={contact.legal_name} onChange={setC("legal_name")} data-testid="dmca-legal-name" /></div>
            <div><label className="rm-label">Nomor Telepon</label><input className="rm-input" value={contact.phone} onChange={setC("phone")} data-testid="dmca-phone" /></div>
            <div><label className="rm-label">Email</label><input className="rm-input" value={contact.email} onChange={setC("email")} data-testid="dmca-email" /></div>
            <div><label className="rm-label">Negara</label><input className="rm-input" value={contact.country} onChange={setC("country")} data-testid="dmca-country" /></div>
            <div className="sm:col-span-2"><label className="rm-label">Alamat</label><input className="rm-input" value={contact.street} onChange={setC("street")} data-testid="dmca-street" /></div>
            <div><label className="rm-label">Kota</label><input className="rm-input" value={contact.city} onChange={setC("city")} data-testid="dmca-city" /></div>
            <div><label className="rm-label">Kode Pos</label><input className="rm-input" value={contact.postcode} onChange={setC("postcode")} data-testid="dmca-postcode" /></div>
          </div>
          <div><label className="rm-label">Tanda Tangan (ketik nama legal lengkap)</label><input className="rm-input" value={signatureName} onChange={(e) => setSignatureName(e.target.value)} data-testid="dmca-signature" /></div>
        </div>
        <DialogFooter>
          <button type="button" className="rm-btn-ghost" onClick={() => setDmcaOpen(false)} data-testid="dmca-cancel">Batal</button>
          <button type="button" className="rm-btn-primary inline-flex items-center gap-2" disabled={busy || dmcaTracks.length === 0 || !contact.legal_name.trim() || !signatureName.trim() || !explanation.trim()} onClick={generateDmca} data-testid="dmca-generate">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null} Generate & Unduh PDF</button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </>;
};
