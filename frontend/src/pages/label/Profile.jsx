import React, { useEffect, useState } from "react";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { Building2, Landmark } from "lucide-react";

export default function LabelProfile() {
  const { refresh, user } = useAuth();
  const [profile, setProfile] = useState(null);
  const [bank, setBank] = useState(null);
  const [bForm, setBForm] = useState({ bank_name: "", account_number: "", account_holder_name: "" });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get("/label/me").then(r => setProfile(r.data));
    api.get("/label/bank-account").then(r => setBank(r.data));
  }, []);

  const saveProfile = async () => {
    setSaving(true); setErr(""); setMsg("");
    try {
      const { data } = await api.patch("/label/me", profile);
      setProfile(data);
      setMsg("Profil tersimpan.");
      refresh();
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setSaving(false); }
  };

  const saveBank = async () => {
    setSaving(true); setErr(""); setMsg("");
    try {
      const { data } = await api.post("/label/bank-account", bForm);
      setBank(data);
      setMsg("Rekening disimpan. Menunggu verifikasi admin.");
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setSaving(false); }
  };

  if (!profile) return <div className="text-slate-500">Memuat…</div>;

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <div className="text-xs uppercase tracking-widest text-slate-500 font-bold">Profil & Rekening</div>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">Profil Label</h1>
      </div>
      {err && <div className="rounded-2xl bg-red-50 text-red-700 px-4 py-3 text-sm">{err}</div>}
      {msg && <div className="rounded-2xl bg-emerald-50 text-emerald-700 px-4 py-3 text-sm">{msg}</div>}

      <div className="rm-card p-6 space-y-4">
        <div className="flex items-center gap-2 font-display font-bold text-lg tracking-tight"><Building2 className="w-5 h-5" /> Info Label</div>
        <div className="grid md:grid-cols-2 gap-3">
          <F label="Nama Label"><input className="rm-input" value={profile.label_name || ""} onChange={e => setProfile({ ...profile, label_name: e.target.value })} data-testid="profile-label-name" /></F>
          <F label="Penanggung Jawab"><input className="rm-input" value={profile.pic_name || ""} onChange={e => setProfile({ ...profile, pic_name: e.target.value })} data-testid="profile-pic-name" /></F>
          <F label="WhatsApp"><input className="rm-input" value={profile.whatsapp || ""} onChange={e => setProfile({ ...profile, whatsapp: e.target.value })} /></F>
          <F label="Email"><input className="rm-input bg-slate-50" value={user?.email || ""} disabled /></F>
          <F label="Alamat"><input className="rm-input" value={profile.address || ""} onChange={e => setProfile({ ...profile, address: e.target.value })} /></F>
          <F label="Kota"><input className="rm-input" value={profile.city || ""} onChange={e => setProfile({ ...profile, city: e.target.value })} /></F>
          <F label="Negara"><input className="rm-input" value={profile.country || ""} onChange={e => setProfile({ ...profile, country: e.target.value })} /></F>
        </div>
        <div className="flex justify-end pt-2">
          <button className="rm-btn-primary" disabled={saving} onClick={saveProfile} data-testid="profile-save">{saving ? "Menyimpan…" : "Simpan Profil"}</button>
        </div>
      </div>

      <div className="rm-card p-6 space-y-4">
        <div className="flex items-center gap-2 font-display font-bold text-lg tracking-tight"><Landmark className="w-5 h-5" /> Rekening Bank</div>
        {bank ? (
          <div className="space-y-3">
            <Row k="Nama Bank" v={bank.bank_name} />
            <Row k="Nomor Rekening" v={bank.account_number} />
            <Row k="Atas Nama" v={bank.account_holder_name} />
            <Row k="Status Verifikasi" v={bank.verified_status} />
            <div className="text-xs text-slate-500 bg-slate-50 rounded-xl p-3">Rekening hanya bisa diinput sekali. Untuk perubahan, hubungi support@rilismusik.com.</div>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-3">
            <F label="Nama Bank"><input className="rm-input" value={bForm.bank_name} onChange={e => setBForm({ ...bForm, bank_name: e.target.value })} placeholder="Bank BCA" data-testid="bank-name" /></F>
            <F label="Nomor Rekening"><input className="rm-input" value={bForm.account_number} onChange={e => setBForm({ ...bForm, account_number: e.target.value })} data-testid="bank-number" /></F>
            <F label="Atas Nama"><input className="rm-input" value={bForm.account_holder_name} onChange={e => setBForm({ ...bForm, account_holder_name: e.target.value })} data-testid="bank-holder" /></F>
            <div className="md:col-span-2 flex justify-end">
              <button className="rm-btn-primary" disabled={saving} onClick={saveBank} data-testid="bank-save">{saving ? "Menyimpan…" : "Submit Rekening"}</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
function F({ label, children }) { return <div><label className="rm-label">{label}</label>{children}</div>; }
function Row({ k, v }) { return <div className="flex justify-between text-sm py-1"><span className="text-slate-500">{k}</span><span className="font-semibold capitalize">{v || "—"}</span></div>; }
