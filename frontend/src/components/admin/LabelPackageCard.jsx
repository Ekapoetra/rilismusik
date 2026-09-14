import React, { useEffect, useState } from "react";
import { ArrowRight, Check, Package } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { toast } from "@/components/ui/sonner";

export const PACKAGE_NAMES = { pay_per_release: "Pay Per Release", annual_normal: "Annual", annual_vip: "VIP" };
const selectedPackage = (label) => label.payment_type === "annual_subscription" ? label.subscription_tier || "annual_normal" : "pay_per_release";

export const LabelPackageCard = ({ label, onChanged, mode = "direct" }) => {
  const { t } = useAppPreferences();
  const isRequest = mode === "request";
  const current = selectedPackage(label);
  const currentExpiry = label.subscription_expires_at?.slice(0, 10) || "";
  const [tier, setTier] = useState(current);
  const [expiry, setExpiry] = useState(currentExpiry);
  const [reason, setReason] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { setTier(current); setExpiry(currentExpiry); setConfirming(false); setReason(""); }, [label.id, label.package_revision, current, currentExpiry]);
  const changed = tier !== current || (tier !== "pay_per_release" && expiry !== currentExpiry);
  const valid = changed && reason.trim().length >= 3 && (tier === "pay_per_release" || expiry);
  const save = async () => {
    if (!valid || saving) return;
    setSaving(true); setError("");
    try {
      if (isRequest) {
        await api.post(`/admin/labels/${label.id}/package-request`, { package: tier, expires_on: tier === "pay_per_release" ? null : expiry, reason: reason.trim(), expected_revision: label.package_revision || 0 });
        setConfirming(false); toast.success(t("Permintaan perubahan paket dikirim untuk persetujuan Super Admin.")); await onChanged();
      } else {
        await api.patch(`/admin/labels/${label.id}/package`, { package: tier, expires_on: tier === "pay_per_release" ? null : expiry, reason: reason.trim(), expected_revision: label.package_revision || 0, confirm: true });
        setConfirming(false); toast.success(t("Paket langganan diperbarui.")); await onChanged();
      }
    } catch (err) { setError(t(formatApiError(err.response?.data?.detail) || "Paket gagal diperbarui.")); }
    finally { setSaving(false); }
  };
  return <section className="rm-card min-w-0 space-y-4 p-5" data-testid="admin-label-subscription-card">
    <h2 className="flex items-center gap-2 font-display text-lg font-bold"><Package className="h-4 w-4" />{t("Paket & Langganan")}{isRequest && <span className="rm-badge bg-amber-500/15 text-amber-300 text-[10px]">{t("Perlu Persetujuan")}</span>}</h2>
    <div className="text-sm text-zinc-400" data-testid="admin-label-current-package">{t("Paket saat ini")}: <strong className="text-zinc-200">{PACKAGE_NAMES[current]}</strong></div>
    <label className="block"><span className="rm-label">{t("Paket")}</span><select className="rm-input" value={tier} onChange={(event) => { setTier(event.target.value); setError(""); }} disabled={saving} data-testid="admin-label-sub-tier-select">{Object.entries(PACKAGE_NAMES).map(([key, name]) => <option key={key} value={key}>{name}</option>)}</select></label>
    {tier !== "pay_per_release" && <label className="block"><span className="rm-label">{t("Masa Berlaku Sampai")}</span><input className="rm-input" type="date" value={expiry} onChange={(event) => setExpiry(event.target.value)} disabled={saving} data-testid="admin-label-sub-expiry-input" /></label>}
    <label className="block"><span className="rm-label">{t("Alasan Perubahan")}</span><textarea className="rm-input min-h-[80px]" value={reason} onChange={(event) => setReason(event.target.value)} minLength={3} maxLength={1000} disabled={saving} data-testid="admin-label-sub-reason" /></label>
    {error && !confirming && <div role="alert" className="text-sm text-red-400" data-testid="admin-label-sub-error">{error}</div>}
    <button type="button" className="rm-btn-primary inline-flex items-center gap-2 text-sm" disabled={!valid || saving} onClick={() => setConfirming(true)} data-testid="admin-label-sub-save">{t(isRequest ? "Ajukan Perubahan" : "Tinjau Perubahan")}<ArrowRight className="h-4 w-4" /></button>
    <Dialog open={confirming} onOpenChange={(open) => { if (!saving) setConfirming(open); }}><DialogContent className="ui-menu max-h-[90dvh] w-[calc(100%-2rem)] max-w-lg overflow-y-auto rounded-lg" data-testid="admin-label-package-confirm-dialog" closeTestId="admin-label-package-confirm-close">
      <DialogHeader><DialogTitle>{t(isRequest ? "Konfirmasi Pengajuan Paket" : "Konfirmasi Perubahan Paket")}</DialogTitle><DialogDescription>{t(isRequest ? "Paket live tidak berubah sampai Super Admin menyetujui permintaan." : "Perubahan langsung berlaku tanpa membuat tagihan otomatis. Invoice yang sudah ada tidak berubah.")}</DialogDescription></DialogHeader>
      <div className="space-y-3 text-sm"><strong className="block break-words" translate="no" data-testid="admin-label-package-confirm-name">{label.label_name}</strong><div className="flex flex-wrap items-center gap-2" data-testid="admin-label-package-confirm-change"><span>{PACKAGE_NAMES[current]}</span><ArrowRight className="h-4 w-4" /><strong>{PACKAGE_NAMES[tier]}</strong></div>{tier !== "pay_per_release" && <p data-testid="admin-label-package-confirm-expiry">{t("Masa Berlaku Sampai")}: {expiry} · 23:59 WIB</p>}<p className="whitespace-pre-wrap break-words" translate="no" data-testid="admin-label-package-confirm-reason">{reason}</p></div>
      {error && <p role="alert" className="text-sm text-red-400" data-testid="admin-label-package-confirm-error">{error}</p>}
      <div className="flex flex-wrap justify-end gap-2"><button type="button" className="rm-btn-ghost" disabled={saving} onClick={() => setConfirming(false)} data-testid="admin-label-package-confirm-cancel">{t("Batal")}</button><button type="button" className="rm-btn-primary inline-flex items-center gap-2" disabled={saving} onClick={save} data-testid="admin-label-package-confirm-submit"><Check className="h-4 w-4" />{t(saving ? "Menyimpan…" : (isRequest ? "Kirim Permintaan" : "Konfirmasi & Simpan"))}</button></div>
    </DialogContent></Dialog>
  </section>;
};