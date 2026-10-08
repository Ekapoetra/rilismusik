import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Check, X } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { openXenditCheckout } from "@/api/payments";
import { useAuth } from "@/api/AuthContext";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { PLAN_TIERS, planFor, planPrice } from "@/lib/plans";

const idr = (value) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(value || 0);
const day = (value) => new Date(value).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Jakarta" });

// Current package from the account entitlements (Multi Label authority included).
export function useLabelPlan() {
  const { user } = useAuth();
  const [state, setState] = useState(null);
  useEffect(() => {
    let active = true;
    api.get("/label/account").then(({ data }) => { if (active) setState(data?.entitlements || null); }).catch(() => { if (active) setState(null); });
    return () => { active = false; };
  }, [user?.id, user?.active_label_id]);
  return state;
}

export function PlanBadge({ pkg, className = "" }) {
  return <span className={`v13-plan-badge ${className}`} data-plan={planFor(pkg).id} translate="no">{planFor(pkg).name}</span>;
}

export function PlansDialog({ entitlements, onClose }) {
  const { t } = useAppPreferences();
  const [pricing, setPricing] = useState(null);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState("");
  const current = planFor(entitlements?.package);
  useEffect(() => { api.get("/cms/landing").then(({ data }) => setPricing(data?.pricing || {})).catch(() => setPricing({})); }, []);
  useEffect(() => {
    const onKey = (event) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const checkout = async (tier) => {
    setBusy(tier.id); setError("");
    try {
      const { data } = await api.post("/payments/subscription", { tier: tier.legacy });
      await openXenditCheckout(data.id);
    } catch (requestError) {
      setError(formatApiError(requestError.response?.data?.detail || requestError.message));
      setBusy(null);
    }
  };
  const action = (tier) => {
    const isCurrent = tier.id === current.id;
    if (tier.id === "basic") return <p className="text-xs text-[var(--ui-muted)]">{current.id === "basic" ? t("Paket aktif tanpa masa berlaku.") : t("Berlaku otomatis setelah masa paket berakhir.")}</p>;
    const rank = PLAN_TIERS.indexOf(tier), currentRank = PLAN_TIERS.indexOf(current);
    if (rank < currentRank && entitlements?.active) return <p className="text-xs text-[var(--ui-muted)]">{t("Bisa dipilih setelah masa paket sekarang berakhir.")}</p>;
    if (tier.id === "business") return isCurrent ? null : <Link to="/ajukan-multi-label" className="v13-plan-cta" onClick={onClose}>{t("Ajukan Business")}</Link>;
    return <button type="button" className="v13-plan-cta" disabled={Boolean(busy)} onClick={() => checkout(tier)} data-testid={`plan-checkout-${tier.id}`}>{busy === tier.id ? t("Membuka Xendit…") : isCurrent ? t("Perpanjang") : t(`Pilih ${tier.name}`)}</button>;
  };
  return <div className="v13-dialog" role="dialog" aria-modal="true" aria-label={t("Paketmu")} data-testid="plans-dialog">
    <button type="button" className="v13-dialog-backdrop" aria-label={t("Tutup")} onClick={onClose} />
    <div className="v13-dialog-panel">
      <div className="flex items-start justify-between gap-4">
        <div><h2 className="text-2xl font-medium tracking-tight">{t("Paketmu")}</h2>
          <p className="mt-1 text-sm text-[var(--ui-muted)]">{entitlements?.active && entitlements?.subscription_expires_at ? `${t("Berlaku sampai")} ${day(entitlements.subscription_expires_at)}.` : current.id === "basic" ? t("Bayar sesuai jumlah lagu.") : ""} {t("Paket dan hak yang sudah dibeli tetap berlaku sampai masa aktifnya berakhir.")}</p></div>
        <button type="button" className="v13-chevron" onClick={onClose} aria-label={t("Tutup")}><X /></button>
      </div>
      {error && <p role="alert" className="mt-4 text-sm text-[var(--v13-urgent)]">{error}</p>}
      <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {PLAN_TIERS.map((tier) => <div key={tier.id} className={`v13-plan-card ${tier.id === current.id ? "is-current" : ""}`} data-testid={`plan-card-${tier.id}`}>
          {tier.id === current.id && <span className="v13-your-plan">{t("Paket Anda")}</span>}
          <PlanBadge pkg={tier.legacy} />
          <div className="mt-5"><strong className="text-2xl font-normal tracking-tight">{pricing ? idr(planPrice(tier, pricing)) : "…"}</strong><span className="text-sm text-[var(--ui-muted)]"> / {t(tier.unit)}</span></div>
          <p className="mt-2 min-h-[40px] text-sm text-[var(--ui-muted)]">{t(tier.summary)}</p>
          <ul className="mt-4 flex-1 space-y-2 text-sm">{tier.features.map((feature) => <li key={feature} className="flex gap-2"><Check className="mt-0.5 h-4 w-4 shrink-0 text-[var(--v13-up)]" />{t(feature)}</li>)}</ul>
          <div className="mt-5">{action(tier)}</div>
        </div>)}
      </div>
    </div>
  </div>;
}

// Header chip: current package plus "Ubah paket", as in the prototype's label header.
export function PlanChip() {
  const { t } = useAppPreferences();
  const entitlements = useLabelPlan();
  const [open, setOpen] = useState(false);
  if (!entitlements) return null;
  return <>
    <button type="button" className="v13-plan-chip" onClick={() => setOpen(true)} data-testid="plan-chip"><PlanBadge pkg={entitlements.package} /><span>{t("Ubah paket")}</span></button>
    {open && <PlansDialog entitlements={entitlements} onClose={() => setOpen(false)} />}
  </>;
}
