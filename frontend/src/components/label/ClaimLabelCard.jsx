import React, { useState } from "react";
import { History, Loader2 } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export const ClaimLabelCard = ({ claimStatus, onSubmitted }) => {
  const [open, setOpen] = useState(false);
  const [legacyName, setLegacyName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    if (legacyName.trim().length < 2) { setError("Nama label lama wajib diisi."); return; }
    setBusy(true); setError("");
    try {
      await api.post("/label/claim-request", { legacy_label_name: legacyName.trim() });
      setOpen(false); setLegacyName("");
      toast.success("Permintaan klaim label dikirim. Admin akan memproses 1-3 hari kerja.");
      await onSubmitted();
    } catch (err) { setError(formatApiError(err.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  return (
    <section className="rm-card p-6 space-y-3" data-testid="label-claim-card">
      <div className="flex items-center gap-2 font-display font-bold text-lg tracking-tight"><History className="w-5 h-5" /> Punya Data Lama di RILIS MUSIK?</div>
      <p className="text-sm text-zinc-400 leading-relaxed">
        Jika Anda sebelumnya sudah menjadi label/artis RILIS MUSIK (data royalti, penarikan, atau rilisan lama), ajukan klaim agar admin menghubungkan data lama ke akun ini.
      </p>
      {claimStatus === "rejected" && <div className="rounded-lg bg-red-500/10 border border-red-500/20 text-red-200 px-4 py-3 text-sm" data-testid="label-claim-rejected">Permintaan klaim sebelumnya ditolak. Anda dapat mengajukan ulang dengan nama label yang benar.</div>}
      <button className="rm-btn-primary" onClick={() => setOpen(true)} data-testid="label-claim-open-button">Klaim Label Lama</button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="border-white/10 bg-[#0F0F0F] text-white" closeTestId="label-claim-dialog-close">
          <DialogHeader>
            <DialogTitle className="font-display text-xl">Klaim Label Lama</DialogTitle>
            <DialogDescription className="text-zinc-400">Masukkan nama label persis seperti yang dulu dikenal RILIS MUSIK. Admin akan menghubungkan data lama Anda dan menghapus profil label kosong akun ini.</DialogDescription>
          </DialogHeader>
          <input
            className="rm-input"
            value={legacyName}
            onChange={(e) => setLegacyName(e.target.value)}
            placeholder="Nama label lama"
            data-testid="label-claim-legacy-name-input"
          />
          {error && <div role="alert" className="text-sm text-red-300" data-testid="label-claim-error">{error}</div>}
          <DialogFooter>
            <button type="button" className="rm-btn-ghost" onClick={() => setOpen(false)} data-testid="label-claim-cancel">Batal</button>
            <button type="button" className="rm-btn-primary inline-flex items-center gap-2" onClick={submit} disabled={busy} data-testid="label-claim-submit">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}{busy ? "Mengirim…" : "Kirim Permintaan"}</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
};
