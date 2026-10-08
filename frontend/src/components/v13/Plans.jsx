import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Check, X } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { openXenditCheckout } from "@/api/payments";
import { useAuth } from "@/api/AuthContext";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { PLAN_TIERS, planFor, planPrice } from "@/lib/plans";
import { TokenDialog, useTokenWallet } from "@/components/v13/Tokens";

const idr = (value) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(value || 0);
const day = (value) => new Date(value).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Jakarta" });
export const PLAN_EVENT = "rilismusik:plan-changed";

// Current package from the account entitlements (Multi Label authority included).
export function useLabelPlan() {
  const { user } = useAuth();
  const [state, setState] = useState(null);
  const load = useCallback(() => api.get("/label/account").then(({ data }) => setState(data?.entitlements || null)).catch(() => setState(null)), []);
  useEffect(() => {
    load();
    window.addEventListener(PLAN_EVENT, load);
    return () => window.removeEventListener(PLAN_EVENT, load);
  }, [load, user?.id, user?.active_label_id]);
  return state;
}

export function PlanBadge({ pkg, className = "" }) {
  return <span className={`v13-plan-badge ${className}`} data-plan={planFor(pkg).id} translate="no">{planFor(pkg).name}</span>;
}

function BasicConfirm({ end, onBack, onDone }) {
  const { t } = useAppPreferences();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const schedule = async () => {
    setBusy(true); setError("");
    try { await api.post("/label/plan/schedule-basic"); window.dispatchEvent(new Event(PLAN_EVENT)); onDone(); }
    catch (requestError) { setError(formatApiError(requestError.response?.data?.detail)); setBusy(false); }
  };
  return <div className="v13-dialog" role="dialog" aria-modal="true" aria-label={t("Gunakan Basic")} data-testid="plan-basic-confirm">
    <button type="button" className="v13-dialog-backdrop" aria-label={t("Tutup")} onClick={onBack} />
    <div className="v13-dialog-panel" style={{ width: "min(480px, 100%)" }}>
      <h2 className="text-2xl font-medium tracking-tight">{t("Gunakan Basic")}</h2>
      <p className="mt-3 text-sm text-[var(--ui-muted)]">{t("Paketmu tetap berlaku hingga berakhir.")} {t("Basic dimulai pada")} {day(end)}. {t("Katalog, royalti, dan token pembelian tetap menjadi milikmu.")}</p>
      {error && <p role="alert" className="mt-3 text-sm text-[var(--v13-urgent)]">{error}</p>}
      <div className="mt-6 flex flex-wrap justify-end gap-3"><button type="button" className="rounded-full px-4 py-2.5 text-sm text-[var(--ui-muted)] hover:text-[var(--ui-text)]" onClick={onBack}>{t("Kembali ke pilihan paket")}</button><button type="button" className="v13-plan-cta px-5" style={{ width: "auto" }} disabled={busy} onClick={schedule} data-testid="plan-basic-schedule">{t("Jadwalkan Basic")}</button></div>
    </div>
  </div>;
}

