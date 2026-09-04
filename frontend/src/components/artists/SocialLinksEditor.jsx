import React from "react";
import { Plus, Trash2 } from "lucide-react";
import { SOCIAL_PLATFORM_OPTIONS, newSocialLink } from "@/constants/socialPlatforms";

export const SocialLinksEditor = ({ links, onChange, prefix }) => {
  const update = (index, patch) => onChange(links.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  return <div className="space-y-3" data-testid={`${prefix}-social-links-editor`}>
    <div className="flex items-center justify-between gap-3"><div><div className="rm-label">Tautan Media Sosial</div><p className="text-xs text-zinc-500">Minimal satu tautan aktif wajib disertakan.</p></div><button type="button" className="rm-btn-ghost inline-flex items-center gap-2 text-xs" onClick={() => onChange([...links, newSocialLink()])} disabled={links.length >= 10} data-testid={`${prefix}-social-add-button`}><Plus className="h-3.5 w-3.5" /> Tambah Tautan</button></div>
    <div className="space-y-2">{links.map((item, index) => {
      const option = SOCIAL_PLATFORM_OPTIONS.find((entry) => entry.value === item.platform);
      return <div className="grid gap-2 md:grid-cols-[160px_minmax(0,1fr)_40px] rm-fade-up" key={item.client_id || `${item.platform}-${index}`} data-testid={`${prefix}-social-row-${index}`}>
        <select className="rm-input" value={item.platform} onChange={(event) => update(index, { platform: event.target.value })} data-testid={`${prefix}-social-platform-${index}`}>{SOCIAL_PLATFORM_OPTIONS.map((entry) => <option key={entry.value} value={entry.value}>{entry.label}</option>)}</select>
        <input type="url" className="rm-input" value={item.url} placeholder={option?.placeholder} onChange={(event) => update(index, { url: event.target.value })} required data-testid={`${prefix}-social-url-${index}`} />
        <button type="button" title="Hapus tautan" className="grid h-11 w-10 place-items-center rounded-md text-red-300 transition-colors hover:bg-red-500/10 disabled:opacity-30" disabled={links.length === 1} onClick={() => onChange(links.filter((_, itemIndex) => itemIndex !== index))} data-testid={`${prefix}-social-remove-${index}`}><Trash2 className="h-4 w-4" /></button>
      </div>;
    })}</div>
  </div>;
};