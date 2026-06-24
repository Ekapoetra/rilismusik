import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth, formatApiError } from "@/api/AuthContext";
import { REGISTER } from "@/constants/testIds";
import { LogoFull } from "@/components/shared/Brand";

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
  });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [verifyToken, setVerifyToken] = useState("");

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
    setLoading(true);
    try {
      const { password_confirm, ...payload } = form;
      const data = await register(payload);
      setVerifyToken(data.verification_token || "");
      setTimeout(() => navigate("/label/dashboard"), 1200);
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail) || "Registrasi gagal");
    } finally {
      setLoading(false);
    }
  };

  if (verifyToken) {
    return (
      <div className="min-h-screen rm-mesh flex items-center justify-center px-4 py-12 text-white">
        <div className="w-full max-w-md rm-glass-strong rounded-[28px] p-8 text-center rm-fade-up">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-emerald-500/15 text-emerald-400 grid place-items-center mb-4 text-3xl">✓</div>
          <h1 className="font-display text-2xl font-extrabold tracking-tighter">Akun berhasil dibuat!</h1>
          <p className="text-sm text-zinc-400 mt-2">Mengalihkan ke dashboard…</p>
          <div className="mt-5 text-left text-xs bg-white/5 border border-white/10 rounded-xl p-3">
            <div className="font-semibold text-zinc-300">[DEV] Verification token (untuk uji email verification):</div>
            <code className="block mt-1 break-all text-zinc-400">{verifyToken}</code>
          </div>
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

        <form onSubmit={submit} className="mt-6 grid gap-4">
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
