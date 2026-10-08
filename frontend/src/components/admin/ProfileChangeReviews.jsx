import React, { useCallback, useEffect, useState } from "react";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

const FIELD_NAMES = { label_name: "Nama label", pic_name: "Penanggung jawab", email: "Email" };

// V13 reviewProfile103: approve a label's identity change or ask for a correction.
export function ProfileChangeReviews() {
  const { t } = useAppPreferences();
  const { hasPermission } = useAuth();
  const canReview = hasPermission("kyc.review");
  const [items, setItems] = useState(null);
  const [notes, setNotes] = useState({});
  const [error, setError] = useState("");
  const load = useCallback(() => api.get("/admin/kyc/profile-changes").then(({ data }) => setItems(data.items || [])).catch((e) => setError(formatApiError(e.response?.data?.detail))), []);
  useEffect(() => { load(); }, [load]);
  const review = async (item, action) => {
    setError("");
    try { await api.post(`/admin/kyc/profile-changes/${item.id}/review`, { action, note: notes[item.id] || null }); load(); }
    catch (e) { setError(formatApiError(e.response?.data?.detail)); }
  };
  if (!items || items.length === 0) return error ? <p role="alert" className="text-sm text-[var(--v13-urgent)]">{error}</p> : null;
  return <section className="v13-card" data-testid="admin-profile-changes">
    <div className="v13-card-head"><h2>{t("Perubahan identitas")} · {items.length}</h2></div>
    <div className="v13-card-body">
      {error && <p role="alert" className="mb-3 text-sm text-[var(--v13-urgent)]">{error}</p>}
      {items.map((item) => <div key={item.id} className="border-b border-[var(--ui-border)] py-4 last:border-0" data-testid={`profile-change-${item.id}`}>
        <div className="flex flex-wrap items-center justify-between gap-2"><strong className="font-medium" translate="no">{item.label_name}</strong><span className="text-xs text-[var(--ui-muted)]">{new Date(item.created_at).toLocaleString("id-ID", { timeZone: "Asia/Jakarta" })}</span></div>
        <table className="mt-2 text-sm"><tbody>{Object.keys(item.after).map((key) => <tr key={key}><td className="pr-4 text-[var(--ui-muted)]">{t(FIELD_NAMES[key])}</td><td className="pr-3">{item.before[key] || "—"}</td><td className="pr-3">→</td><td className="font-medium">{item.after[key]}</td></tr>)}</tbody></table>
        {canReview && <div className="mt-3 flex flex-wrap items-center gap-2"><input value={notes[item.id] || ""} onChange={(event) => setNotes({ ...notes, [item.id]: event.target.value })} placeholder={t("Catatan (wajib untuk perbaikan)")} className="v13-select min-w-[240px] flex-1" /><button type="button" className="rounded-full border border-[var(--ui-border)] px-4 py-2 text-sm" onClick={() => review(item, "correct")}>{t("Minta perbaikan")}</button><button type="button" className="v13-plan-cta px-4 py-2 text-sm" style={{ width: "auto" }} onClick={() => review(item, "approve")}>{t("Setujui perubahan")}</button></div>}
      </div>)}
    </div>
  </section>;
}
