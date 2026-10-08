import React from "react";
import { Check } from "lucide-react";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

const STEPS = ["Pemeriksaan", "Siap dikirim", "Distribusi", "Tayang"];
// Current step per production status (prototype steps9): all done once live.
const CURRENT = { submitted: 0, awaiting_payment: 0, paid: 0, under_review: 0, need_revision: 0, approved: 1, delivered: 2, live: 4 };

export function ReleaseProgress({ status }) {
  const { t } = useAppPreferences();
  if (!(status in CURRENT)) return null;
  const current = CURRENT[status];
  return <section className="v13-card px-5 pb-5 pt-4" data-testid="release-progress">
    <div className="text-sm font-medium">{t("Perkembangan rilisan")}</div>
    <div className="v13-steps mt-4" style={{ "--steps": STEPS.length, "--fraction": Math.min(1, current / (STEPS.length - 1)) }}>{STEPS.map((step, index) => <i key={step} className={index < current ? "is-done" : index === current ? "is-current" : ""}>{index < current && <Check strokeWidth={3} />}</i>)}</div>
    <div className="mt-2 grid text-center text-xs" style={{ gridTemplateColumns: `repeat(${STEPS.length}, minmax(0, 1fr))` }}>{STEPS.map((step, index) => <span key={step} className={index === current ? "text-[var(--ui-text)]" : "text-[var(--ui-muted)]"}>{t(step)}</span>)}</div>
  </section>;
}
