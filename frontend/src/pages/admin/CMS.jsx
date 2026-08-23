import React, { useCallback, useEffect, useState } from "react";
import { api, formatApiError } from "@/api/client";
import { ADMIN_CMS } from "@/constants/testIds";
import { CMSPanel } from "@/components/admin/CMSPanels";

const TABS = [
  ["general", "General"], ["hero", "Hero"], ["benefits", "Benefits"],
  ["pricing", "Pricing"], ["faq", "FAQ"], ["seo", "SEO"],
  ["footer", "Footer"], ["legal_entity", "Legal Entity"],
].map(([id, label]) => ({ id, label }));

function withEditorIds(settings) {
  return {
    ...settings,
    benefits: (settings.benefits || []).map((item) => ({ ...item, _clientId: item._clientId || crypto.randomUUID() })),
    faq: (settings.faq || []).map((item) => ({ ...item, _clientId: item._clientId || crypto.randomUUID() })),
  };
}

function withoutEditorIds(settings) {
  const clean = structuredClone(settings);
  clean.benefits = (clean.benefits || []).map(({ _clientId, ...item }) => item);
  clean.faq = (clean.faq || []).map(({ _clientId, ...item }) => item);
  return clean;
}

export default function AdminCMS() {
  const [settings, setSettings] = useState(null);
  const [tab, setTab] = useState("hero");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    let active = true;
    api.get("/cms/landing")
      .then((response) => active && setSettings(withEditorIds(response.data)))
      .catch((error) => active && setErr(formatApiError(error.response?.data?.detail)));
    return () => { active = false; };
  }, []);

  const setValue = useCallback((path, value) => {
    setSettings((current) => {
      const next = structuredClone(current);
      const keys = path.split(".");
      let target = next;
      for (const key of keys.slice(0, -1)) target = target[key] ||= {};
      target[keys.at(-1)] = value;
      return next;
    });
  }, []);

  const save = async () => {
    setSaving(true); setErr(""); setMsg("");
    try {
      await api.patch("/cms/landing", { settings: withoutEditorIds(settings) });
      setMsg("Pengaturan landing tersimpan.");
    } catch (error) {
      setErr(formatApiError(error.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  if (!settings) return <div className="text-zinc-500">Memuat…</div>;
  return <div className="space-y-5 max-w-4xl">
    <div className="flex justify-between items-start flex-wrap gap-3">
      <div><div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Content Management</div><h1 className="font-display text-3xl font-extrabold tracking-tighter">Landing Page CMS</h1></div>
      <button className="rm-btn-primary" onClick={save} disabled={saving} data-testid={ADMIN_CMS.saveButton}>{saving ? "Menyimpan…" : "Simpan Perubahan"}</button>
    </div>
    {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm">{err}</div>}
    {msg && <div className="rounded-2xl bg-emerald-500/15 text-emerald-300 px-4 py-3 text-sm">{msg}</div>}
    <div className="flex flex-wrap gap-2 border-b border-white/10">{TABS.map((item) => <button key={item.id} onClick={() => setTab(item.id)} className={`px-4 py-2 text-sm font-bold rounded-t-xl ${tab === item.id ? "bg-[#14111E] border border-white/10 border-b-[#14111E] rm-gradient-text" : "text-zinc-500 hover:text-white"}`} data-testid={`admin-cms-tab-${item.id}`}>{item.label}</button>)}</div>
    <div className="rm-card p-6 space-y-4"><CMSPanel tab={tab} settings={settings} setValue={setValue} /></div>
  </div>;
}