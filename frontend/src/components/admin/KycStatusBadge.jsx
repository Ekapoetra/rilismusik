import React from "react";
import { AlertTriangle, CheckCircle2, Clock3, ShieldAlert } from "lucide-react";

const STATUS = {
  verified: { label: "Terverifikasi", icon: CheckCircle2, className: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200" },
  pending_review: { label: "Menunggu Review", icon: Clock3, className: "border-amber-400/30 bg-amber-400/10 text-amber-200" },
  rejected: { label: "Ditolak", icon: ShieldAlert, className: "border-red-400/30 bg-red-400/10 text-red-200" },
  needs_update: { label: "Perlu Diperbarui", icon: AlertTriangle, className: "border-orange-400/30 bg-orange-400/10 text-orange-200" },
  incomplete: { label: "Belum Lengkap", icon: AlertTriangle, className: "border-white/10 bg-white/[0.04] text-zinc-400" },
  unverified: { label: "Belum Lengkap", icon: AlertTriangle, className: "border-white/10 bg-white/[0.04] text-zinc-400" },
};

export const KycStatusBadge = ({ status, reason, testId }) => {
  const config = STATUS[status] || STATUS.incomplete;
  const Icon = config.icon;
  return <span title={reason || config.label} className={`inline-flex max-w-full items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] font-bold ${config.className}`} data-testid={testId}><Icon className="h-3.5 w-3.5 shrink-0" /><span className="truncate">{config.label}</span></span>;
};