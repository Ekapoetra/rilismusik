// Shared UI helpers for the Performance (KPI) pages — no business logic here,
// only presentation mapping. All thresholds/categories come from the backend config.
export const CATEGORY_COLOR = {
  excellent: "bg-emerald-500/15 text-emerald-300 border-emerald-400/30",
  strong: "bg-sky-500/15 text-sky-300 border-sky-400/30",
  meets: "bg-indigo-500/15 text-indigo-300 border-indigo-400/30",
  needs_improvement: "bg-amber-500/15 text-amber-300 border-amber-400/30",
  below: "bg-red-500/15 text-red-300 border-red-400/30",
};

export const CONFIDENCE_LABEL = {
  high: ["Tinggi", "High"],
  moderate: ["Sedang", "Moderate"],
  low: ["Rendah", "Low"],
  insufficient: ["Data Kurang", "Insufficient"],
};

export const CONFIDENCE_COLOR = {
  high: "text-emerald-300",
  moderate: "text-sky-300",
  low: "text-amber-300",
  insufficient: "text-zinc-500",
};

export const scoreColor = (score) => {
  if (score === null || score === undefined) return "text-zinc-500";
  if (score >= 90) return "text-emerald-300";
  if (score >= 75) return "text-sky-300";
  if (score >= 60) return "text-indigo-300";
  if (score >= 40) return "text-amber-300";
  return "text-red-300";
};

export const catName = (category, locale) =>
  !category ? null : locale === "en" ? category.name_en : category.name_id;
