import React, { useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Clock3, LogOut } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { BankAccountPanel } from "@/components/label/BankAccountPanel";
import { KycPanel } from "@/components/label/KycPanel";
import { KycUploadField } from "@/components/label/KycUploadField";
import { ClaimLabelCard } from "@/components/label/ClaimLabelCard";
import { LabelLogo } from "@/components/shared/LabelLogo";
import { GoogleConnectCard } from "@/components/label/GoogleConnectCard";
import { PlanBadge, useLabelPlan } from "@/components/v13/Plans";
import LabelContract from "@/pages/label/Contract";

const TABS = [["identity", "Identitas label"], ["bank", "Rekening penerima"], ["contract", "Kontrak"]];
const FIELD_NAMES = { label_name: "Nama label", pic_name: "Penanggung jawab", email: "Email" };
const MINOR = ["whatsapp", "address", "city", "country"];

function Row({ label, value }) {
  return <div className="v13-row"><span className="text-sm text-[var(--ui-muted)]">{label}</span><span className="text-right text-sm" translate="no">{value || "—"}</span></div>;
}

function ChangeStatus({ request, onFix }) {
  const { t } = useAppPreferences();
  const [open, setOpen] = useState(false);
  if (!request || !["pending", "correction"].includes(request.status)) return null;
  const pending = request.status === "pending";
  return <section className="v13-attention" data-tone={pending ? "info" : "mustard"} data-testid="profile-change-status">
    <Clock3 aria-hidden="true" />
    <div className="min-w-0"><h3>{t(pending ? "Perubahan identitas sedang diperiksa" : "Perbaiki perubahan identitas")}</h3><p>{pending ? t("Profil saat ini tetap berlaku.") : request.review_note}</p>
      {open && <table className="mt-3 text-sm"><tbody>{Object.keys(request.after).map((key) => <tr key={key}><td className="pr-4 text-[var(--ui-muted)]">{t(FIELD_NAMES[key])}</td><td className="pr-3">{request.before[key] || "—"}</td><td className="pr-3">→</td><td>{request.after[key]}</td></tr>)}</tbody></table>}
    </div>
    <div className="flex gap-2"><button type="button" className="rounded-full px-3 py-1.5 text-sm underline" onClick={() => setOpen(!open)}>{t(open ? "Tutup" : "Lihat perubahan")}</button>{!pending && <button type="button" className="v13-plan-cta px-4 py-1.5 text-sm" style={{ width: "auto" }} onClick={onFix}>{t("Perbaiki")}</button>}</div>
  </section>;
}

