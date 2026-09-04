import React, { useCallback, useEffect, useState } from "react";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { Building2 } from "lucide-react";
import { BankAccountPanel } from "@/components/label/BankAccountPanel";
import { KycPanel } from "@/components/label/KycPanel";
import { LabelLogo } from "@/components/shared/LabelLogo";

export default function LabelProfile() {
  const { refresh, user } = useAuth();
  const [profile, setProfile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    const { data } = await api.get("/label/me");
    setProfile(data);
    window.dispatchEvent(new CustomEvent("rilismusik:kyc-updated", { detail: data.kyc }));
  }, []);

  useEffect(() => { load().catch((e) => setErr(formatApiError(e.response?.data?.detail))); }, [load]);

  const saveProfile = async () => {
    setSaving(true); setErr(""); setMsg("");
    try {
      const payload = Object.fromEntries(["label_name", "pic_name", "whatsapp", "address", "city", "country"].map((key) => [key, profile[key] || ""]));
      const { data } = await api.patch("/label/me", payload);
      setProfile(data);
      setMsg("Profil tersimpan.");
      refresh();
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setSaving(false); }
  };

  if (!profile) return <div className="text-zinc-500">Memuat…</div>;

  return (
    <div className="space-y-8 max-w-5xl">
      <div className="flex items-center gap-4">
        <LabelLogo src={profile.logo_url} labelName={profile.label_name} className="h-16 w-16 md:h-20 md:w-20" testId="label-profile-logo" />
        <div>
          <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Profil & Rekening</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter" data-testid="label-profile-name">{profile.label_name || "Profil Label"}</h1>
        </div>
      </div>
      {err && <div role="alert" className="rounded-lg bg-red-500/15 text-red-300 px-4 py-3 text-sm" data-testid="profile-error-alert">{err}</div>}
      {msg && <div className="rounded-lg bg-emerald-500/15 text-emerald-300 px-4 py-3 text-sm" data-testid="profile-success-alert">{msg}</div>}

      <KycPanel profile={profile} onReload={load} />

      <div className="rm-card p-6 space-y-4">
        <div className="flex items-center gap-2 font-display font-bold text-lg tracking-tight"><Building2 className="w-5 h-5" /> Info Label</div>
        <div className="grid md:grid-cols-2 gap-3">
          <F label="Nama Label"><input className="rm-input" value={profile.label_name || ""} onChange={e => setProfile({ ...profile, label_name: e.target.value })} data-testid="profile-label-name" /></F>
          <F label="Penanggung Jawab"><input className="rm-input" value={profile.pic_name || ""} onChange={e => setProfile({ ...profile, pic_name: e.target.value })} data-testid="profile-pic-name" /></F>
          <F label="WhatsApp"><input className="rm-input" value={profile.whatsapp || ""} onChange={e => setProfile({ ...profile, whatsapp: e.target.value })} data-testid="profile-whatsapp" /></F>
          <F label="Email"><input className="rm-input bg-white/5" value={user?.email || ""} disabled data-testid="profile-email" /></F>
          <F label="Alamat"><input className="rm-input" value={profile.address || ""} onChange={e => setProfile({ ...profile, address: e.target.value })} data-testid="profile-address" /></F>
          <F label="Kota"><input className="rm-input" value={profile.city || ""} onChange={e => setProfile({ ...profile, city: e.target.value })} data-testid="profile-city" /></F>
          <F label="Negara"><input className="rm-input" value={profile.country || ""} onChange={e => setProfile({ ...profile, country: e.target.value })} data-testid="profile-country" /></F>
        </div>
        <div className="flex justify-end pt-2">
          <button className="rm-btn-primary" disabled={saving} onClick={saveProfile} data-testid="profile-save">{saving ? "Menyimpan…" : "Simpan Profil"}</button>
        </div>
      </div>

      <BankAccountPanel onChanged={load} />
    </div>
  );
}
function F({ label, children }) { return <div><label className="rm-label">{label}</label>{children}</div>; }
