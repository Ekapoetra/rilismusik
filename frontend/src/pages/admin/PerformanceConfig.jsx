import React, { useCallback, useEffect, useMemo, useState } from "react";
import { SlidersHorizontal, Save, Scale, Target, Gauge } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

const num = (v) => (v === "" || v === null || v === undefined ? null : Number(v));

function Section({ title, icon: Ico, children, onSave, testid }) {
  const { t } = useAppPreferences();
  const [reason, setReason] = useState("");
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5" data-testid={testid}>
      <h3 className="flex items-center gap-2 font-bold"><Ico className="h-4 w-4 text-pink-300" />{title}</h3>
      <div className="mt-4">{children}</div>
      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-white/10 pt-3">
        <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder={t("Alasan perubahan (audit)")} className="rm-input flex-1 py-1.5 text-sm" data-testid={`${testid}-reason`} />
        <button onClick={() => onSave(reason, () => setReason(""))} className="rm-btn inline-flex items-center gap-1.5 text-sm" data-testid={`${testid}-save`}><Save className="h-4 w-4" />{t("Simpan")}</button>
      </div>
    </div>
  );
}

export default function PerformanceConfig() {
  const { t, locale } = useAppPreferences();
  const [cfg, setCfg] = useState(null);
  const [roleFilter, setRoleFilter] = useState("default");

  const load = useCallback(async () => {
    try { const { data } = await api.get("/admin/performance/config"); setCfg(data); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const save = async (section, value, reason, done) => {
    try { await api.put("/admin/performance/config", { section, value, reason }); toast.success(t("Konfigurasi disimpan.")); done && done(); await load(); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const workTypes = cfg?.work_types || [];
  const roles = cfg?.roles || [];
  const targetValue = useMemo(() => (wt) => {
    const node = cfg?.targets?.[wt] || {};
    if (roleFilter === "default") return node.default ?? "";
    return (node.roles || {})[roleFilter] ?? "";
  }, [cfg, roleFilter]);

  if (!cfg) return <p className="p-6 text-sm text-zinc-500">{t("Memuat…")}</p>;

  return (
    <div className="space-y-6" data-testid="performance-config-page">
      <header className="border-b border-white/10 pb-5">
        <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">{t("Kinerja")}</div>
        <h1 className="mt-1 flex items-center gap-2 font-display text-3xl font-extrabold"><SlidersHorizontal className="h-6 w-6 text-pink-400" />{t("Konfigurasi KPI")}</h1>
        <p className="mt-2 text-sm text-zinc-400">{t("Nilai berikut adalah default yang wajar dan dapat Anda ubah. Setiap perubahan tercatat (audit).")}</p>
      </header>

      {/* WEIGHTS */}
      <Section title={t("Bobot Jenis Pekerjaan")} icon={Scale} testid="perf-cfg-weights"
        onSave={(reason, done) => save("weights", cfg.weights, reason, done)}>
        <p className="mb-3 text-xs text-zinc-500">{t("Bobot mewakili kompleksitas operasional relatif untuk pengukuran, bukan penilaian keahlian staf.")}</p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {workTypes.map((w) => (
            <label key={w.key} className="flex items-center justify-between gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm">
              <span className="truncate">{locale === "en" ? w.label_en : w.label_id}</span>
              <input type="number" step="0.5" min="0" value={cfg.weights[w.key] ?? 1} onChange={(e) => setCfg({ ...cfg, weights: { ...cfg.weights, [w.key]: Number(e.target.value) } })} className="rm-input w-20 py-1 text-right" data-testid={`perf-weight-${w.key}`} />
            </label>
          ))}
        </div>
      </Section>

      {/* TARGETS */}
      <Section title={t("Target Bulanan")} icon={Target} testid="perf-cfg-targets"
        onSave={(reason, done) => save("targets", cfg.targets, reason, done)}>
        <p className="mb-3 text-xs text-zinc-500">{t("Kosongkan bila jenis pekerjaan tidak punya target kuantitatif (Tidak Berlaku). Target didefinisikan per Role + Jenis Pekerjaan.")}</p>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className="text-xs text-zinc-500">{t("Berlaku untuk")}:</span>
          <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} className="rm-input py-1 text-sm" data-testid="perf-target-role-filter">
            <option value="default">{t("Default (semua role)")}</option>
            {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {workTypes.map((w) => (
            <label key={w.key} className="flex items-center justify-between gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm">
              <span className="truncate">{locale === "en" ? w.label_en : w.label_id}</span>
              <input type="number" min="0" placeholder="—" value={targetValue(w.key)} onChange={(e) => {
                const node = { ...(cfg.targets[w.key] || {}) };
                if (roleFilter === "default") node.default = num(e.target.value);
                else node.roles = { ...(node.roles || {}), [roleFilter]: num(e.target.value) };
                setCfg({ ...cfg, targets: { ...cfg.targets, [w.key]: node } });
              }} className="rm-input w-20 py-1 text-right" data-testid={`perf-target-${w.key}`} />
            </label>
          ))}
        </div>
      </Section>

      {/* SCORING */}
      <Section title={t("Skoring & Kategori")} icon={Gauge} testid="perf-cfg-scoring"
        onSave={(reason, done) => save("scoring", cfg.scoring, reason, done)}>
        <div className="space-y-5 text-sm">
          <div>
            <div className="mb-2 text-xs font-bold uppercase tracking-wide text-zinc-500">{t("Bobot Komponen Skor")}</div>
            <div className="grid gap-3 sm:grid-cols-4">
              {["achievement", "timeliness", "complexity", "quality"].map((k) => (
                <label key={k} className="flex items-center justify-between gap-2 rounded-lg border border-white/10 px-3 py-2">
                  <span className="capitalize">{t({ achievement: "Pencapaian", timeliness: "Ketepatan", complexity: "Kompleksitas", quality: "Kualitas" }[k])}</span>
                  <input type="number" step="0.1" min="0" max="1" value={cfg.scoring.component_weights[k] ?? 0} onChange={(e) => setCfg({ ...cfg, scoring: { ...cfg.scoring, component_weights: { ...cfg.scoring.component_weights, [k]: Number(e.target.value) } } })} className="rm-input w-16 py-1 text-right" data-testid={`perf-cw-${k}`} />
                </label>
              ))}
            </div>
            <p className="mt-1 text-[11px] text-zinc-500">{t("Komponen tanpa data tidak dipaksa 0/100 — bobot dinormalisasi ulang atas komponen yang tersedia.")}</p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <label className="flex items-center justify-between gap-2 rounded-lg border border-white/10 px-3 py-2">
              <span>{t("Batas Skor Pencapaian")}</span>
              <input type="number" min="0" value={cfg.scoring.achievement_curve?.cap ?? 100} onChange={(e) => setCfg({ ...cfg, scoring: { ...cfg.scoring, achievement_curve: { ...cfg.scoring.achievement_curve, cap: Number(e.target.value) } } })} className="rm-input w-20 py-1 text-right" data-testid="perf-ach-cap" />
            </label>
            <label className="flex items-center justify-between gap-2 rounded-lg border border-white/10 px-3 py-2">
              <span>{t("Referensi Kompleksitas")}</span>
              <input type="number" min="0" placeholder="—" value={cfg.scoring.complexity_reference?.default ?? ""} onChange={(e) => setCfg({ ...cfg, scoring: { ...cfg.scoring, complexity_reference: { ...cfg.scoring.complexity_reference, default: num(e.target.value) } } })} className="rm-input w-20 py-1 text-right" data-testid="perf-complexity-ref" />
            </label>
            <label className="flex items-center justify-between gap-2 rounded-lg border border-white/10 px-3 py-2">
              <span>{t("Sampel Min. Skor")}</span>
              <input type="number" min="0" value={cfg.scoring.min_sample_to_show ?? 1} onChange={(e) => setCfg({ ...cfg, scoring: { ...cfg.scoring, min_sample_to_show: Number(e.target.value) } })} className="rm-input w-20 py-1 text-right" data-testid="perf-min-sample" />
            </label>
          </div>

          <div>
            <div className="mb-2 text-xs font-bold uppercase tracking-wide text-zinc-500">{t("Ambang Kategori (skor minimum)")}</div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {(cfg.scoring.categories || []).map((c, i) => (
                <label key={c.key} className="flex items-center justify-between gap-2 rounded-lg border border-white/10 px-3 py-2">
                  <span className="truncate">{locale === "en" ? c.name_en : c.name_id}</span>
                  <input type="number" min="0" max="100" value={c.min} onChange={(e) => { const cats = [...cfg.scoring.categories]; cats[i] = { ...c, min: Number(e.target.value) }; setCfg({ ...cfg, scoring: { ...cfg.scoring, categories: cats } }); }} className="rm-input w-16 py-1 text-right" data-testid={`perf-cat-${c.key}`} />
                </label>
              ))}
            </div>
          </div>

          <div>
            <div className="mb-2 text-xs font-bold uppercase tracking-wide text-zinc-500">{t("Ambang Keyakinan (jumlah sampel)")}</div>
            <div className="grid gap-3 sm:grid-cols-3">
              {["high", "moderate", "low"].map((k) => (
                <label key={k} className="flex items-center justify-between gap-2 rounded-lg border border-white/10 px-3 py-2">
                  <span>{t({ high: "Tinggi", moderate: "Sedang", low: "Rendah" }[k])}</span>
                  <input type="number" min="0" value={cfg.scoring.confidence?.[k] ?? 0} onChange={(e) => setCfg({ ...cfg, scoring: { ...cfg.scoring, confidence: { ...cfg.scoring.confidence, [k]: Number(e.target.value) } } })} className="rm-input w-16 py-1 text-right" data-testid={`perf-conf-${k}`} />
                </label>
              ))}
            </div>
          </div>
        </div>
      </Section>
    </div>
  );
}