export function PlansDialog({ entitlements, onClose }) {
  const { t } = useAppPreferences();
  const [pricing, setPricing] = useState(null);
  const [group, setGroup] = useState(entitlements?.package === "multi_label" ? "multi" : "single");
  const [periods, setPeriods] = useState({});
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState("");
  const [confirmBasic, setConfirmBasic] = useState(false);
  const [buyTokens, setBuyTokens] = useState(false);
  const { wallet } = useTokenWallet();
  const current = planFor(entitlements?.package);
  const scheduled = entitlements?.scheduled_change;
  useEffect(() => { api.get("/cms/landing").then(({ data }) => setPricing(data?.pricing || {})).catch(() => setPricing({})); }, []);
  useEffect(() => {
    const onKey = (event) => { if (event.key === "Escape" && !confirmBasic && !buyTokens) onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, confirmBasic, buyTokens]);
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
  const cancelBasic = async () => {
    setError("");
    try { await api.delete("/label/plan/scheduled"); window.dispatchEvent(new Event(PLAN_EVENT)); }
    catch (requestError) { setError(formatApiError(requestError.response?.data?.detail)); }
  };
  const tiers = PLAN_TIERS.filter((tier) => (group === "multi" ? true : tier.id !== "business"));
  const action = (tier) => {
    const isCurrent = tier.id === current.id;
    const rank = PLAN_TIERS.indexOf(tier), currentRank = PLAN_TIERS.indexOf(current);
    if (tier.id === "basic") {
      if (isCurrent) return <button type="button" className="v13-plan-cta" onClick={() => setBuyTokens(true)} data-testid="plan-cta-basic">{t("Beli token")}</button>;
      return <button type="button" className="v13-plan-cta" disabled={Boolean(scheduled)} onClick={() => setConfirmBasic(true)} data-testid="plan-cta-basic">{t("Gunakan Basic")}</button>;
    }
    if ((periods[tier.id] || "annual") === "monthly") return <p className="text-xs text-[var(--ui-muted)]">{t("Periode ini belum dapat dibeli.")}</p>;
    if (tier.id === "business" && !isCurrent) return <Link to="/ajukan-multi-label" className="v13-plan-cta" onClick={onClose} data-testid="plan-cta-business">{t("Beralih ke Business")}</Link>;
    const label = isCurrent ? t("Perpanjang paket") : `${t("Beralih ke")} ${tier.name}`;
    return <>
      <button type="button" className="v13-plan-cta" disabled={Boolean(busy) || Boolean(scheduled)} onClick={() => checkout(tier)} data-testid={`plan-checkout-${tier.id}`}>{busy === tier.id ? t("Membuka Xendit…") : label}</button>
      {!isCurrent && rank < currentRank && entitlements?.active && <p className="mt-2 text-xs text-[var(--ui-muted)]">{t("Dimulai saat paket sekarang berakhir.")}</p>}
    </>;
  };
  return <div className="v13-dialog" role="dialog" aria-modal="true" aria-label={t("Rilis Musik Service Plans")} data-testid="plans-dialog">
    <button type="button" className="v13-dialog-backdrop" aria-label={t("Tutup")} onClick={onClose} />
    <div className="v13-dialog-panel">
      <div className="flex items-start justify-between gap-4">
        <div><h2 className="text-3xl font-normal tracking-tight">Rilis Musik Service Plans</h2>
          <p className="mt-2 text-sm text-[var(--ui-muted)]">{t("Pilih alat dan layanan yang paling sesuai dengan cara labelmu bekerja.")}</p>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-sm"><PlanBadge pkg={entitlements?.package} /><span className="text-[var(--ui-muted)]">{current.id === "basic" ? t("Bayar sesuai jumlah lagu") : entitlements?.subscription_expires_at ? `${t("Berlaku sampai")} ${day(entitlements.subscription_expires_at)}` : ""}</span></div>
        </div>
        <button type="button" className="v13-chevron" onClick={onClose} aria-label={t("Tutup")}><X /></button>
      </div>
      {scheduled && <div className="mt-4 flex flex-wrap items-center gap-3 rounded-2xl bg-[var(--v13-pill-blue-bg)] px-4 py-3 text-sm" data-testid="plan-scheduled-banner"><PlanBadge pkg={scheduled.tier} /><span>{t("Mulai")} {day(scheduled.starts_at)}. {t("Paketmu sekarang tetap berlaku sampai tanggal tersebut.")}</span>{scheduled.source === "basic" && <button type="button" className="ml-auto text-sm underline" onClick={cancelBasic}>{t("Batalkan jadwal")}</button>}</div>}
      <div className="mt-5 flex justify-center"><div className="v13-switch" data-mode={group === "multi" ? "staff" : "platform"} style={{ width: 260, margin: 0 }} role="group" aria-label={t("Jumlah label")}>{[["single", "1 Label"], ["multi", "Multi Label"]].map(([key, name]) => <button key={key} type="button" aria-pressed={group === key} onClick={() => setGroup(key)} data-testid={`plans-group-${key}`}>{t(name)}</button>)}</div></div>
      {error && <p role="alert" className="mt-4 text-sm text-[var(--v13-urgent)]">{error}</p>}
      <div className={`mt-6 grid gap-3 md:grid-cols-2 ${tiers.length > 3 ? "xl:grid-cols-4" : "xl:grid-cols-3"}`}>
        {tiers.map((tier) => {
          const period = periods[tier.id] || "annual";
          return <div key={tier.id} className={`v13-plan-card v13-fade-in ${tier.id === current.id ? "is-current" : ""}`} data-testid={`plan-card-${tier.id}`}>
            {tier.id === current.id && <span className="v13-your-plan">{t("Paket Anda")}</span>}
            <div className="flex items-center gap-2 text-xs text-[var(--ui-muted)]"><span>{tier.id === "business" ? "Multi Label" : "Single Label"}</span><PlanBadge pkg={tier.legacy} /></div>
            <h3 className="mt-4 text-2xl font-normal tracking-tight">{tier.name}</h3>
            <p className="mt-2 min-h-[40px] text-sm text-[var(--ui-muted)]">{t(tier.summary)}</p>
            <div className="mt-4 text-xs text-[var(--ui-muted)]">{t("Termasuk")}</div>
            <ul className="mt-2 flex-1 space-y-2 text-sm">{tier.features.map((feature) => <li key={feature} className="flex gap-2"><Check className="mt-0.5 h-4 w-4 shrink-0 text-[var(--v13-up)]" />{t(feature)}</li>)}</ul>
            <div className="mt-5 border-t border-[var(--ui-border)] pt-4">
              {tier.id === "basic" ? <><div className="text-xs text-[var(--ui-muted)]">{t("Layanan sesuai kebutuhan")}</div><div className="mt-2"><strong className="text-xl font-normal">Rp 0</strong><span className="text-sm text-[var(--ui-muted)]"> · {t("tanpa biaya langganan")}</span></div><div className="mt-1 text-xs text-[var(--ui-muted)]">{pricing ? `${idr(planPrice(tier, pricing))} ${t("per lagu saat rilisan diajukan")}` : ""}</div></>
                : <><div className="v13-tabs" style={{ display: "inline-flex" }}>{[["monthly", "Bulanan"], ["annual", "Tahunan"]].map(([key, name]) => <a key={key} href={`#${key}`} onClick={(event) => { event.preventDefault(); setPeriods((value) => ({ ...value, [tier.id]: key })); }} className={period === key ? "is-active" : ""}>{t(name)}</a>)}</div>
                  <div className="mt-3">{period === "monthly" ? <><strong className="text-lg font-normal">{t("Belum ditetapkan")}</strong><div className="text-xs text-[var(--ui-muted)]">{t("Harga periode ini menunggu pengaturan.")}</div></> : <><strong className="text-xl font-normal">{pricing ? idr(planPrice(tier, pricing)) : "…"}</strong><span className="text-sm text-[var(--ui-muted)]"> / {t("tahun")}</span></>}</div></>}
              <div className="mt-4">{action(tier)}</div>
            </div>
          </div>;
        })}
      </div>
      <div className="mt-6 space-y-1 text-xs text-[var(--ui-muted)]"><p>{t("Masa aktif paket dimulai setelah pembayaran dikonfirmasi; peralihan ke paket lebih tinggi langsung berlaku dan sisa masa aktif ditambahkan.")}</p><p>{t("Paket lebih rendah dan Basic dimulai saat paket sekarang berakhir. Paket dan hak yang sudah dibeli tidak dikurangi.")}</p></div>
    </div>
    {confirmBasic && <BasicConfirm end={entitlements?.subscription_expires_at} onBack={() => setConfirmBasic(false)} onDone={() => setConfirmBasic(false)} />}
    {buyTokens && <TokenDialog wallet={wallet} onClose={() => setBuyTokens(false)} />}
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
