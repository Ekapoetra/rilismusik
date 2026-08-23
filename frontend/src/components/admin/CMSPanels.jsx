import React from "react";
import { ADMIN_CMS } from "@/constants/testIds";

const Field = ({ label, children }) => <div><label className="rm-label">{label}</label>{children}</div>;

const textInput = (value, onChange, testId) => (
  <input className="rm-input" value={value || ""} onChange={onChange} data-testid={testId} />
);

function GeneralPanel({ settings, setValue }) {
  return <div className="grid md:grid-cols-2 gap-3">
    <Field label="Brand Name">{textInput(settings.general?.brand_name, (e) => setValue("general.brand_name", e.target.value))}</Field>
    <Field label="Support Email">{textInput(settings.general?.support_email, (e) => setValue("general.support_email", e.target.value))}</Field>
    <Field label="WhatsApp">{textInput(settings.general?.whatsapp, (e) => setValue("general.whatsapp", e.target.value))}</Field>
    <Field label="Primary Color">{textInput(settings.general?.primary_color, (e) => setValue("general.primary_color", e.target.value))}</Field>
  </div>;
}

function HeroPanel({ settings, setValue }) {
  const hero = settings.hero || {};
  return <div className="space-y-3">
    <Field label="Headline">{textInput(hero.headline, (e) => setValue("hero.headline", e.target.value), ADMIN_CMS.heroHeadline)}</Field>
    <Field label="Subheadline"><textarea data-testid={ADMIN_CMS.heroSubheadline} className="rm-input min-h-[80px]" value={hero.subheadline || ""} onChange={(e) => setValue("hero.subheadline", e.target.value)} /></Field>
    <div className="grid md:grid-cols-2 gap-3">
      {[["CTA Primary Text", "cta_primary_text"], ["CTA Primary URL", "cta_primary_url"], ["CTA Secondary Text", "cta_secondary_text"], ["CTA Secondary URL", "cta_secondary_url"]].map(([label, key]) => (
        <Field key={key} label={label}>{textInput(hero[key], (e) => setValue(`hero.${key}`, e.target.value))}</Field>
      ))}
    </div>
    <Field label="Hero Image URL">{textInput(hero.hero_image_url, (e) => setValue("hero.hero_image_url", e.target.value))}</Field>
  </div>;
}

function BenefitsPanel({ settings, setValue }) {
  const items = settings.benefits || [];
  const update = (index, key, value) => {
    const next = [...items]; next[index] = { ...next[index], [key]: value }; setValue("benefits", next);
  };
  return <div className="space-y-3">
    {items.map((item, index) => <div key={item._clientId} className="border border-white/5 rounded-2xl p-3 grid md:grid-cols-2 gap-3 bg-white/[0.02]">
      <Field label={`Title ${index + 1}`}>{textInput(item.title, (e) => update(index, "title", e.target.value))}</Field>
      <Field label="Description">{textInput(item.desc, (e) => update(index, "desc", e.target.value))}</Field>
    </div>)}
    <button className="rm-btn-ghost text-sm" onClick={() => setValue("benefits", [...items, { _clientId: crypto.randomUUID(), title: "New benefit", desc: "Describe it." }])}>+ Tambah Benefit</button>
  </div>;
}

function PricingPanel({ settings, setValue }) {
  const pricing = settings.pricing || {};
  return <div className="grid md:grid-cols-2 gap-3">
    <Field label="Pay Per Release (Rp)"><input data-testid={ADMIN_CMS.payPrice} className="rm-input" type="number" value={pricing.pay_per_release_price || 0} onChange={(e) => setValue("pricing.pay_per_release_price", Number(e.target.value || 0))} /></Field>
    <Field label="Annual Subscription (Rp)"><input data-testid={ADMIN_CMS.subPrice} className="rm-input" type="number" value={pricing.annual_subscription_price || 0} onChange={(e) => setValue("pricing.annual_subscription_price", Number(e.target.value || 0))} /></Field>
    <Field label="Description">{textInput(pricing.description, (e) => setValue("pricing.description", e.target.value))}</Field>
  </div>;
}

function FaqPanel({ settings, setValue }) {
  const items = settings.faq || [];
  const update = (index, key, value) => {
    const next = [...items]; next[index] = { ...next[index], [key]: value }; setValue("faq", next);
  };
  return <div className="space-y-3">
    {items.map((item, index) => <div key={item._clientId} className="border border-white/5 rounded-2xl p-3 grid gap-2 bg-white/[0.02]">
      <Field label={`Question ${index + 1}`}>{textInput(item.q, (e) => update(index, "q", e.target.value))}</Field>
      <Field label="Answer"><textarea className="rm-input min-h-[60px]" value={item.a || ""} onChange={(e) => update(index, "a", e.target.value)} /></Field>
    </div>)}
    <button className="rm-btn-ghost text-sm" onClick={() => setValue("faq", [...items, { _clientId: crypto.randomUUID(), q: "New question", a: "Answer here" }])}>+ Tambah FAQ</button>
  </div>;
}

function SeoPanel({ settings, setValue }) {
  const seo = settings.seo || {};
  return <div className="space-y-3">
    <Field label="Page Title">{textInput(seo.page_title, (e) => setValue("seo.page_title", e.target.value))}</Field>
    <Field label="Meta Description"><textarea className="rm-input min-h-[80px]" value={seo.meta_description || ""} onChange={(e) => setValue("seo.meta_description", e.target.value)} /></Field>
    <div className="grid md:grid-cols-2 gap-3">{[["OG Title", "og_title"], ["Canonical URL", "canonical_url"], ["OG Description", "og_description"], ["OG Image URL", "og_image"]].map(([label, key]) => <Field key={key} label={label}>{textInput(seo[key], (e) => setValue(`seo.${key}`, e.target.value))}</Field>)}</div>
  </div>;
}

function FooterPanel({ settings, setValue }) {
  return <div className="space-y-3">
    <Field label="Description"><textarea className="rm-input min-h-[80px]" value={settings.footer?.description || ""} onChange={(e) => setValue("footer.description", e.target.value)} /></Field>
    <Field label="Support Email">{textInput(settings.footer?.support_email, (e) => setValue("footer.support_email", e.target.value))}</Field>
  </div>;
}

function LegalPanel({ settings, setValue }) {
  const legal = settings.legal_entity || {};
  const fields = [["Company Name", "company_name"], ["NIB", "nib"], ["Address Line 1", "address_line1"], ["Address Line 2", "address_line2"], ["City", "city"], ["Postal Code", "postal_code"], ["Country", "country"], ["WhatsApp / HP", "whatsapp"]];
  return <div className="space-y-3" data-testid="admin-cms-legal-entity">
    <div className="text-xs text-zinc-500 mb-2">Informasi badan hukum operator yang ditampilkan di footer landing page, invoice, dan dokumen kontrak.</div>
    <div className="grid md:grid-cols-2 gap-3">{fields.map(([label, key]) => <Field key={key} label={label}>{textInput(legal[key], (e) => setValue(`legal_entity.${key}`, e.target.value), `admin-cms-legal-${key}`)}</Field>)}</div>
  </div>;
}

const PANELS = { general: GeneralPanel, hero: HeroPanel, benefits: BenefitsPanel, pricing: PricingPanel, faq: FaqPanel, seo: SeoPanel, footer: FooterPanel, legal_entity: LegalPanel };

export const CMSPanel = ({ tab, settings, setValue }) => {
  const Panel = PANELS[tab];
  return Panel ? <Panel settings={settings} setValue={setValue} /> : null;
};