import React, { useEffect, useState } from "react";
import { api } from "@/api/client";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { AlertTriangle } from "lucide-react";

const fmtWib = (iso) => {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("id-ID", {
    timeZone: "Asia/Jakarta", day: "numeric", month: "long",
    hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).format(d).replace(".", ":") + " WIB";
};

/** Member-facing maintenance announcement (D13). Polls /maintenance/active. */
export default function MaintenanceBanner() {
  const { t } = useAppPreferences();
  const [windows, setWindows] = useState([]);
  useEffect(() => {
    let on = true;
    const load = () => api.get("/maintenance/active")
      .then((r) => { if (on) setWindows(r.data?.windows || []); })
      .catch(() => {});
    load();
    const timer = setInterval(load, 60000);
    return () => { on = false; clearInterval(timer); };
  }, []);
  if (!windows.length) return null;
  return windows.map((w) => (
    <section
      key={w.id}
      className={`maintenance-banner${w.mode === "readonly" ? " is-readonly" : ""}${w.status !== "active" ? " is-upcoming" : ""}`}
      data-testid="maintenance-banner"
      role="status"
    >
      <AlertTriangle className="maintenance-banner-icon" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <strong className="text-sm font-semibold">{w.title}</strong>
          <span className="maintenance-banner-tag">{w.mode === "readonly" ? t("Baca-saja") : t("Pengumuman")}</span>
        </div>
        <p className="mt-0.5 text-sm">{w.message}</p>
        <small className="mt-0.5 block text-xs opacity-75">
          {fmtWib(w.start_at)} – {fmtWib(w.end_at)} · {w.duration_minutes} {t("menit")}
        </small>
      </div>
    </section>
  ));
}
