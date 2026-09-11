import React, { useState } from "react";
import { ADMIN_CMS } from "@/constants/testIds";
import { api, fileUrl, formatApiError } from "@/api/client";

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
    <Field label="Pay Per Release / Single & EP per lagu (Rp)"><input data-testid={ADMIN_CMS.payPrice} className="rm-input" type="number" value={pricing.pay_per_release_price || 0} onChange={(e) => setValue("pricing.pay_per_release_price", Number(e.target.value || 0))} /></Field>
    <Field label="Paket Album 7–12 lagu (Rp)"><input data-testid="admin-cms-album-price" className="rm-input" type="number" value={pricing.album_package_price || 0} onChange={(e) => setValue("pricing.album_package_price", Number(e.target.value || 0))} /></Field>
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

function DocumentsPanel({ settings, setValue }) {
  const documents = settings.documents || {};
  const [uploading, setUploading] = useState("");
  const [error, setError] = useState("");
  const upload = async (event, key) => {
    const file = event.target.files?.[0]; if (!file) return;
    setUploading(key); setError("");
    try { const data = new FormData(); data.append("file", file); const response = await api.post("/cms/documents/upload-signature", data, { headers: { "Content-Type": "multipart/form-data" } }); setValue(`documents.${key}`, response.data.url); }
    catch (err) { setError(formatApiError(err.response?.data?.detail)); }
    finally { setUploading(""); }
  };
  return <div className="space-y-4" data-testid="admin-cms-documents-panel">
    <div className="text-sm text-zinc-400">Aset ini digunakan pada Surat Pernyataan Hak Cipta yang dapat diunduh setelah rilisan disetujui.</div>
    {error && <div role="alert" className="text-sm text-red-300" data-testid="admin-cms-documents-error">{error}</div>}
    <div className="grid md:grid-cols-2 gap-3"><Field label="Nama Penanggung Jawab">{textInput(documents.responsible_person_name, (e) => setValue("documents.responsible_person_name", e.target.value), "admin-cms-responsible-name")}</Field><Field label="Jabatan">{textInput(documents.responsible_person_title, (e) => setValue("documents.responsible_person_title", e.target.value), "admin-cms-responsible-title")}</Field></div>
    <div className="grid md:grid-cols-2 gap-4">{[["signature_url", "Tanda Tangan"], ["stamp_url", "Stempel"]].map(([key, label]) => <div key={key} className="rounded-lg border border-white/10 p-4"><div className="text-sm font-bold mb-3">{label}</div>{documents[key] && <img src={fileUrl(documents[key])} alt={label} className="mb-3 h-24 w-full object-contain bg-white rounded-md p-2" data-testid={`admin-cms-${key}-preview`} />}<label className="rm-btn-ghost inline-flex cursor-pointer text-sm"><input type="file" className="sr-only" accept=".png,.jpg,.jpeg,.webp" onChange={(event) => upload(event, key)} data-testid={`admin-cms-${key}-upload`} />{uploading === key ? "Mengunggah…" : `Upload ${label}`}</label></div>)}</div>
  </div>;
}

const PANELS = { general: GeneralPanel, hero: HeroPanel, benefits: BenefitsPanel, pricing: PricingPanel, faq: FaqPanel, seo: SeoPanel, footer: FooterPanel, legal_entity: LegalPanel, documents: DocumentsPanel };

export const CMSPanel = ({ tab, settings, setValue }) => {
  const Panel = PANELS[tab];
  return Panel ? <Panel settings={settings} setValue={setValue} /> : null;
};