function IdentityEditor({ profile, email, request, onSaved, onCancel, direct = false }) {
  const { t } = useAppPreferences();
  const [form, setForm] = useState({ label_name: profile.label_name || "", pic_name: profile.pic_name || "", email: email || "", ...Object.fromEntries(MINOR.map((key) => [key, profile[key] || ""])) });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const pendingReview = request?.status === "pending";
  const save = async () => {
    setSaving(true); setError("");
    try {
      if (direct) {  // Before activation the whole identity saves directly.
        await api.patch("/label/me", Object.fromEntries(["label_name", "pic_name", ...MINOR].map((key) => [key, form[key]])));
        onSaved(t("Identitas tersimpan."));
        return;
      }
      const minor = Object.fromEntries(MINOR.map((key) => [key, form[key]]));
      const minorChanged = MINOR.some((key) => (form[key] || "") !== (profile[key] || ""));
      if (minorChanged) await api.patch("/label/me", minor);
      const reviewed = { label_name: form.label_name, pic_name: form.pic_name, email: form.email };
      const reviewChanged = reviewed.label_name !== (profile.label_name || "") || reviewed.pic_name !== (profile.pic_name || "") || reviewed.email !== (email || "");
      let sent = false;
      if (reviewChanged && !pendingReview) { await api.post("/label/profile-change", reviewed); sent = true; }
      onSaved(sent ? t("Perubahan identitas dikirim untuk diperiksa.") : t("Identitas tersimpan."));
    } catch (requestError) { setError(formatApiError(requestError.response?.data?.detail)); }
    finally { setSaving(false); }
  };
  const field = (key, label, props = {}) => <label className="block text-sm">{t(label)}<input className="v13-select mt-1 w-full" style={{ height: 40 }} value={form[key]} onChange={(event) => setForm({ ...form, [key]: event.target.value })} data-testid={`profile-${key.replace("_", "-")}`} {...props} /></label>;
  return <div className="space-y-4" data-testid="profile-identity-editor">
    {!direct && <p className="text-sm text-[var(--ui-muted)]">{t("Perubahan nama label, email, atau penanggung jawab akan diperiksa sebelum digunakan.")}</p>}
    <div className="grid gap-3 md:grid-cols-2">{field("label_name", "Nama label", { disabled: pendingReview })}{field("email", "Email", { type: "email", disabled: pendingReview || direct })}{field("pic_name", "Penanggung jawab", { disabled: pendingReview })}{field("whatsapp", "WhatsApp")}</div>
    <div className="text-xs text-[var(--ui-muted)]">{t("Lokasi operasional label")}</div>
    <div className="grid gap-3 md:grid-cols-3">{field("address", "Alamat")}{field("city", "Kabupaten/kota")}{field("country", "Negara")}</div>
    {error && <p role="alert" className="text-sm text-[var(--v13-urgent)]">{error}</p>}
    <div className="flex justify-end gap-3"><button type="button" className="rounded-full px-4 py-2 text-sm text-[var(--ui-muted)] hover:text-[var(--ui-text)]" onClick={onCancel}>{t("Batal")}</button><button type="button" className="v13-plan-cta px-5" style={{ width: "auto" }} disabled={saving} onClick={save} data-testid="profile-save">{saving ? t("Menyimpan…") : t("Simpan")}</button></div>
  </div>;
}

