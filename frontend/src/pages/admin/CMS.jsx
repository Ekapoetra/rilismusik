import React, { useEffect, useState } from "react";
import { api, formatApiError } from "@/api/client";
import { ADMIN_CMS } from "@/constants/testIds";

export default function AdminCMS() {
  const [s, setS] = useState(null);
  const [tab, setTab] = useState("hero");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => { api.get("/cms/landing").then((r) => setS(r.data)); }, []);

  const save = async () => {
    setSaving(true); setErr(""); setMsg("");
    try {
      await api.patch("/cms/landing", { settings: s });
      setMsg("Pengaturan landing tersimpan.");
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setSaving(false); }
  };

  if (!s) return <div className="text-zinc-500">Memuat…</div>;

  const setVal = (path, val) => {
    const next = JSON.parse(JSON.stringify(s));
    const keys = path.split(".");
    let cur = next;
    for (let i = 0; i < keys.length - 1; i++) cur = cur[keys[i]] ||= {};
    cur[keys[keys.length - 1]] = val;
    setS(next);
  };

  const TABS = [
    { id: "general", label: "General" },
    { id: "hero", label: "Hero" },
    { id: "benefits", label: "Benefits" },
    { id: "pricing", label: "Pricing" },
    { id: "faq", label: "FAQ" },
    { id: "seo", label: "SEO" },
    { id: "footer", label: "Footer" },
    { id: "legal_entity", label: "Legal Entity" },
  ];

  return (
    <div className="space-y-5 max-w-4xl">
      <div className="flex justify-between items-start flex-wrap gap-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Content Management</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter">Landing Page CMS</h1>
        </div>
        <button className="rm-btn-primary" onClick={save} disabled={saving} data-testid={ADMIN_CMS.saveButton}>{saving ? "Menyimpan…" : "Simpan Perubahan"}</button>
      </div>

      {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm">{err}</div>}
      {msg && <div className="rounded-2xl bg-emerald-500/15 text-emerald-300 px-4 py-3 text-sm">{msg}</div>}

      <div className="flex flex-wrap gap-2 border-b border-white/10">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)} className={`px-4 py-2 text-sm font-bold rounded-t-xl ${tab === t.id ? "bg-[#14111E] border border-white/10 border-b-[#14111E] rm-gradient-text" : "text-zinc-500 hover:text-white"}`} data-testid={`admin-cms-tab-${t.id}`}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="rm-card p-6 space-y-4">
        {tab === "general" && (
          <div className="grid md:grid-cols-2 gap-3">
            <F label="Brand Name"><input className="rm-input" value={s.general?.brand_name || ""} onChange={(e) => setVal("general.brand_name", e.target.value)} /></F>
            <F label="Support Email"><input className="rm-input" value={s.general?.support_email || ""} onChange={(e) => setVal("general.support_email", e.target.value)} /></F>
            <F label="WhatsApp"><input className="rm-input" value={s.general?.whatsapp || ""} onChange={(e) => setVal("general.whatsapp", e.target.value)} /></F>
            <F label="Primary Color"><input className="rm-input" value={s.general?.primary_color || ""} onChange={(e) => setVal("general.primary_color", e.target.value)} /></F>
          </div>
        )}
        {tab === "hero" && (
          <div className="space-y-3">
            <F label="Headline"><input data-testid={ADMIN_CMS.heroHeadline} className="rm-input" value={s.hero?.headline || ""} onChange={(e) => setVal("hero.headline", e.target.value)} /></F>
            <F label="Subheadline"><textarea data-testid={ADMIN_CMS.heroSubheadline} className="rm-input min-h-[80px]" value={s.hero?.subheadline || ""} onChange={(e) => setVal("hero.subheadline", e.target.value)} /></F>
            <div className="grid md:grid-cols-2 gap-3">
              <F label="CTA Primary Text"><input className="rm-input" value={s.hero?.cta_primary_text || ""} onChange={(e) => setVal("hero.cta_primary_text", e.target.value)} /></F>
              <F label="CTA Primary URL"><input className="rm-input" value={s.hero?.cta_primary_url || ""} onChange={(e) => setVal("hero.cta_primary_url", e.target.value)} /></F>
              <F label="CTA Secondary Text"><input className="rm-input" value={s.hero?.cta_secondary_text || ""} onChange={(e) => setVal("hero.cta_secondary_text", e.target.value)} /></F>
              <F label="CTA Secondary URL"><input className="rm-input" value={s.hero?.cta_secondary_url || ""} onChange={(e) => setVal("hero.cta_secondary_url", e.target.value)} /></F>
            </div>
            <F label="Hero Image URL"><input className="rm-input" value={s.hero?.hero_image_url || ""} onChange={(e) => setVal("hero.hero_image_url", e.target.value)} /></F>
          </div>
        )}
        {tab === "benefits" && (
          <div className="space-y-3">
            {(s.benefits || []).map((b, i) => (
              <div key={i} className="border border-white/5 rounded-2xl p-3 grid md:grid-cols-2 gap-3 bg-white/[0.02]">
                <F label={`Title ${i + 1}`}><input className="rm-input" value={b.title} onChange={(e) => {
                  const next = [...s.benefits]; next[i] = { ...b, title: e.target.value }; setVal("benefits", next);
                }} /></F>
                <F label="Description"><input className="rm-input" value={b.desc} onChange={(e) => {
                  const next = [...s.benefits]; next[i] = { ...b, desc: e.target.value }; setVal("benefits", next);
                }} /></F>
              </div>
            ))}
            <button className="rm-btn-ghost text-sm" onClick={() => setVal("benefits", [...(s.benefits || []), { title: "New benefit", desc: "Describe it." }])}>+ Tambah Benefit</button>
          </div>
        )}
        {tab === "pricing" && (
          <div className="grid md:grid-cols-2 gap-3">
            <F label="Pay Per Release (Rp)"><input data-testid={ADMIN_CMS.payPrice} className="rm-input" type="number" value={s.pricing?.pay_per_release_price || 0} onChange={(e) => setVal("pricing.pay_per_release_price", parseInt(e.target.value || 0))} /></F>
            <F label="Annual Subscription (Rp)"><input data-testid={ADMIN_CMS.subPrice} className="rm-input" type="number" value={s.pricing?.annual_subscription_price || 0} onChange={(e) => setVal("pricing.annual_subscription_price", parseInt(e.target.value || 0))} /></F>
            <F label="Distributor Fee (%)"><input className="rm-input" type="number" value={s.pricing?.distributor_fee_percent || 0} onChange={(e) => setVal("pricing.distributor_fee_percent", parseFloat(e.target.value || 0))} /></F>
            <F label="Description"><input className="rm-input" value={s.pricing?.description || ""} onChange={(e) => setVal("pricing.description", e.target.value)} /></F>
          </div>
        )}
        {tab === "faq" && (
          <div className="space-y-3">
            {(s.faq || []).map((f, i) => (
              <div key={i} className="border border-white/5 rounded-2xl p-3 grid gap-2 bg-white/[0.02]">
                <F label={`Question ${i + 1}`}><input className="rm-input" value={f.q} onChange={(e) => {
                  const next = [...s.faq]; next[i] = { ...f, q: e.target.value }; setVal("faq", next);
                }} /></F>
                <F label="Answer"><textarea className="rm-input min-h-[60px]" value={f.a} onChange={(e) => {
                  const next = [...s.faq]; next[i] = { ...f, a: e.target.value }; setVal("faq", next);
                }} /></F>
              </div>
            ))}
            <button className="rm-btn-ghost text-sm" onClick={() => setVal("faq", [...(s.faq || []), { q: "New question", a: "Answer here" }])}>+ Tambah FAQ</button>
          </div>
        )}
        {tab === "seo" && (
          <div className="space-y-3">
            <F label="Page Title"><input className="rm-input" value={s.seo?.page_title || ""} onChange={(e) => setVal("seo.page_title", e.target.value)} /></F>
            <F label="Meta Description"><textarea className="rm-input min-h-[80px]" value={s.seo?.meta_description || ""} onChange={(e) => setVal("seo.meta_description", e.target.value)} /></F>
            <div className="grid md:grid-cols-2 gap-3">
              <F label="OG Title"><input className="rm-input" value={s.seo?.og_title || ""} onChange={(e) => setVal("seo.og_title", e.target.value)} /></F>
              <F label="Canonical URL"><input className="rm-input" value={s.seo?.canonical_url || ""} onChange={(e) => setVal("seo.canonical_url", e.target.value)} /></F>
              <F label="OG Description"><input className="rm-input" value={s.seo?.og_description || ""} onChange={(e) => setVal("seo.og_description", e.target.value)} /></F>
              <F label="OG Image URL"><input className="rm-input" value={s.seo?.og_image || ""} onChange={(e) => setVal("seo.og_image", e.target.value)} /></F>
            </div>
          </div>
        )}
        {tab === "footer" && (
          <div className="space-y-3">
            <F label="Description"><textarea className="rm-input min-h-[80px]" value={s.footer?.description || ""} onChange={(e) => setVal("footer.description", e.target.value)} /></F>
            <F label="Support Email"><input className="rm-input" value={s.footer?.support_email || ""} onChange={(e) => setVal("footer.support_email", e.target.value)} /></F>
          </div>
        )}
        {tab === "legal_entity" && (
          <div className="space-y-3" data-testid="admin-cms-legal-entity">
            <div className="text-xs text-zinc-500 mb-2">Informasi badan hukum operator yang ditampilkan di footer landing page, invoice, dan dokumen kontrak.</div>
            <div className="grid md:grid-cols-2 gap-3">
              <F label="Company Name"><input className="rm-input" value={s.legal_entity?.company_name || ""} onChange={(e) => setVal("legal_entity.company_name", e.target.value)} data-testid="admin-cms-legal-company_name" /></F>
              <F label="NIB"><input className="rm-input" value={s.legal_entity?.nib || ""} onChange={(e) => setVal("legal_entity.nib", e.target.value)} data-testid="admin-cms-legal-nib" /></F>
              <F label="Address Line 1"><input className="rm-input" value={s.legal_entity?.address_line1 || ""} onChange={(e) => setVal("legal_entity.address_line1", e.target.value)} data-testid="admin-cms-legal-address_line1" /></F>
              <F label="Address Line 2"><input className="rm-input" value={s.legal_entity?.address_line2 || ""} onChange={(e) => setVal("legal_entity.address_line2", e.target.value)} data-testid="admin-cms-legal-address_line2" /></F>
              <F label="City"><input className="rm-input" value={s.legal_entity?.city || ""} onChange={(e) => setVal("legal_entity.city", e.target.value)} data-testid="admin-cms-legal-city" /></F>
              <F label="Postal Code"><input className="rm-input" value={s.legal_entity?.postal_code || ""} onChange={(e) => setVal("legal_entity.postal_code", e.target.value)} data-testid="admin-cms-legal-postal_code" /></F>
              <F label="Country"><input className="rm-input" value={s.legal_entity?.country || ""} onChange={(e) => setVal("legal_entity.country", e.target.value)} data-testid="admin-cms-legal-country" /></F>
              <F label="WhatsApp / HP"><input className="rm-input" value={s.legal_entity?.whatsapp || ""} onChange={(e) => setVal("legal_entity.whatsapp", e.target.value)} data-testid="admin-cms-legal-whatsapp" /></F>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
function F({ label, children }) { return <div><label className="rm-label">{label}</label>{children}</div>; }
