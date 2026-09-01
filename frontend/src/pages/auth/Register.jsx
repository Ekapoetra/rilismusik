import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth, formatApiError } from "@/api/AuthContext";
import { REGISTER } from "@/constants/testIds";
import { LogoFull } from "@/components/shared/Brand";
import { GoogleAuthButton } from "@/components/auth/GoogleAuthButton";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    label_name: "",
    pic_name: "",
    email: "",
    whatsapp: "",
    password: "",
    password_confirm: "",
    account_type: "label",
    mda_accepted: false,
    claim_existing: false,
    legacy_label_name: "",
  });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [registered, setRegistered] = useState(false);
  const [claimPending, setClaimPending] = useState(false);

  const onChange = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    if (form.password !== form.password_confirm) {
      setErr("Konfirmasi password tidak cocok");
      return;
    }
    if (form.password.length < 8) {
      setErr("Password minimal 8 karakter");
      return;
    }
    if (!form.mda_accepted) {
      setErr("Anda harus menyetujui Master Distribution Agreement (MDA) untuk mendaftar.");
      return;
    }
    if (form.claim_existing && !form.legacy_label_name.trim()) {
      setErr("Mohon isi nama label lama Anda untuk klaim akun.");
      return;
    }
    setLoading(true);
    try {
      const { password_confirm, ...payload } = form;
      const data = await register(payload);
      if (data.claim_pending) {
        setClaimPending(true);
      } else {
        setRegistered(true);
        setTimeout(() => navigate("/label/dashboard"), 1500);
      }
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail) || "Registrasi gagal");
    } finally {
      setLoading(false);
    }
  };

  if (claimPending) {
    return (
      <div className="min-h-screen rm-mesh flex items-center justify-center px-4 py-12 text-white">
        <div className="w-full max-w-md rm-glass-strong rounded-[28px] p-8 text-center rm-fade-up" data-testid="register-claim-pending">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-amber-500/15 text-amber-400 grid place-items-center mb-4 text-3xl">⌛</div>
          <h1 className="font-display text-2xl font-extrabold tracking-tighter">Akun Anda menunggu verifikasi admin</h1>
          <p className="text-sm text-zinc-400 mt-3">
            Permintaan klaim akun lama untuk <b className="text-zinc-200">{form.legacy_label_name}</b> sedang diproses tim kami. Admin akan menghubungkan data lama Anda dalam 1-3 hari kerja.
          </p>
          <p className="text-xs text-zinc-500 mt-3">
            Anda akan menerima notifikasi setelah akun terhubung. Hubungi WhatsApp admin (085864137150) jika urgent.
          </p>
          <button onClick={() => navigate("/label/dashboard")} className="rm-btn-primary mt-6 w-full">
            Masuk Dashboard (Mode Terbatas)
          </button>
        </div>
      </div>
    );
  }

  if (registered) {
    return (
      <div className="min-h-screen rm-mesh flex items-center justify-center px-4 py-12 text-white">
        <div className="w-full max-w-md rm-glass-strong rounded-[28px] p-8 text-center rm-fade-up" data-testid="register-success">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-emerald-500/15 text-emerald-400 grid place-items-center mb-4 text-3xl">✓</div>
          <h1 className="font-display text-2xl font-extrabold tracking-tighter">Akun berhasil dibuat!</h1>
          <p className="text-sm text-zinc-400 mt-2">Kami sudah mengirim link verifikasi ke email Anda. Cek inbox / folder spam.</p>
          <p className="text-xs text-zinc-500 mt-3">Mengalihkan ke dashboard…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen rm-mesh flex items-center justify-center px-4 py-12 text-white">
      <div className="w-full max-w-lg rm-glass-strong rounded-[28px] p-8 md:p-10 rm-fade-up">
        <Link to="/" className="inline-block mb-6">
          <LogoFull width={160} />
        </Link>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">Daftar Akun Label</h1>
        <p className="text-sm text-zinc-400 mt-2">Daftar sebagai label musik atau artis independen.</p>
        <div className="mt-5"><GoogleAuthButton source="register" /><p className="mt-2 text-center text-[11px] text-zinc-500">Google Login hanya untuk akun label yang sudah terdaftar. Pengguna baru tetap melengkapi formulir di bawah.</p></div>
        <div className="my-5 flex items-center gap-3 text-[10px] font-bold uppercase tracking-widest text-zinc-600"><span className="h-px flex-1 bg-white/10" />atau daftar manual<span className="h-px flex-1 bg-white/10" /></div>

        <form onSubmit={submit} className="grid gap-4">
          <div className="grid grid-cols-2 gap-3">
            <button type="button" onClick={() => setForm({ ...form, account_type: "label" })}
              className={`p-3 rounded-2xl border text-sm font-semibold transition ${form.account_type === "label" ? "border-[#FF1F8E] bg-[rgba(255,31,142,0.10)] text-white" : "border-white/10 bg-white/[0.03] text-zinc-300 hover:border-white/20"}`}
              data-testid="register-account-type-label">
              Label Musik
            </button>
            <button type="button" onClick={() => setForm({ ...form, account_type: "independent_artist" })}
              className={`p-3 rounded-2xl border text-sm font-semibold transition ${form.account_type === "independent_artist" ? "border-[#FF1F8E] bg-[rgba(255,31,142,0.10)] text-white" : "border-white/10 bg-white/[0.03] text-zinc-300 hover:border-white/20"}`}
              data-testid="register-account-type-artist">
              Artis Independen
            </button>
          </div>
          <div className="grid md:grid-cols-2 gap-3">
            <div>
              <label className="rm-label">Nama Label / Artis</label>
              <input data-testid={REGISTER.nameInput} className="rm-input" value={form.label_name} onChange={onChange("label_name")} required />
            </div>
            <div>
              <label className="rm-label">Penanggung Jawab</label>
              <input className="rm-input" value={form.pic_name} onChange={onChange("pic_name")} required data-testid="register-pic-input" />
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-3">
            <div>
              <label className="rm-label">Email</label>
              <input data-testid={REGISTER.emailInput} type="email" className="rm-input" value={form.email} onChange={onChange("email")} required />
            </div>
            <div>
              <label className="rm-label">WhatsApp</label>
              <input className="rm-input" value={form.whatsapp} onChange={onChange("whatsapp")} required placeholder="+62812..." data-testid="register-whatsapp-input" />
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-3">
            <div>
              <label className="rm-label">Password</label>
              <input data-testid={REGISTER.passwordInput} type="password" className="rm-input" value={form.password} onChange={onChange("password")} required minLength={8} />
            </div>
            <div>
              <label className="rm-label">Konfirmasi Password</label>
              <input data-testid={REGISTER.passwordConfirmInput} type="password" className="rm-input" value={form.password_confirm} onChange={onChange("password_confirm")} required minLength={8} />
            </div>
          </div>
          {err && <div className="text-sm text-red-300 bg-red-500/10 border border-red-500/20 rounded-xl px-3 py-2">{err}</div>}

          <label className="flex items-start gap-3 rounded-2xl border border-amber-500/20 bg-amber-500/[0.04] px-4 py-3 cursor-pointer hover:border-amber-500/40 transition" data-testid="register-claim-block">
            <input
              type="checkbox"
              className="mt-1 w-4 h-4 accent-amber-400"
              checked={form.claim_existing}
              onChange={(e) => setForm({ ...form, claim_existing: e.target.checked })}
              data-testid="register-claim-checkbox"
            />
            <span className="text-xs text-zinc-300 leading-relaxed">
              <b className="text-amber-200">Saya sudah punya data lama di RILIS MUSIK</b><br/>
              <span className="text-zinc-500">Centang ini jika Anda label/artis lama (pre-migrasi). Admin akan menghubungkan data lama (royalti, withdraw, rilisan) ke akun baru ini dalam 1-3 hari kerja.</span>
            </span>
          </label>
          {form.claim_existing && (
            <input
              required={form.claim_existing}
              value={form.legacy_label_name}
              onChange={onChange("legacy_label_name")}
              placeholder="Nama label lama (persis seperti yang dulu dikenal RILIS MUSIK)"
              className="rm-input"
              data-testid="register-legacy-label-name"
            />
          )}

          <label className="flex items-start gap-3 rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 cursor-pointer hover:border-white/20 transition" data-testid="register-mda-block">
            <input
              type="checkbox"
              className="mt-1 w-4 h-4 accent-[#FF1F8E]"
              checked={form.mda_accepted}
              onChange={(e) => setForm({ ...form, mda_accepted: e.target.checked })}
              data-testid="register-mda-checkbox"
            />
            <span className="text-xs text-zinc-300 leading-relaxed">
              Saya telah membaca dan menyetujui{" "}
              <a
                href={`${process.env.REACT_APP_BACKEND_URL || ""}/api/cms/mda/preview`}
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold rm-gradient-text underline-offset-2 hover:underline"
                data-testid="register-mda-link"
              >
                Master Distribution Agreement (MDA)
              </a>
              {" "}— perjanjian distribusi musik digital antara label dan PT. Jeeres Group Indonesia.
              Persetujuan checkbox ini memiliki kekuatan hukum sesuai UU ITE No. 11/2008.
            </span>
          </label>
          <button data-testid={REGISTER.submitButton} type="submit" className="rm-btn-primary mt-2" disabled={loading || !form.mda_accepted}>
            {loading ? "Memproses…" : "Daftar Sekarang"}
          </button>
        </form>
        <div className="mt-5 text-sm text-center text-zinc-400">
          Sudah punya akun? <Link to="/login" data-testid={REGISTER.loginLink} className="font-semibold rm-gradient-text">Login →</Link>
        </div>
      </div>
    </div>
  );
}