export default function LabelProfile() {
  const { refresh, user, logout } = useAuth();
  const { t } = useAppPreferences();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const tab = TABS.some(([key]) => key === params.get("tab")) ? params.get("tab") : "identity";
  const plan = useLabelPlan();
  const [profile, setProfile] = useState(null);
  const [request, setRequest] = useState(null);
  const [editing, setEditing] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    const { data } = await api.get("/label/me");
    setProfile(data);
    window.dispatchEvent(new CustomEvent("rilismusik:kyc-updated", { detail: data.kyc }));
    api.get("/label/profile-change").then((response) => setRequest(response.data?.request || null)).catch(() => {});
  }, []);
  useEffect(() => { load().catch((e) => setErr(formatApiError(e.response?.data?.detail))); }, [load]);
  const onLogout = async () => { await logout(); navigate("/login"); };

  if (!profile) return <div className="text-[var(--ui-muted)]">{t("Memuat…")}</div>;
  if (profile.claim_pending) {
    return <div className="max-w-2xl space-y-6" data-testid="label-profile-claim-pending">
      <div className="v13-card space-y-4 p-8 text-center"><Clock3 className="mx-auto h-7 w-7 text-[var(--v13-pill-mustard)]" /><h1 className="text-2xl">{t("Permintaan Klaim Menunggu Verifikasi")}</h1><p className="text-sm text-[var(--ui-muted)]">{t("Permintaan klaim untuk label lama")} <b>{profile.claim_legacy_name}</b> {t("sedang diproses tim kami. Anda akan menerima notifikasi setelah akun terhubung.")}</p></div>
      <GoogleConnectCard />
    </div>;
  }
  const verified = Boolean(profile.kyc?.is_verified);
  const canClaim = !user?.claim_status || user?.claim_status === "rejected";
  const saved = (text) => { setEditing(false); setMsg(text); load(); refresh(); };

  return <div className="max-w-5xl space-y-6" data-testid="label-profile">
    <header className="flex flex-wrap items-center gap-4">
      <LabelLogo src={profile.logo_url} labelName={profile.label_name} className="h-16 w-16 md:h-20 md:w-20" testId="label-profile-logo" />
      <div className="min-w-0 flex-1"><h1 className="text-3xl" data-testid="label-profile-name" translate="no">{profile.label_name || t("Profil Label")}</h1><div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-[var(--ui-muted)]">{plan && <PlanBadge pkg={plan.package} />}<span translate="no">{user?.email}</span></div></div>
      <button type="button" onClick={onLogout} className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm text-[var(--v13-urgent)] hover:bg-[var(--ui-hover)]" data-testid="label-logout-button-desktop"><LogOut className="h-4 w-4" />{t("Keluar")}</button>
    </header>
    {err && <div role="alert" className="text-sm text-[var(--v13-urgent)]" data-testid="profile-error-alert">{err}</div>}
    {msg && <div role="status" className="text-sm text-[var(--v13-up)]" data-testid="profile-success-alert">{msg}</div>}
    <ChangeStatus request={request} onFix={() => { setParams({}); setEditing(true); }} />
    <nav className="v13-tabs" style={{ display: "inline-flex" }} aria-label={t("Profil Label")}>{TABS.map(([key, name]) => <a key={key} href={`?tab=${key}`} onClick={(event) => { event.preventDefault(); setParams(key === "identity" ? {} : { tab: key }); setMsg(""); }} className={tab === key ? "is-active" : ""} data-testid={`profile-tab-${key}`}>{t(name)}</a>)}</nav>

    {tab === "identity" && <div className="space-y-5">
      {!verified ? <>
        <KycPanel profile={profile} onReload={load} />
        <section className="v13-card"><div className="v13-card-head"><h2>{t("Identitas label")}</h2></div><div className="v13-card-body">
          <IdentityEditor direct profile={profile} email={user?.email} request={null} onSaved={(text) => saved(text)} onCancel={() => load()} />
        </div></section>
      </> : <section className="v13-card" data-testid="profile-identity">
        <div className="v13-card-head"><h2>{t("Identitas label")}</h2>{!editing && <button type="button" className="v13-plan-cta px-4 py-2 text-sm" style={{ width: "auto" }} onClick={() => setEditing(true)} data-testid="profile-edit-identity">{t("Edit identitas")}</button>}</div>
        <div className="v13-card-body">{editing ? <IdentityEditor profile={profile} email={user?.email} request={request} onSaved={saved} onCancel={() => setEditing(false)} />
          : <><Row label={t("Nama label")} value={profile.label_name} /><Row label={t("Email")} value={user?.email} /><Row label={t("Penanggung jawab")} value={profile.pic_name} /><Row label="WhatsApp" value={profile.whatsapp} /><Row label={t("Alamat")} value={profile.address} /><Row label={t("Kabupaten/kota")} value={profile.city} /><Row label={t("Negara")} value={profile.country} /><Row label={t("Dokumen identitas")} value={profile.kyc?.document ? t("Tersimpan") : t("Belum dilengkapi")} /></>}</div>
      </section>}
      {verified && <section className="v13-card"><div className="v13-card-body grid gap-6 pt-5 lg:grid-cols-2">
        <KycUploadField kind="logo" title={t("Foto profil label")} description={t("JPG atau PNG, tampil pada profil dan header.")} maxMb={5} currentUrl={profile.logo_url} onUploaded={load} />
        <div><div className="text-sm font-medium">{t("KTP penanggung jawab")}</div><p className="mt-1 text-sm text-[var(--ui-muted)]">{t("Disetujui saat aktivasi dan tetap berlaku. Untuk mengganti dokumen, hubungi kami lewat Tiket Bantuan.")}</p>{profile.kyc?.document && <a className="mt-3 inline-flex text-sm underline" href={`/api/label/kyc/ktp?v=${encodeURIComponent(profile.kyc.document.uploaded_at || "current")}`} target="_blank" rel="noreferrer">{t("Lihat dokumen identitas")}</a>}</div>
      </div></section>}
      <GoogleConnectCard />
      {canClaim && <ClaimLabelCard claimStatus={user?.claim_status} onSubmitted={() => { load(); refresh(); }} />}
    </div>}
    {tab === "bank" && <div className="space-y-3"><p className="text-sm text-[var(--ui-muted)]">{t("Digunakan untuk penerimaan royalti. Rekening saat ini tetap digunakan sampai rekening baru disetujui.")}</p><BankAccountPanel onChanged={load} /></div>}
    {tab === "contract" && <LabelContract />}
  </div>;
}
