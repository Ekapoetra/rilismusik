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

const LABEL_HERO_CTA_ROUTES = [
  ["/label/releases/upload", "Ajukan Rilisan"],
  ["/label/releases", "Rilisan"],
  ["/label/royalty", "Royalti"],
  ["/label/withdraw", "Penarikan Dana"],
  ["/label/artists", "Artis"],
];

function isUnsafeCta(value) {
  return /^\s*javascript:/i.test(value || "");
}

function LabelHeroPreview({ hero, variant }) {
  const src = variant === "mobile"
    ? (fileUrl(hero.mobile_image) || fileUrl(hero.desktop_image) || "/hero/label-hero-mobile.webp")
    : (fileUrl(hero.desktop_image) || "/hero/label-hero-desktop.webp");
  const overlay = Math.min(Math.max(Number(hero.overlay_opacity ?? 55), 0), 90) / 100;
  return (
    <div className={`relative overflow-hidden rounded-xl border border-white/10 ${variant === "mobile" ? "aspect-[9/14] max-w-[220px]" : "aspect-[21/9]"}`} data-testid={`admin-cms-label-hero-preview-${variant}`}>
      <img src={src} alt="" className="absolute inset-0 h-full w-full object-cover" onError={(e) => { e.currentTarget.style.display = "none"; }} />
      <div className="absolute inset-0" style={{ background: `linear-gradient(90deg, rgba(11,13,18,${overlay + 0.25}) 0%, rgba(11,13,18,${overlay}) 45%, rgba(11,13,18,0.15) 100%)` }} />
      <div className={`relative flex h-full flex-col justify-end gap-2 ${variant === "mobile" ? "p-4" : "p-6"}`}>
        <h3 className={`font-display font-extrabold leading-tight text-white ${variant === "mobile" ? "text-lg" : "text-2xl md:text-3xl"}`}>{hero.headline || "Musik menghubungkan lebih banyak cerita"}</h3>
        {hero.subheadline && <p className="max-w-md text-xs text-zinc-300">{hero.subheadline}</p>}
        {hero.cta_text && <span className="mt-1 inline-flex w-fit items-center rounded-full bg-gradient-to-r from-[#FF1F8E] to-[#A24EFF] px-4 py-2 text-xs font-bold text-white">{hero.cta_text}</span>}
      </div>
    </div>
  );
}

