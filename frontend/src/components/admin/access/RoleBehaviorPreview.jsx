import React from "react";
import { Eye, Pencil, ShieldAlert, CheckCircle2, Zap, Ban, Lock } from "lucide-react";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

const STATE_STYLE = {
  view: { cls: "bg-sky-500/15 text-sky-300", Icon: Eye },
  standard: { cls: "bg-emerald-500/15 text-emerald-300", Icon: Pencil },
  sensitive: { cls: "bg-amber-500/15 text-amber-300", Icon: ShieldAlert },
  approval: { cls: "bg-violet-500/15 text-violet-300", Icon: CheckCircle2 },
  direct: { cls: "bg-red-500/15 text-red-300", Icon: Zap },
  unavailable: { cls: "bg-white/5 text-zinc-500", Icon: Ban },
};

export const RoleBehaviorPreview = ({ preview, loading, active = true }) => {
  const { locale } = useAppPreferences();
  const modules = preview?.modules || [];
  const nm = (m, key) => (locale === "en" ? m[`${key}_en`] : m[`${key}_id`]);
  return (
    <section className="space-y-3 border-y border-white/10 py-5" data-testid="admin-role-behavior-preview">
      <div>
        <h3 className="text-sm font-bold">Pratinjau Perilaku Akses</h3>
        <p className="mt-1 text-xs text-zinc-500">Simulasi memakai mesin otorisasi asli · baca-saja, tidak mengubah data.</p>
      </div>
      {!active && <div className="rounded-md border border-red-400/30 bg-red-500/[0.06] px-3 py-2 text-xs text-red-200" data-testid="admin-role-behavior-inactive"><Lock className="mr-1 inline h-3.5 w-3.5" /> Role nonaktif — semua akses ditolak.</div>}
      {loading && modules.length === 0 ? (
        <p className="text-xs text-zinc-500">Memuat…</p>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {modules.map((m) => (
            <div key={m.key} className={`rounded-md border p-3 ${m.accessible ? "border-white/10 bg-white/[0.02]" : "border-white/5 bg-transparent opacity-60"}`} data-testid={`admin-role-behavior-module-${m.key}`}>
              <div className="flex items-center justify-between gap-2">
                <strong className="text-sm text-zinc-200">{nm(m, "label")}</strong>
                {m.accessible ? (m.read_only ? <span className="rm-badge bg-sky-500/15 text-sky-300 text-[10px]">Baca-saja</span> : <span className="rm-badge bg-emerald-500/15 text-emerald-300 text-[10px]">Aktif</span>) : <span className="rm-badge bg-white/5 text-zinc-500 text-[10px]">Tidak Tampil</span>}
              </div>
              <ul className="mt-2 space-y-1">
                {m.actions.map((a) => {
                  const st = STATE_STYLE[a.state] || STATE_STYLE.unavailable;
                  const Icon = st.Icon;
                  return (
                    <li key={a.key} className="flex items-center justify-between gap-2 text-xs" data-testid={`admin-role-behavior-action-${a.key.replaceAll(".", "-")}`}>
                      <span className={a.allowed ? "text-zinc-300" : "text-zinc-600"}>{locale === "en" ? a.label_en : a.label_id}</span>
                      <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-bold ${st.cls}`}><Icon className="h-3 w-3" />{locale === "en" ? a.state_label_en : a.state_label_id}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      )}
    </section>
  );
};
