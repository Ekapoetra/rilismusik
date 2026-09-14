import React from "react";
import { AlertTriangle, Info } from "lucide-react";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

export const RoleValidationPanel = ({ warnings = [], loading = false }) => {
  const { locale } = useAppPreferences();
  const msg = (w) => (locale === "en" ? w.message_en : w.message_id);
  if (loading && warnings.length === 0) return null;
  return (
    <section className="space-y-2 border-y border-white/10 py-5" data-testid="admin-role-validation">
      <h3 className="text-sm font-bold">Validasi Konfigurasi</h3>
      {warnings.length === 0 ? (
        <p className="text-xs text-emerald-300" data-testid="admin-role-validation-ok">Tidak ada konflik konfigurasi terdeteksi.</p>
      ) : (
        <ul className="space-y-2">
          {warnings.map((w, i) => (
            <li key={`${w.code}-${w.permission}-${i}`} className={`flex items-start gap-2 rounded-md border px-3 py-2 text-xs ${w.severity === "info" ? "border-sky-400/30 bg-sky-500/[0.06] text-sky-200" : "border-amber-400/30 bg-amber-500/[0.06] text-amber-200"}`} data-testid={`admin-role-warning-${w.code}`}>
              {w.severity === "info" ? <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" /> : <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />}
              <span>{msg(w)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};
