import React from "react";
import { AlertTriangle, CheckCircle2, Clock3, ShieldCheck } from "lucide-react";
import { KycChecklist } from "@/components/label/KycChecklist";
import { KycUploadField } from "@/components/label/KycUploadField";

const STATUS = {
  verified: { label: "Terverifikasi", icon: CheckCircle2, tone: "border-emerald-400/30 bg-emerald-400/[0.07] text-emerald-200" },
  pending_review: { label: "Menunggu Review Admin", icon: Clock3, tone: "border-amber-400/30 bg-amber-400/[0.07] text-amber-100" },
  rejected: { label: "Ditolak — perlu diperbaiki", icon: AlertTriangle, tone: "border-red-400/30 bg-red-400/[0.07] text-red-100" },
  needs_update: { label: "Data perlu dilengkapi kembali", icon: AlertTriangle, tone: "border-amber-400/30 bg-amber-400/[0.07] text-amber-100" },
  incomplete: { label: "Belum Lengkap", icon: ShieldCheck, tone: "border-white/10 bg-white/[0.03] text-zinc-200" },
};

export const KycPanel = ({ profile, onReload }) => {
  const kyc = profile.kyc || {};
  const status = STATUS[kyc.status] || STATUS.incomplete;
  const StatusIcon = status.icon;
  const ktpUrl = kyc.document ? `/api/label/kyc/ktp?v=${encodeURIComponent(kyc.document.uploaded_at || "current")}` : null;
  const ktpDisabled = !kyc.prerequisites_complete || ["pending_review", "verified"].includes(kyc.status);

  return (
    <section className="rm-card overflow-hidden" data-testid="label-kyc-panel">
      <div className={`border-b p-6 md:p-8 ${status.tone}`} data-testid="label-kyc-status-banner">
        <div className="flex items-start gap-4"><StatusIcon className="mt-0.5 h-6 w-6 shrink-0" /><div><div className="text-xs font-bold uppercase tracking-widest">Aktivasi Akun</div><h2 className="mt-1 font-display text-2xl font-extrabold" data-testid="label-kyc-status-text">{status.label}</h2><p className="mt-2 max-w-2xl text-sm leading-relaxed opacity-80">Lengkapi identitas label agar fitur rilisan, royalti, withdraw, WAMI, support, dan invoice dapat digunakan.</p></div></div>
        {kyc.status === "rejected" && <blockquote className="mt-5 border-l-2 border-red-300/70 bg-black/20 px-4 py-3 text-sm" data-testid="label-kyc-rejection-reason"><span className="block text-xs font-bold uppercase tracking-widest text-red-300">Alasan penolakan</span><span className="mt-1 block text-red-100">{kyc.rejection_reason}</span></blockquote>}
      </div>
      <div className="space-y-7 p-6 md:p-8">
        <KycChecklist kyc={kyc} />
        <div className="grid gap-8 lg:grid-cols-2">
          <KycUploadField kind="logo" title="Logo Label" description="Logo tampil pada profil label dan dapat diperbarui kapan saja." maxMb={5} currentUrl={profile.logo_url} onUploaded={onReload} />
          <KycUploadField kind="ktp" title="KTP Penanggung Jawab" description={kyc.prerequisites_complete ? "File disimpan privat dan hanya dapat dilihat oleh Anda serta reviewer KYC." : "Simpan profil, logo, kontrak, dan rekening terlebih dahulu sebelum mengunggah KTP."} maxMb={10} currentUrl={ktpUrl} disabled={ktpDisabled} onUploaded={onReload} />
        </div>
      </div>
    </section>
  );
};