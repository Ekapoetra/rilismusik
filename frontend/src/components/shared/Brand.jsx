import React from "react";

/** Logo mark — icon-only (rounded square with gradient RM inside).
 *  Used in nav, sidebar, mobile bar, auth forms, dashboards. */
export function LogoMark({ size = 40, className = "" }) {
  return (
    <img
      src="/brand/logo-icon-gradient.png"
      alt="RILIS MUSIK"
      width={size}
      height={size}
      className={className}
      style={{ display: "block" }}
    />
  );
}

/** Full lockup — RM gradient + RILISMUSIK text underneath.
 *  Used on Landing hero and auth pages. */
export function LogoFull({ width = 220, className = "" }) {
  return (
    <img
      src="/brand/logo-full.png"
      alt="RILIS MUSIK"
      width={width}
      className={className}
      style={{ display: "block" }}
    />
  );
}

/** Brand wordmark inline (icon + RILIS MUSIK text right of it) — for navbars/sidebars. */
export function BrandInline({ size = 38, white = true, subtitle = null }) {
  return (
    <div className="flex items-center gap-2.5">
      <LogoMark size={size} />
      <div className="leading-none">
        <div className={`font-display font-extrabold tracking-tight text-base md:text-lg ${white ? "text-white" : ""}`}>
          RILIS<span className="opacity-80 font-bold ml-0.5">MUSIK</span>
        </div>
        {subtitle && <div className="text-[11px] mt-1 text-zinc-400">{subtitle}</div>}
      </div>
    </div>
  );
}
