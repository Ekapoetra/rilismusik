import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

const when = (iso) => new Date(iso).toLocaleString("id-ID", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Asia/Jakarta" });

// V13 history10: recent events for the label and its releases.
export default function LabelHistory() {
  const { t } = useAppPreferences();
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api.get("/label/history").then(({ data }) => setItems(data.items || [])).catch((e) => setError(formatApiError(e.response?.data?.detail))); }, []);
  return <div className="max-w-4xl space-y-5" data-testid="label-history">
    <header><div className="v13-section-label">{t("Riwayat")}</div><h1 className="mt-1 text-3xl">{t("Jejak aktivitas labelmu.")}</h1></header>
    <section className="v13-card"><div className="v13-card-body pt-4">
      {error ? <p role="alert" className="py-4 text-sm text-[var(--v13-urgent)]">{error}</p>
        : items === null ? <p role="status" className="py-4 text-sm text-[var(--ui-muted)]">{t("Memuat riwayat…")}</p>
          : items.length === 0 ? <p className="py-4 text-sm text-[var(--ui-muted)]">{t("Belum ada aktivitas.")}</p>
            : items.map((item, index) => {
              const inner = <><div className="min-w-0"><div className="v13-row-title">{t(item.name)}</div><div className="v13-row-sub truncate">{[item.target, when(item.at), t(item.actor)].filter(Boolean).join(" · ")}</div>{item.note && <div className="mt-1 text-xs text-[var(--ui-muted)]">{item.note}</div>}</div></>;
              return item.link ? <Link key={index} to={item.link} className="v13-row">{inner}</Link> : <div key={index} className="v13-row">{inner}</div>;
            })}
    </div></section>
  </div>;
}
