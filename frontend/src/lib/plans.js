// V13 package names over the existing production packages. Only the names change:
// prices, expiry and benefits still come from the stored package and its config.
export const PLAN_TIERS = [
  {
    id: "basic", name: "Basic", legacy: "pay_per_release", priceKey: "pay_per_release_price", defaultPrice: 35000, unit: "lagu",
    summary: "Bayar layanan sesuai kebutuhan, tanpa berlangganan.",
    features: ["Katalog, draft & pengajuan rilisan", "Biaya per lagu saat rilisan diajukan", "Mode Express/MAX dengan token"],
  },
  {
    id: "studio", name: "Studio", legacy: "annual_normal", priceKey: "annual_normal_price", defaultPrice: 350000, unit: "tahun",
    summary: "Rilis tanpa biaya per lagu selama setahun.",
    features: ["Semua manfaat Basic", "Rilisan Standar tanpa biaya per lagu", "Prioritas pemeriksaan"],
  },
  {
    id: "pro", name: "Pro", legacy: "annual_vip", priceKey: "annual_subscription_price", defaultPrice: 500000, unit: "tahun",
    summary: "Studio plus WAMI dan layanan tambahan gratis.",
    features: ["Semua manfaat Studio", "Registrasi WAMI gratis", "Layanan tambahan gratis"],
  },
  {
    id: "business", name: "Business", legacy: "multi_label", priceKey: "multi_label_price", defaultPrice: 1500000, unit: "tahun",
    summary: "Kelola beberapa label dari satu akun master.",
    features: ["Semua manfaat Pro", "Kelola banyak label dalam satu login", "Satu rekening & pencairan gabungan"],
  },
];

const BY_LEGACY = Object.fromEntries(PLAN_TIERS.map((tier) => [tier.legacy, tier]));

// Accepts a legacy package key (pay_per_release, annual_normal, annual_vip, multi_label).
export const planFor = (pkg) => BY_LEGACY[pkg] || BY_LEGACY.pay_per_release;
export const planName = (pkg) => planFor(pkg).name;

// The package stored on a label document; expired annual packages fall back to Basic.
export function labelPackage(label) {
  if (!label) return "pay_per_release";
  if (label.payment_type !== "annual_subscription" && !label.subscription_tier) return "pay_per_release";
  const expires = label.subscription_expires_at ? new Date(label.subscription_expires_at) : null;
  const active = label.subscription_status === "active" && (!expires || expires > new Date());
  return active ? (label.subscription_tier || "annual_normal") : "pay_per_release";
}

export const planPrice = (tier, pricing) => Number(pricing?.[tier.priceKey]) || tier.defaultPrice;
