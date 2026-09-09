import React from "react";
import { Check, Minus } from "lucide-react";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

export const PermissionMatrix = ({ modules, permissions, onChange, readOnly = false }) => {
  const { locale, t } = useAppPreferences();
  const selected = new Set(permissions);
  const toggleModule = (module) => { const keys = module.actions.map((action) => action.key); const all = keys.every((key) => selected.has(key)); const next = new Set(selected); keys.forEach((key) => all ? next.delete(key) : next.add(key)); onChange([...next]); };
  const toggleAction = (key) => { const next = new Set(selected); next.has(key) ? next.delete(key) : next.add(key); onChange([...next]); };
  const labelFor = (item) => locale === "en" ? item.label_en || t(item.label_id) : item.label_id;
  return <div className="divide-y divide-white/10 border-y border-white/10" data-testid="admin-permission-matrix">{modules.map((module) => {
    const count = module.actions.filter((action) => selected.has(action.key)).length;
    const all = count === module.actions.length; const partial = count > 0 && !all;
    return <section className="grid gap-4 py-5 lg:grid-cols-[220px_minmax(0,1fr)]" key={module.key} data-testid={`admin-permission-module-${module.key}`}>
      <button type="button" disabled={readOnly} onClick={() => toggleModule(module)} className="flex items-start gap-3 text-left disabled:cursor-default" data-testid={`admin-permission-module-toggle-${module.key}`}><span className={`mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded border ${all || partial ? "border-emerald-400/50 bg-emerald-400/10 text-emerald-300" : "border-white/15 text-zinc-600"}`}>{all ? <Check className="h-3.5 w-3.5" /> : partial ? <Minus className="h-3.5 w-3.5" /> : null}</span><span><strong className="block text-sm text-zinc-200" data-testid={`admin-permission-module-title-${module.key}`}>{labelFor(module)}</strong><span className="text-xs text-zinc-600">{count}/{module.actions.length} {t("izin")}</span></span></button>
      <div className="grid gap-2 sm:grid-cols-2">{module.actions.map((action) => <label className={`flex items-center gap-3 rounded-md border px-3 py-2.5 text-sm transition-colors ${readOnly ? "cursor-default" : "cursor-pointer"} ${selected.has(action.key) ? "border-emerald-400/30 bg-emerald-400/[0.07] text-zinc-100" : "border-white/10 bg-white/[0.02] text-zinc-500 hover:bg-white/[0.04]"}`} key={action.key} data-testid={`admin-permission-action-${action.key.replaceAll(".", "-")}`}><input type="checkbox" className="sr-only" checked={selected.has(action.key)} disabled={readOnly} onChange={() => toggleAction(action.key)} data-testid={`admin-permission-checkbox-${action.key.replaceAll(".", "-")}`} /><span className={`grid h-4 w-4 shrink-0 place-items-center rounded border ${selected.has(action.key) && "border-emerald-400 bg-emerald-400 text-black"}`}>{selected.has(action.key) && <Check className="h-3 w-3" />}</span><span>{labelFor(action)}</span></label>)}</div>
    </section>;
  })}</div>;
};