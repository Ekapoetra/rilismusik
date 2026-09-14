import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BadgeCheck } from "lucide-react";
import { fileUrl } from "@/api/client";
import { LabelLogo } from "@/components/shared/LabelLogo";

const DEFAULT_DESKTOP = "/hero/label-hero-desktop.webp";
const DEFAULT_MOBILE = "/hero/label-hero-mobile.webp";
const DEFAULT_HEADLINE = "Musik menghubungkan lebih banyak cerita";
const DEFAULT_CTA_TEXT = "Ajukan Rilisan";
const DEFAULT_CTA_TARGET = "/label/releases/upload";

function safeTarget(target) {
  if (typeof target === "string" && target.startsWith("/") && !target.startsWith("//")) return target;
  return DEFAULT_CTA_TARGET;
}

export function LabelHero({ hero, label, verified, subline }) {
  const cfg = (hero && hero.is_active) ? hero : {};
  const desktopSrc = fileUrl(cfg.desktop_image) || DEFAULT_DESKTOP;
  const mobileSrc = fileUrl(cfg.mobile_image) || fileUrl(cfg.desktop_image) || DEFAULT_MOBILE;
  const headline = cfg.headline || DEFAULT_HEADLINE;
  const subheadline = cfg.subheadline || "";
  const ctaText = cfg.cta_text || DEFAULT_CTA_TEXT;
  const ctaTarget = safeTarget(cfg.cta_target || DEFAULT_CTA_TARGET);
  const overlay = Math.min(Math.max(Number(cfg.overlay_opacity ?? 55), 0), 90) / 100;
  const alt = cfg.alt_text || "";

  return (
    <section className="relative isolate overflow-hidden rounded-2xl border border-[color:rgba(170,120,255,0.18)]" data-testid="label-dashboard-hero">
      {/* Image layer (mobile vs desktop) */}
      <img src={mobileSrc} alt={alt} aria-hidden={alt ? undefined : true} loading="eager" className="absolute inset-0 h-full w-full object-cover md:hidden" onError={(e) => { e.currentTarget.style.visibility = "hidden"; }} />
      <img src={desktopSrc} alt={alt} aria-hidden={alt ? undefined : true} loading="eager" className="absolute inset-0 hidden h-full w-full object-cover md:block" onError={(e) => { e.currentTarget.style.visibility = "hidden"; }} />
      {/* Gradient fallback + overlay */}
      <div className="absolute inset-0 -z-[1] bg-gradient-to-br from-[#171226] via-[#0F1219] to-[#0B0D12]" />
      <div className="absolute inset-0" style={{ background: `linear-gradient(100deg, rgba(11,13,18,${Math.min(overlay + 0.3, 0.95)}) 0%, rgba(11,13,18,${overlay}) 50%, rgba(11,13,18,0.12) 100%)` }} />

      <div className="relative flex min-h-[220px] flex-col justify-between gap-6 p-5 sm:p-7 md:min-h-[280px] md:p-9">
        {/* Identity */}
        <div className="flex items-center gap-3">
          <LabelLogo src={label?.logo_url} labelName={label?.label_name} className="h-12 w-12 md:h-14 md:w-14" testId="label-hero-logo" />
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="truncate font-display text-base font-extrabold tracking-tight text-white md:text-lg" data-testid="label-hero-name" translate="no">{label?.label_name}</span>
              {verified && <BadgeCheck className="h-4 w-4 shrink-0 text-sky-400" data-testid="label-hero-verified" />}
            </div>
            {subline && <div className="truncate text-xs text-zinc-300/90">{subline}</div>}
          </div>
        </div>

        {/* Copy + CTA */}
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div className="max-w-2xl">
            <h1 className="font-display text-2xl font-extrabold leading-[1.1] tracking-tight text-white sm:text-3xl md:text-4xl" data-testid="label-hero-headline">{headline}</h1>
            {subheadline && <p className="mt-2 max-w-xl text-sm text-zinc-300">{subheadline}</p>}
          </div>
          <Link to={ctaTarget} data-testid="label-hero-cta" className="inline-flex w-fit shrink-0 items-center gap-2 rounded-full bg-gradient-to-r from-[#FF1F8E] to-[#A24EFF] px-6 py-3 text-sm font-bold text-white shadow-lg shadow-[#FF1F8E]/20 transition-transform hover:scale-[1.03]">
            + {ctaText} <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </section>
  );
}
