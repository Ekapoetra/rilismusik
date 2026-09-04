import React from "react";
import { ExternalLink } from "lucide-react";
import { socialPlatformLabel } from "@/constants/socialPlatforms";

export const SocialLinksList = ({ links = [], prefix, emptyText = "Belum ada tautan sosial" }) => {
  const safeLinks = links.filter((item) => { try { return ["http:", "https:"].includes(new URL(item.url).protocol); } catch { return false; } });
  if (!safeLinks.length) return <span className="text-xs text-amber-300" data-testid={`${prefix}-empty`}>{emptyText}</span>;
  return <div className="flex flex-wrap gap-2" data-testid={`${prefix}-list`}>{safeLinks.map((item, index) => <a key={`${item.platform}-${item.url}-${index}`} href={item.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-md border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-xs font-semibold text-zinc-300 transition-colors hover:border-white/25 hover:text-white" data-testid={`${prefix}-link-${index}`}>{socialPlatformLabel(item.platform)}<ExternalLink className="h-3 w-3" /></a>)}</div>;
};