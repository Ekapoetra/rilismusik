import React from "react";

/** Shared page header: eyebrow + display title + optional subtitle + actions.
 * `bordered` matches the admin-page style (border-bottom); label pages use the default. */
export default function PageHeader({ eyebrow, title, icon: Icon, iconClassName = "text-pink-400", sub, bordered = false, children }) {
  return (
    <header className={`flex flex-wrap items-center justify-between gap-3 ${bordered ? "items-start gap-4 border-b border-white/10 pb-5" : ""}`}>
      <div>
        {eyebrow && <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">{eyebrow}</div>}
        <h1 className={`font-display text-3xl font-extrabold ${bordered ? "mt-1 flex items-center gap-2" : "tracking-tighter"}`}>
          {Icon && <Icon className={`h-6 w-6 ${iconClassName}`} />}{title}
        </h1>
        {sub && <p className={`text-sm text-zinc-400 ${bordered ? "mt-2 max-w-2xl" : "mt-1"}`}>{sub}</p>}
      </div>
      {children}
    </header>
  );
}
