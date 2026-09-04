import React from "react";
import { MessageCircle } from "lucide-react";
import { releaseWhatsAppUrl } from "@/utils/releasePresentation";

export const WhatsAppFollowUpButton = ({ release }) => {
  const url = releaseWhatsAppUrl(release);
  if (!url) return <span className="text-xs text-zinc-500" data-testid="admin-release-whatsapp-unavailable">Nomor WhatsApp label belum tersedia.</span>;
  return <a href={url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-md border border-emerald-400/30 bg-emerald-400/[0.08] px-4 py-2 text-sm font-bold text-emerald-200 transition-colors hover:bg-emerald-400/[0.14]" data-testid="admin-release-whatsapp-followup"><MessageCircle className="h-4 w-4" /> Hubungi Label</a>;
};