import React from "react";
import { Info } from "lucide-react";
import { fileUrl } from "@/api/client";
import { METADATA_FIELDS } from "@/components/label/tickets/ticketFormConfig";

export const TicketRequestSummary = ({ ticket, prefix }) => {
  const urls = ticket.youtube_urls?.length ? ticket.youtube_urls : ticket.youtube_url ? [ticket.youtube_url] : [];
  const labels = Object.fromEntries(METADATA_FIELDS.map(([label, key]) => [key, label]));
  return <div className="min-w-0 space-y-4 text-sm" data-testid={`${prefix}-request-summary`}>
    {ticket.reason && <div><div className="text-xs text-zinc-500">{ticket.category === "edit_metadata" ? "Alasan Perubahan" : "Alasan"}</div><div className="mt-1 whitespace-pre-wrap break-words text-zinc-200" data-testid={`${prefix}-reason`}>{ticket.reason}</div></div>}
    {urls.length > 0 && <div><div className="mb-2 text-xs text-zinc-500">Link Video YouTube ({urls.length})</div><ul className="space-y-2">{urls.map((url, index) => <li key={`${url}-${index}`}><a href={url} target="_blank" rel="noreferrer" className="block break-all font-semibold text-sky-300 transition-colors hover:text-sky-200" data-testid={index === 0 ? `${prefix}-youtube-link` : `${prefix}-youtube-link-${index + 1}`}>{index + 1}. {url} ↗</a></li>)}</ul></div>}
    {ticket.new_metadata && <section><h3 className="mb-3 text-xs text-zinc-500">Metadata Baru</h3><dl className="divide-y divide-white/10">{Object.entries(ticket.new_metadata).map(([key, value]) => <div key={key} className="min-w-0 py-2"><dt className="text-xs text-zinc-500">{labels[key] || key}</dt>{ticket.original_metadata && <dd className="mt-1 break-words text-xs text-zinc-500 line-through" data-testid={`${prefix}-metadata-before-${key}`}>{ticket.original_metadata[key] || "—"}</dd>}<dd className="mt-1 break-words" data-testid={`${prefix}-metadata-after-${key}`}>{typeof value === "object" ? JSON.stringify(value) : String(value ?? "") || "—"}</dd></div>)}</dl></section>}
    {ticket.new_audio_url && <a href={fileUrl(ticket.new_audio_url)} target="_blank" rel="noreferrer" className="block font-semibold text-sky-300" data-testid={`${prefix}-new-audio`}>Buka WAV Baru ↗</a>}
    {ticket.new_cover_url && <img src={fileUrl(ticket.new_cover_url)} alt="Cover baru yang diajukan" className="aspect-square w-32 max-w-full object-contain" data-testid={`${prefix}-new-cover`} />}
    {ticket.originality_declared && <div className="flex items-center gap-2 text-xs text-emerald-300" data-testid={`${prefix}-originality`}><Info className="h-3 w-3 shrink-0" /> Originalitas dinyatakan ✓</div>}
  </div>;
};