function LabelDashboardPanel({ settings, setValue }) {
  const hero = settings.label_dashboard_hero || {};
  const [uploading, setUploading] = useState("");
  const [error, setError] = useState("");
  const upload = async (event, key) => {
    const file = event.target.files?.[0]; if (!file) return;
    setUploading(key); setError("");
    try {
      const data = new FormData(); data.append("file", file);
      const response = await api.post("/cms/landing/upload-image", data, { headers: { "Content-Type": "multipart/form-data" } });
      setValue(`label_dashboard_hero.${key}`, response.data.url);
    } catch (err) { setError(formatApiError(err.response?.data?.detail)); }
    finally { setUploading(""); event.target.value = ""; }
  };
  const ctaUnsafe = isUnsafeCta(hero.cta_target);
  return <div className="space-y-5" data-testid="admin-cms-label-dashboard-panel">
    <div className={`flex items-start justify-between gap-4 rounded-lg border p-4 ${hero.is_active ? "border-emerald-400/40 bg-emerald-400/[0.06]" : "border-amber-400/40 bg-amber-400/[0.06]"}`}>
      <div>
        <div className="text-sm font-bold">Hero Banner Dashboard Label</div>
        <p className="mt-0.5 text-xs text-zinc-400">Banner ini tampil di dashboard semua akun label. Jika nonaktif, sistem memakai gambar default bawaan.</p>
        {!hero.is_active && <p className="mt-1.5 text-xs font-semibold text-amber-300" data-testid="admin-cms-label-hero-inactive-warning">⚠️ Status NONAKTIF — banner ini belum tampil di dashboard label. Aktifkan lalu Simpan agar tayang.</p>}
      </div>
      <label className={`inline-flex shrink-0 cursor-pointer items-center gap-2 rounded-full px-3 py-1.5 text-sm font-bold ${hero.is_active ? "bg-emerald-500/20 text-emerald-200" : "bg-amber-500/20 text-amber-200"}`}>
        <input type="checkbox" checked={!!hero.is_active} onChange={(e) => setValue("label_dashboard_hero.is_active", e.target.checked)} data-testid="admin-cms-label-hero-active" className="h-4 w-4 accent-[#FF1F8E]" />
        {hero.is_active ? "Aktif" : "Nonaktif"}
      </label>
    </div>
    {error && <div role="alert" className="text-sm text-red-300" data-testid="admin-cms-label-hero-error">{error}</div>}

    <div className="grid gap-4 md:grid-cols-2">
      {[["desktop_image", "Gambar Desktop (rasio lebar, mis. 1600×685)"], ["mobile_image", "Gambar Mobile (potrait, opsional)"]].map(([key, label]) => (
        <div key={key} className="rounded-lg border border-white/10 p-4">
          <div className="mb-3 text-sm font-bold">{label}</div>
          {hero[key] && <img src={fileUrl(hero[key])} alt={label} className="mb-3 h-28 w-full rounded-md object-cover" data-testid={`admin-cms-label-hero-${key}-preview`} />}
          <div className="flex flex-wrap items-center gap-2">
            <label className="rm-btn-ghost inline-flex cursor-pointer text-sm"><input type="file" className="sr-only" accept=".png,.jpg,.jpeg,.webp" onChange={(e) => upload(e, key)} data-testid={`admin-cms-label-hero-${key}-upload`} />{uploading === key ? "Mengunggah…" : `Upload ${key === "mobile_image" ? "Mobile" : "Desktop"}`}</label>
            {hero[key] && <button type="button" className="text-xs font-semibold text-zinc-400 hover:text-red-300" onClick={() => setValue(`label_dashboard_hero.${key}`, "")} data-testid={`admin-cms-label-hero-${key}-clear`}>Hapus</button>}
          </div>
        </div>
      ))}
    </div>

    <Field label="Headline">{textInput(hero.headline, (e) => setValue("label_dashboard_hero.headline", e.target.value), "admin-cms-label-hero-headline")}</Field>
    <Field label="Subheadline"><textarea data-testid="admin-cms-label-hero-subheadline" className="rm-input min-h-[70px]" value={hero.subheadline || ""} onChange={(e) => setValue("label_dashboard_hero.subheadline", e.target.value)} /></Field>
    <div className="grid gap-3 md:grid-cols-2">
      <Field label="CTA Text">{textInput(hero.cta_text, (e) => setValue("label_dashboard_hero.cta_text", e.target.value), "admin-cms-label-hero-cta-text")}</Field>
      <Field label="CTA Target (route internal)">
        <select className="rm-input" value={LABEL_HERO_CTA_ROUTES.some(([r]) => r === hero.cta_target) ? hero.cta_target : ""} onChange={(e) => setValue("label_dashboard_hero.cta_target", e.target.value)} data-testid="admin-cms-label-hero-cta-target">
          <option value="">— Pilih tujuan —</option>
          {LABEL_HERO_CTA_ROUTES.map(([route, name]) => <option key={route} value={route}>{`${name} (${route})`}</option>)}
        </select>
      </Field>
    </div>
    {ctaUnsafe && <p className="text-xs text-red-300" data-testid="admin-cms-label-hero-cta-unsafe">Target CTA tidak aman (javascript:) dan akan diabaikan.</p>}
    <div className="grid gap-3 md:grid-cols-2">
      <Field label={`Overlay Gelap (${hero.overlay_opacity ?? 55}%)`}>
        <input type="range" min="0" max="90" value={hero.overlay_opacity ?? 55} onChange={(e) => setValue("label_dashboard_hero.overlay_opacity", Number(e.target.value))} className="w-full accent-[#FF1F8E]" data-testid="admin-cms-label-hero-overlay" />
      </Field>
      <Field label="Alt Text (aksesibilitas)">{textInput(hero.alt_text, (e) => setValue("label_dashboard_hero.alt_text", e.target.value), "admin-cms-label-hero-alt")}</Field>
    </div>

    <div>
      <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-zinc-500">
        Preview
        {hero.is_active
          ? <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-200" data-testid="admin-cms-label-hero-preview-status">Tayang di dashboard label</span>
          : <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-bold text-amber-200" data-testid="admin-cms-label-hero-preview-status">Nonaktif — belum tayang</span>}
      </div>
      <div className={`flex flex-wrap items-start gap-6 ${hero.is_active ? "" : "opacity-50"}`}>
        <div className="min-w-0 flex-1"><div className="mb-2 text-[11px] font-semibold text-zinc-500">Desktop</div><LabelHeroPreview hero={hero} variant="desktop" /></div>
        <div><div className="mb-2 text-[11px] font-semibold text-zinc-500">Mobile</div><LabelHeroPreview hero={hero} variant="mobile" /></div>
      </div>
    </div>
  </div>;
}

const PANELS = { general: GeneralPanel, hero: HeroPanel, benefits: BenefitsPanel, pricing: PricingPanel, faq: FaqPanel, seo: SeoPanel, footer: FooterPanel, legal_entity: LegalPanel, documents: DocumentsPanel, label_dashboard: LabelDashboardPanel };

export const CMSPanel = ({ tab, settings, setValue }) => {
  const Panel = PANELS[tab];
  return Panel ? <Panel settings={settings} setValue={setValue} /> : null;
};